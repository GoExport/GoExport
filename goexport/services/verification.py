"""Browser verification (Cloudflare, Anubis) for the existing Selenium session.

When a challenge is detected, export preparation pauses until it is cleared in
the same Chromium session (same profile, cookies and WebDriver). The
controller never creates a browser or replaces the driver::

    IDLE -> CHALLENGE_DETECTED -> [VERIFYING_AUTOMATICALLY] -> WAITING_FOR_USER
         -> VERIFIED -> RESUMED                  \\-> TIMEOUT | CANCELLED | FAILED

Anubis challenges are proof-of-work checks that Chromium completes by itself,
so they are first left to run unattended. The browser is only shown when one
stops making progress or does not finish within the automatic window, and for
Cloudflare challenges, which need the user.

How the browser is shown is delegated to a presenter: the Chromium window
itself on Windows (and on Linux without GoExport's Xvfb display), or a bundled
VNC viewer attached to GoExport's private Xvfb display on Linux.
"""

from __future__ import annotations

import json
import logging
import sys
import threading
import time
from collections.abc import Callable
from enum import Enum
from typing import IO, NoReturn, Protocol

from goexport import config
from goexport.reporting import Reporter
from goexport.services.challenge import (
    ANUBIS_PROOF_OF_WORK,
    BrowserUnavailableError,
    ChallengeDetector,
    ChallengeKind,
    ChallengeProvider,
    ChallengeResult,
)

logger = logging.getLogger(__name__)

POLL_SECONDS = 1.0
# Challenges reload the protected page once they are solved. Requiring
# consecutive clean, fully loaded polls avoids resuming on that transition.
VERIFIED_STABLE_POLLS = 2
# How long a page that is still loading or redirecting may take to settle
# before GoExport decides whether it is a challenge.
SETTLE_SECONDS = 10
# A computing Anubis page updates its speed and progress at least every
# second; one showing nothing new for this long has stalled.
ANUBIS_STALL_SECONDS = 20
# Anubis issuing more challenges than this in one verification means its pass
# is not being accepted; retrying further would loop forever.
MAX_ANUBIS_CHALLENGES = 3

UNSUPPORTED_MESSAGE = (
    "Cloudflare reports that GoExport's browser is unsupported. GoExport must "
    "use Chromium 87 for Flash playback, so this site's verification cannot be "
    "completed. Ask the site operator to allow GoExport or use a server "
    "without Cloudflare verification."
)
BLOCKED_MESSAGE = (
    "Cloudflare denied access to {url}. This is a block, not a verification "
    "challenge, so it cannot be completed manually."
)
TIMEOUT_MESSAGE = (
    "Browser verification was not completed within {timeout} seconds. Cloudflare "
    "may not accept GoExport's Chromium 87 browser; if the challenge kept "
    "repeating, this site cannot be exported."
)
ANUBIS_UNSUPPORTED_MESSAGE = (
    "Anubis could not run its proof-of-work check in GoExport's browser{detail}. "
    "GoExport must use Chromium 87 for Flash playback and cannot switch to a "
    "newer browser, so this site cannot be exported until its Anubis "
    "configuration supports Chromium 87."
)
ANUBIS_FAILED_MESSAGE = (
    "Anubis verification failed{detail}. The check cannot continue by itself; "
    "try again later, or ask the site operator if the problem persists."
)
ANUBIS_BLOCKED_MESSAGE = (
    "Anubis denied access to {url}{detail}. This is a block, not a verification "
    "challenge, so it cannot be completed."
)
ANUBIS_TIMEOUT_MESSAGE = (
    "Anubis verification was not completed within {timeout} seconds{detail}. "
    "Its proof-of-work may be too slow for this difficulty in Chromium 87, or "
    "the site may not accept GoExport's browser."
)
ANUBIS_REPEATED_MESSAGE = (
    "Anubis issued a new challenge after each completed check ({count} "
    "challenges), so its pass is not being accepted. Verification was stopped "
    "instead of retrying indefinitely; the site may not accept GoExport's "
    "Chromium 87 browser."
)


