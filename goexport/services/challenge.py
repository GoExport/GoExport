"""Platform-independent detection of Cloudflare and Anubis browser challenges.

Detection only reads the page Chromium is showing. The browser collects raw
signals with one script and Python classifies them, so the rules are testable
without a browser. Only strongly identifiable challenge characteristics count:
an HTTP 403 or a Cloudflare-branded page alone is never treated as a challenge,
and neither is a page that merely links to or mentions Anubis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchWindowException,
    WebDriverException,
)

logger = logging.getLogger(__name__)

CHALLENGE_TITLES = ("just a moment...", "just a moment…")
LEGACY_CHALLENGE_TITLE = "attention required! | cloudflare"

# Elements that only exist on Cloudflare's interstitial challenge pages.
STRONG_SELECTORS = (
    "#challenge-form",
    "#challenge-running",
    "#challenge-stage",
    "#challenge-body-text",
    "#challenge-error-text",
    "#cf-challenge-running",
    "#trk_jschal_js",
    "script[src*='/cdn-cgi/challenge-platform/']",
    "form[action*='__cf_chl_']",
)

# Cloudflare-related elements that ordinary pages can contain as well, such
# as an embedded Turnstile widget or a Cloudflare error page. These only lead
# to a challenge verdict when the response header confirms it.
WEAK_SELECTORS = (
    "#cf-wrapper",
    "#cf-error-details",
    ".cf-error-details",
    ".cf-turnstile",
    "iframe[src*='challenges.cloudflare.com']",
    "script[src*='challenges.cloudflare.com']",
    "[src*='/cdn-cgi/']",
    "[href*='/cdn-cgi/']",
)

BLOCK_PHRASES = (
    "sorry, you have been blocked",
    "you are unable to access",
    "used cloudflare to restrict access",
    "error 1020",
    "error code: 1020",
)

UNSUPPORTED_PHRASES = (
    "unsupported browser",
    "browser is not supported",
    "browser is out of date",
    "browser is outdated",
    "update your browser",
    "upgrade your browser",
)

# Anubis (https://github.com/TecharoHQ/anubis) serves every asset of its
# challenge and error pages below this path.
ANUBIS_PATH = "/.within.website/x/cmd/anubis/"
# Proof-of-work algorithms; their page reports progress while it computes.
ANUBIS_PROOF_OF_WORK = frozenset({"fast", "slow", "argon2id", "hashx", "sha256"})
# Anubis' untranslated feature names in its "Missing feature" title, and the
# phrases it uses when the browser cannot run the check.
ANUBIS_UNSUPPORTED_PHRASES = (
    "web workers",
    "web.crypto",
    "webassembly",
    "is your browser out of date",
    "browser is up to date",
)
ANUBIS_BLOCK_PHRASES = ("access denied",)

SIGNALS_SCRIPT = """
    const selectors = arguments[0];
    const doc = document;
    const matches = list => list.filter(selector => {
        try {
            return doc.querySelector(selector) !== null;
        } catch (e) {
            return false;
        }
    });
    const body = doc.body ? (doc.body.innerText || '') : '';
    const anubisPath = '/.within.website/x/cmd/anubis/';
    const elementText = id => {
        const element = doc.getElementById(id);
        return element
            ? String(element.innerText || element.textContent || '').trim().slice(0, 300)
            : null;
    };
    const anubis = (() => {
        const data = doc.getElementById('anubis_challenge');
        const result = {challenge: false, algorithm: null, difficulty: null, challengeId: null};
        if (data && data.type === 'application/json') {
            try {
                const parsed = JSON.parse(data.textContent);
                if (parsed && parsed.rules && typeof parsed.rules.algorithm === 'string'
                        && parsed.challenge) {
                    result.challenge = true;
                    result.algorithm = parsed.rules.algorithm;
                    result.difficulty = typeof parsed.rules.difficulty === 'number'
                        ? parsed.rules.difficulty : null;
                    // Current releases send an object; older ones a string.
                    result.challengeId = typeof parsed.challenge === 'object'
                        ? String(parsed.challenge.id || '') || null
                        : String(parsed.challenge);
                }
            } catch (e) {
                // Not Anubis' challenge data.
            }
        }
        const image = doc.getElementById('image');
        const scriptError = doc.getElementById('anubis-script-error');
        const progress = doc.getElementById('progress');
        result.version = doc.getElementById('anubis_version') !== null;
        result.script = doc.querySelector("script[src*='" + anubisPath + "']") !== null;
        result.assets = doc.querySelector(
            "[src*='" + anubisPath + "'], [href*='" + anubisPath + "']") !== null;
        result.booted = window.__anubisBooted === true;
        result.rejected = Boolean(image && (image.getAttribute('src') || '')
            .indexOf(anubisPath + 'static/img/reject.') !== -1);
        result.scriptError = Boolean(scriptError
            && getComputedStyle(scriptError).display !== 'none');
        result.heading = elementText('title');
        result.status = elementText('status');
        result.progress = progress ? progress.getAttribute('aria-valuenow') : null;
        return result;
    })();
    return {
        url: String(location.href),
        title: String(doc.title || ''),
        readyState: String(doc.readyState),
        strong: matches(selectors.strong),
        weak: matches(selectors.weak),
        challengeOptions: typeof window._cf_chl_opt !== 'undefined',
        text: body.slice(0, 4000),
        anubis: anubis,
    };
"""

# Confirm an ambiguous page with Cloudflare's ``cf-mitigated`` response
# header. A same-origin request exposes it; nothing on the page is changed.
HEADER_PROBE_SCRIPT = """
    const done = arguments[arguments.length - 1];
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    fetch(location.href, {
        method: 'HEAD',
        credentials: 'include',
        cache: 'no-store',
        redirect: 'manual',
        signal: controller.signal,
    }).then(response => {
        clearTimeout(timer);
        done({status: response.status, mitigated: response.headers.get('cf-mitigated')});
    }).catch(() => {
        clearTimeout(timer);
        done(null);
    });
"""


class ChallengeKind(Enum):
    NONE = "none"
    CHALLENGE = "challenge"
    BLOCKED = "blocked"
    UNSUPPORTED = "unsupported"
    # The challenge page reports an error it cannot recover from by itself.
    FAILED = "failed"


class ChallengeProvider(Enum):
    CLOUDFLARE = "cloudflare"
    ANUBIS = "anubis"

    @property
    def label(self) -> str:
        return "Cloudflare" if self is ChallengeProvider.CLOUDFLARE else "Anubis"


@dataclass(frozen=True)
class ChallengeResult:
    kind: ChallengeKind
    reason: str = ""
    url: str = ""
    ready: bool = True
    provider: ChallengeProvider | None = None
    # What the challenge page itself says, for diagnostics.
    detail: str = ""
    # Anubis only: the algorithm, the issued challenge and its visible
    # progress, which identify repeated challenges and stalls.
    algorithm: str | None = None
    challenge_id: str | None = None
    progress: str | None = None

    @property
    def automatic(self) -> bool:
        """Whether the challenge normally completes without the user."""
        return (
            self.kind is ChallengeKind.CHALLENGE
            and self.provider is ChallengeProvider.ANUBIS
        )

    @property
    def is_challenge(self) -> bool:
        return self.kind is ChallengeKind.CHALLENGE


NO_CHALLENGE = ChallengeResult(ChallengeKind.NONE)


class BrowserUnavailableError(RuntimeError):
    """Raised when the Selenium session or its window no longer exists."""


def is_session_lost(error: WebDriverException) -> bool:
    if isinstance(error, (NoSuchWindowException, InvalidSessionIdException)):
        return True
    message = str(error).lower()
    return any(
        phrase in message
        for phrase in (
            "chrome not reachable",
            "disconnected",
            "target window already closed",
            "no such window",
            "invalid session id",
            "session deleted",
        )
    )


def classify(signals: dict[str, Any], mitigated: str | None = None) -> ChallengeResult:
    """Classify the raw page signals collected by ``SIGNALS_SCRIPT``.

    ``mitigated`` is the value of the response's ``cf-mitigated`` header, when
    it is known.
    """
    url = str(signals.get("url", ""))
    ready = signals.get("readyState") == "complete"
    if not url.lower().startswith(("http://", "https://")):
        return ChallengeResult(ChallengeKind.NONE, url=url, ready=ready)

    anubis = classify_anubis(signals, url, ready)
    if anubis is not None:
        return anubis

    title = str(signals.get("title", "")).strip().lower()
    text = str(signals.get("text", "")).lower()
    strong = tuple(signals.get("strong") or ())
    weak = tuple(signals.get("weak") or ())

    reason = ""
    if mitigated is not None and mitigated.strip().lower() == "challenge":
        reason = "cf-mitigated: challenge response header"
    elif title in CHALLENGE_TITLES:
        reason = f"challenge page title {signals.get('title')!r}"
    elif signals.get("challengeOptions"):
        reason = "Cloudflare challenge options (_cf_chl_opt)"
    elif strong:
        reason = f"challenge page element {strong[0]}"
    elif title == LEGACY_CHALLENGE_TITLE and not _has_phrase(text, BLOCK_PHRASES):
        reason = f"challenge page title {signals.get('title')!r}"

    if reason:
        if _has_phrase(text, UNSUPPORTED_PHRASES):
            return ChallengeResult(
                ChallengeKind.UNSUPPORTED,
                "Cloudflare reports that this browser is unsupported",
                url,
                ready,
                ChallengeProvider.CLOUDFLARE,
            )
        return ChallengeResult(
            ChallengeKind.CHALLENGE, reason, url, ready, ChallengeProvider.CLOUDFLARE
        )

    if (weak or "cloudflare" in text or "cloudflare" in title) and _has_phrase(
        text + " " + title, BLOCK_PHRASES
    ):
        return ChallengeResult(
            ChallengeKind.BLOCKED,
            "Cloudflare access-denied page",
            url,
            ready,
            ChallengeProvider.CLOUDFLARE,
        )
    # Anubis' pass-challenge redirect is a transition, never the real page.
    if ANUBIS_PATH in url:
        return ChallengeResult(ChallengeKind.NONE, url=url, ready=False)
    return ChallengeResult(ChallengeKind.NONE, url=url, ready=ready)


def classify_anubis(
    signals: dict[str, Any], url: str, ready: bool
) -> ChallengeResult | None:
    """Classify an Anubis challenge or error page, or None for other pages.

    An Anubis page needs either its challenge data (a JSON document with
    ``rules.algorithm``) or both its version marker and its own scripts or
    images. Links to Anubis, or text mentioning it, never count.
    """
    anubis = signals.get("anubis")
    if not isinstance(anubis, dict):
        return None
    challenge = bool(anubis.get("challenge"))
    if not challenge and not (anubis.get("version") and anubis.get("assets")):
        return None

    heading = str(anubis.get("heading") or "").strip()
    status = str(anubis.get("status") or "").strip()
    detail = " ".join(" ".join(part.split()) for part in (heading, status) if part)
    lowered = detail.lower()
    algorithm = str(anubis["algorithm"]) if anubis.get("algorithm") else None
    challenge_id = str(anubis["challengeId"]) if anubis.get("challengeId") else None
    progress = str(anubis["progress"]) if anubis.get("progress") else None

    def result(kind: ChallengeKind, reason: str) -> ChallengeResult:
        return ChallengeResult(
            kind,
            reason,
            url,
            ready,
            ChallengeProvider.ANUBIS,
            detail,
            algorithm,
            challenge_id,
            progress,
        )

    if anubis.get("scriptError"):
        return result(ChallengeKind.FAILED, "Anubis could not load its JavaScript")
    if anubis.get("rejected"):
        if _has_phrase(lowered, ANUBIS_UNSUPPORTED_PHRASES + UNSUPPORTED_PHRASES):
            return result(
                ChallengeKind.UNSUPPORTED,
                "Anubis reports that this browser cannot run its check",
            )
        if challenge:
            return result(ChallengeKind.FAILED, "Anubis challenge error")
        if _has_phrase(lowered, ANUBIS_BLOCK_PHRASES):
            return result(ChallengeKind.BLOCKED, "Anubis access-denied page")
        return result(ChallengeKind.FAILED, "Anubis error page")

    if challenge or anubis.get("script"):
        difficulty = anubis.get("difficulty")
        reason = f"Anubis {algorithm or 'challenge'} challenge" + (
            f" (difficulty {difficulty})" if difficulty is not None else ""
        )
        return result(ChallengeKind.CHALLENGE, reason)
    return None


def needs_header_probe(signals: dict[str, Any]) -> bool:
    """Whether a page is Cloudflare-related but not conclusively a challenge."""
    return bool(signals.get("weak")) and classify(signals).kind is ChallengeKind.NONE


def _has_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


class ChallengeDetector:
    """Detect a Cloudflare or Anubis challenge in a Selenium-controlled page."""

    def detect(self, driver) -> ChallengeResult:
        try:
            signals = driver.execute_script(
                SIGNALS_SCRIPT,
                {"strong": list(STRONG_SELECTORS), "weak": list(WEAK_SELECTORS)},
            )
        except WebDriverException as error:
            if is_session_lost(error):
                raise BrowserUnavailableError(
                    "The Chromium window was closed."
                ) from error
            # A navigating page (such as Cloudflare's own reload after a
            # solved challenge) briefly rejects scripts. It is not verified.
            logger.debug("Could not inspect the page: %s", error)
            return ChallengeResult(ChallengeKind.NONE, ready=False)

        if not isinstance(signals, dict):
            logger.debug("Unexpected challenge signals: %r", signals)
            return NO_CHALLENGE

        mitigated = None
        if needs_header_probe(signals):
            mitigated = self._probe_header(driver)
        result = classify(signals, mitigated)
        if result.kind is not ChallengeKind.NONE:
            logger.debug("Challenge detection on %s: %s", result.url, result)
        return result

    @staticmethod
    def _probe_header(driver) -> str | None:
        try:
            response = driver.execute_async_script(HEADER_PROBE_SCRIPT)
        except WebDriverException as error:
            if is_session_lost(error):
                raise BrowserUnavailableError(
                    "The Chromium window was closed."
                ) from error
            logger.debug("Cloudflare header probe failed: %s", error)
            return None
        if isinstance(response, dict):
            mitigated = response.get("mitigated")
            return str(mitigated) if mitigated else None
        return None