class VerificationState(Enum):
    IDLE = "idle"
    CHALLENGE_DETECTED = "challenge_detected"
    VERIFYING_AUTOMATICALLY = "verifying_automatically"
    WAITING_FOR_USER = "waiting_for_user"
    VERIFIED = "verified"
    RESUMED = "resumed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    FAILED = "failed"


class VerificationError(RuntimeError):
    """Browser verification ended without the challenge being cleared."""

    def __init__(self, message: str, state: VerificationState):
        super().__init__(message)
        self.state = state


class VerificationCancelled(VerificationError):
    def __init__(self, message: str = "Browser verification was cancelled."):
        super().__init__(message, VerificationState.CANCELLED)


class VerificationInterruptedError(RuntimeError):
    """A challenge replaced the player after recording or rendering began."""


class PresentationError(RuntimeError):
    """The verification browser could not be shown to the user."""


class VerificationPresenter(Protocol):
    # "window" shows Chromium itself; "vnc" shows a VNC viewer.
    presentation: str
    instructions: str

    def show(self) -> None: ...

    def poll(self) -> str | None:
        """Return why the presentation ended early, or None while it is usable.

        ``"closed"`` means the user closed it; any other value is a failure.
        """
        ...

    def restore(self) -> None: ...


# Set by the GUI's JSON ``cancel`` command or by direct callers.
CANCEL_EVENT = threading.Event()
COMMAND_POLL_SECONDS = 0.2
ERROR_BROKEN_PIPE = 109
_listener_lock = threading.Lock()
_listener: threading.Thread | None = None


def listen_for_commands(stream: IO[str] | None = None) -> None:
    """Accept newline-delimited JSON commands from the controlling GUI.

    The only command is ``{"command": "cancel"}``. The listener is started the
    first time verification waits in JSON mode and lives until stdin closes.
    """
    global _listener
    with _listener_lock:
        if _listener is not None:
            return
        source = stream if stream is not None else sys.stdin
        _listener = threading.Thread(
            target=_read_commands,
            args=(source,),
            name="goexport-commands",
            daemon=True,
        )
        _listener.start()


def _handle_command(line: str) -> None:
    try:
        command = json.loads(line)
    except ValueError:
        return
    if isinstance(command, dict) and command.get("command") == "cancel":
        logger.info("Cancellation requested by the controlling application.")
        CANCEL_EVENT.set()


def _read_commands(stream: IO[str]) -> None:
    try:
        if config.SYSTEM == "Windows" and _read_windows_pipe(stream):
            return
        for line in stream:
            _handle_command(line)
    except (OSError, ValueError):
        logger.debug("Command stream closed.", exc_info=True)


def _read_windows_pipe(stream: IO[str]) -> bool:
    """Read commands from a Windows pipe without leaving a read pending.

    While one thread is blocked reading a synchronous pipe, Windows makes
    file information queries on that handle from any other thread wait for
    the read to finish. Native libraries query the standard handles while
    loading (numpy's DLLs, imported by CaptureKit after verification, do), so
    a pending read on the GUI's stdin pipe froze the export forever. Only
    bytes that PeekNamedPipe reports as already waiting are read, so no read
    is ever left pending.
    Returns False if the stream is not a pipe (a console or a file).
    """
    import ctypes
    import msvcrt
    import os
    from ctypes import wintypes

    try:
        fd = stream.fileno()
        handle = msvcrt.get_osfhandle(fd)
    except (AttributeError, OSError, ValueError):
        return False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    peek = kernel32.PeekNamedPipe
    peek.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    peek.restype = wintypes.BOOL
    available = wintypes.DWORD()
    if not peek(handle, None, 0, None, ctypes.byref(available), None):
        if ctypes.get_last_error() == ERROR_BROKEN_PIPE:
            return True
        return False

    pending = b""
    while True:
        if not peek(handle, None, 0, None, ctypes.byref(available), None):
            # The controlling application closed its end of the pipe.
            logger.debug("Command pipe closed (error %s).", ctypes.get_last_error())
            return True
        if not available.value:
            time.sleep(COMMAND_POLL_SECONDS)
            continue
        data = os.read(fd, available.value)
        if not data:
            return True
        pending += data
        *lines, pending = pending.split(b"\n")
        for line in lines:
            _handle_command(line.decode("utf-8", errors="replace"))


def _page_detail(result: ChallengeResult) -> str:
    return f" (the page reports: {result.detail})" if result.detail else ""


class VerificationController:
    def __init__(
        self,
        driver,
        presenter_factory: Callable[[], VerificationPresenter],
        reporter: Reporter,
        timeout_seconds: float = config.VERIFICATION_TIMEOUT,
        interactive: bool = config.VERIFICATION_INTERACTIVE,
        detector: ChallengeDetector | None = None,
        cancel_event: threading.Event | None = None,
        poll_seconds: float = POLL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        automatic_timeout_seconds: float = config.VERIFICATION_AUTOMATIC_TIMEOUT,
    ):
        self.driver = driver
        self.presenter_factory = presenter_factory
        self.reporter = reporter
        self.timeout_seconds = timeout_seconds
        self.automatic_timeout_seconds = automatic_timeout_seconds
        self.interactive = interactive
        self.detector = detector or ChallengeDetector()
        self.cancel_event = cancel_event if cancel_event is not None else CANCEL_EVENT
        self.poll_seconds = poll_seconds
        self.clock = clock
        self.state = VerificationState.IDLE
        self.provider = ChallengeProvider.CLOUDFLARE
        self._last_challenge: ChallengeResult | None = None

    def ensure_verified(self) -> bool:
        """Pause until the current page is not a challenge.

        Returns False when no challenge was present (nothing is shown), True
        after a completed verification. Raises ``VerificationError`` otherwise.
        """
        self.state = VerificationState.IDLE
        result = self._settle(self._detect())
        if result.kind is ChallengeKind.NONE:
            return False
        self.state = VerificationState.CHALLENGE_DETECTED
        self.provider = result.provider or ChallengeProvider.CLOUDFLARE
        self._last_challenge = result
        logger.info(
            "%s challenge detected on %s (%s).",
            self.provider.label,
            result.url,
            result.reason,
        )
        self._fail_if_unrecoverable(result)
        deadline = (
            self.clock() + self.timeout_seconds if self.timeout_seconds > 0 else None
        )

        why = ""
        if result.automatic:
            pending = self._verify_automatically(result, deadline)
            if pending is None:
                self._resume()
                return True
            result, why = pending
            self.provider = result.provider or self.provider

        if not self.interactive:
            if why:
                message = (
                    f"{self.provider.label} verification did not complete "
                    f"automatically for {result.url} ({why}), and interactive "
                    "verification is disabled."
                )
            else:
                message = (
                    f"{self.provider.label} requires manual browser verification "
                    f"for {result.url}, but interactive verification is disabled."
                )
            self._fail(message, "disabled")

        try:
            presenter = self.presenter_factory()
            presenter.show()
        except PresentationError as error:
            self._fail(str(error), "presentation")
        try:
            self.state = VerificationState.WAITING_FOR_USER
            intro = (
                f"{self.provider.label} verification needs your help because {why}. "
                if why
                else "Manual browser verification is required. "
            )
            self.reporter.verification_required(
                self.provider.value,
                intro + presenter.instructions,
                presenter.presentation,
                self._remaining(deadline),
            )
            if self.reporter.json_mode:
                listen_for_commands()
            self._wait(presenter, deadline)
            self.state = VerificationState.VERIFIED
        finally:
            presenter.restore()
        self._resume()
        return True

    def _settle(self, result: ChallengeResult) -> ChallengeResult:
        """Wait briefly while a page is still loading or redirecting.

        A fast challenge can already be submitting its pass when it is first
        inspected; the page it leads to decides whether one is needed.
        """
        deadline = self.clock() + SETTLE_SECONDS
        while (
            result.kind is ChallengeKind.NONE
            and not result.ready
            and self.clock() < deadline
            and not self.cancel_event.is_set()
        ):
            self.cancel_event.wait(min(self.poll_seconds, 0.25))
            result = self._detect()
        return result

    def _resume(self) -> None:
        self.state = VerificationState.VERIFIED
        self.reporter.verification_complete(self.provider.value)
        self.state = VerificationState.RESUMED
        logger.info("%s verification complete; resuming export.", self.provider.label)

    def _remaining(self, deadline: float | None) -> float | None:
        if deadline is None:
            return None
        return max(0, round(deadline - self.clock()))

    def _verify_automatically(
        self, result: ChallengeResult, deadline: float | None
    ) -> tuple[ChallengeResult, str] | None:
        """Let an automatic challenge complete in the background.

        Returns None once the intended page has loaded, or the challenge and
        the reason it needs the user. The page is only read once per poll, so
        the proof-of-work (which runs in Web Workers) is never interrupted.
        """
        self.state = VerificationState.VERIFYING_AUTOMATICALLY
        self.reporter.verification_required(
            self.provider.value,
            f"{self.provider.label} verification is in progress.",
            None,
            self.timeout_seconds or None,
            interaction="automatic",
        )
        if self.reporter.json_mode:
            listen_for_commands()
        started = self.clock()
        automatic_deadline = (
            started + self.automatic_timeout_seconds
            if self.automatic_timeout_seconds > 0
            else None
        )
        challenges = 1
        last = result
        on_challenge = True
        fingerprint = (result.challenge_id, result.detail, result.progress)
        changed_at = started
        clean_polls = 0
        while True:
            if self.cancel_event.is_set():
                self._fail("Browser verification was cancelled.", "cancelled")
            self._fail_if_unrecoverable(result)
            now = self.clock()
            if result.kind is ChallengeKind.CHALLENGE:
                clean_polls = 0
                if not result.automatic:
                    label = (result.provider or ChallengeProvider.CLOUDFLARE).label
                    return result, f"a {label} challenge appeared"
                new_challenge = (
                    result.challenge_id is not None
                    and last.challenge_id is not None
                    and result.challenge_id != last.challenge_id
                )
                if not on_challenge or new_challenge:
                    challenges += 1
                    logger.info("Anubis issued another challenge (%d).", challenges)
                    if challenges > MAX_ANUBIS_CHALLENGES:
                        self._fail(
                            ANUBIS_REPEATED_MESSAGE.format(count=challenges),
                            "repeated",
                        )
                on_challenge = True
                last = self._last_challenge = result
                current = (result.challenge_id, result.detail, result.progress)
                if current != fingerprint:
                    fingerprint, changed_at = current, now
                elif (
                    result.algorithm in ANUBIS_PROOF_OF_WORK
                    and now - changed_at >= ANUBIS_STALL_SECONDS
                ):
                    logger.warning(
                        "Anubis made no progress for %d seconds%s.",
                        ANUBIS_STALL_SECONDS,
                        _page_detail(result),
                    )
                    return (
                        result,
                        f"it made no progress for {ANUBIS_STALL_SECONDS} seconds",
                    )
            else:
                on_challenge = False
                if result.ready:
                    clean_polls += 1
                    if clean_polls >= VERIFIED_STABLE_POLLS:
                        logger.info(
                            "Anubis verification completed automatically in %.1f "
                            "seconds.",
                            now - started,
                        )
                        return None
                else:
                    clean_polls = 0

            if deadline is not None and now >= deadline:
                self._fail_timeout()
            if automatic_deadline is not None and now >= automatic_deadline:
                return (
                    last,
                    f"it did not finish within "
                    f"{int(self.automatic_timeout_seconds)} seconds",
                )
            self.cancel_event.wait(self.poll_seconds)
            result = self._detect()

    def _wait(self, presenter: VerificationPresenter, deadline: float | None) -> None:
        clean_polls = 0
        while True:
            if self.cancel_event.is_set():
                self._fail("Browser verification was cancelled.", "cancelled")
            ended = presenter.poll()
            if ended == "closed":
                self._fail(
                    "Browser verification was cancelled because the "
                    "verification window was closed.",
                    "cancelled",
                )
            if ended is not None:
                self._fail(f"Browser verification failed: {ended}", "failed")

            result = self._detect()
            self._fail_if_unrecoverable(result)
            if result.kind is ChallengeKind.NONE and result.ready:
                clean_polls += 1
                if clean_polls >= VERIFIED_STABLE_POLLS:
                    return
            else:
                clean_polls = 0
                if result.kind is ChallengeKind.CHALLENGE:
                    self._last_challenge = result

            if deadline is not None and self.clock() >= deadline:
                self._fail_timeout()
            self.cancel_event.wait(self.poll_seconds)

    def _fail_if_unrecoverable(self, result: ChallengeResult) -> None:
        """Stop at once for blocks and pages that report they cannot continue."""
        if result.kind not in (
            ChallengeKind.BLOCKED,
            ChallengeKind.UNSUPPORTED,
            ChallengeKind.FAILED,
        ):
            return
        if result.provider is not None:
            self.provider = result.provider
        detail = _page_detail(result)
        if self.provider is ChallengeProvider.ANUBIS:
            if result.kind is ChallengeKind.BLOCKED:
                self._fail(
                    ANUBIS_BLOCKED_MESSAGE.format(url=result.url, detail=detail),
                    "blocked",
                )
            if result.kind is ChallengeKind.UNSUPPORTED:
                self._fail(
                    ANUBIS_UNSUPPORTED_MESSAGE.format(detail=detail), "unsupported"
                )
            self._fail(ANUBIS_FAILED_MESSAGE.format(detail=detail), "failed")
        if result.kind is ChallengeKind.BLOCKED:
            self._fail(BLOCKED_MESSAGE.format(url=result.url), "blocked")
        if result.kind is ChallengeKind.UNSUPPORTED:
            self._fail(UNSUPPORTED_MESSAGE, "unsupported")
        self._fail(f"Browser verification failed: {result.reason}.", "failed")

    def _fail_timeout(self) -> NoReturn:
        timeout = int(self.timeout_seconds)
        if self.provider is ChallengeProvider.ANUBIS:
            last = self._last_challenge
            detail = _page_detail(last) if last is not None else ""
            self._fail(
                ANUBIS_TIMEOUT_MESSAGE.format(timeout=timeout, detail=detail),
                "timeout",
            )
        self._fail(TIMEOUT_MESSAGE.format(timeout=timeout), "timeout")

    def _detect(self) -> ChallengeResult:
        try:
            return self.detector.detect(self.driver)
        except BrowserUnavailableError as error:
            self._fail(
                f"Browser verification failed: {error} The export cannot continue.",
                "browser_closed",
            )

    def _fail(self, message: str, reason: str) -> NoReturn:
        if reason == "cancelled":
            state = VerificationState.CANCELLED
        elif reason == "timeout":
            state = VerificationState.TIMEOUT
        else:
            state = VerificationState.FAILED
        self.state = state
        self.reporter.verification_failed(message, reason, self.provider.value)
        if state is VerificationState.CANCELLED:
            raise VerificationCancelled(message)
        raise VerificationError(message, state)


def create_presenter(service, driver) -> VerificationPresenter:
    """Choose how to show the existing browser session on this platform."""
    display = getattr(service, "display", None)
    if config.SYSTEM == "Linux" and display is not None and display.active:
        from goexport.services.vnc import VNCPresenter

        return VNCPresenter(display)

    from goexport.services.window_presenter import WindowPresenter

    return WindowPresenter(driver)


def verify_browser(service, driver, args, reporter: Reporter) -> bool:
    """Pause until the current page is not a challenge, verifying if needed."""
    controller = VerificationController(
        driver,
        lambda: create_presenter(service, driver),
        reporter,
        timeout_seconds=getattr(
            args, "verification_timeout", config.VERIFICATION_TIMEOUT
        ),
        interactive=getattr(
            args, "interactive_verification", config.VERIFICATION_INTERACTIVE
        ),
        automatic_timeout_seconds=getattr(
            args,
            "automatic_verification_timeout",
            config.VERIFICATION_AUTOMATIC_TIMEOUT,
        ),
    )
    return controller.ensure_verified()


def explain_interruption(driver, error: BaseException) -> None:
    """Raise a clear error if ``error`` happened because a challenge appeared."""
    try:
        result = ChallengeDetector().detect(driver)
    except BrowserUnavailableError:
        return
    if result.kind in (
        ChallengeKind.CHALLENGE,
        ChallengeKind.UNSUPPORTED,
        ChallengeKind.FAILED,
    ):
        label = (result.provider or ChallengeProvider.CLOUDFLARE).label
        raise VerificationInterruptedError(
            f"A {label} challenge replaced the movie after export started, so "
            "the partial output was discarded. Run the export again; GoExport "
            "completes verification before Flash starts."
        ) from error
