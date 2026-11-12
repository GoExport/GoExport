"""Verification against the bundled Chromium 87 and local mock challenge pages.

The Anubis tests run Anubis' own challenge code (vendored in fixtures/anubis)
against a mock server that checks the proof-of-work, as a real site does.

Opt-in because it opens a visible browser: set GOEXPORT_BROWSER_TESTS=1. On
Linux it runs on GoExport's Xvfb display and needs no desktop for detection.
"""

import hashlib
import io
import json
import os
import secrets
import threading
import time
import unittest
import uuid
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs

from goexport import config
from goexport.reporting import Reporter
from goexport.services import verification
from goexport.services.browser import BrowserService
from goexport.services.challenge import (
    ChallengeDetector,
    ChallengeKind,
    ChallengeProvider,
)
from goexport.services.verification import (
    MAX_ANUBIS_CHALLENGES,
    VerificationController,
    VerificationError,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "cloudflare"

# path -> (fixture, status, cf-mitigated header, clearance cookie lifts it)
ROUTES = {
    "/challenge": ("challenge.html", 403, "challenge", True),
    "/stuck": ("challenge.html", 403, "challenge", False),
    "/header-only": ("header_only_challenge.html", 403, "challenge", True),
    "/login": ("turnstile_login.html", 200, None, False),
    "/forbidden": ("forbidden.html", 403, None, False),
    "/bad-gateway": ("cloudflare_502.html", 502, None, False),
    "/blocked": ("blocked.html", 403, "block", False),
    "/unsupported": ("unsupported.html", 403, "challenge", False),
    "/": ("wrapper.html", 200, None, False),
}


class MockCloudflare(BaseHTTPRequestHandler):
    def _respond(self, body: bool):
        path = self.path.split("?", 1)[0]
        fixture, status, mitigated, clearable = ROUTES.get(path, ROUTES["/"])
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        if clearable and "cf_clearance" in cookie:
            fixture, status, mitigated = "wrapper.html", 200, None
        data = (FIXTURES / fixture).read_bytes()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        if mitigated:
            self.send_header("cf-mitigated", mitigated)
        self.end_headers()
        if body:
            self.wfile.write(data)

    def do_GET(self):
        self._respond(True)

    def do_HEAD(self):
        self._respond(False)

    def log_message(self, *_args):
        pass


def _browser_available():
    return (
        os.environ.get("GOEXPORT_BROWSER_TESTS") == "1"
        and config.CHROME_PATH.is_file()
        and config.CHROMEDRIVER_PATH.is_file()
    )


@unittest.skipUnless(
    _browser_available(),
    "Set GOEXPORT_BROWSER_TESTS=1 with the bundled Chromium installed.",
)
class BrowserVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockCloudflare)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.service = BrowserService(
            config.CHROME_PATH,
            config.CHROMEDRIVER_PATH,
            config.FLASH_PLUGIN_PATH,
            config.FLASH_PLUGIN_VERSION,
            width=800,
            height=600,
        )
        cls.driver = cls.service.create_driver()

    @classmethod
    def tearDownClass(cls):
        cls.service.close()
        cls.server.shutdown()

    def setUp(self):
        self.driver.delete_all_cookies()

    def controller(self, timeout=20):
        stream = io.StringIO()
        controller = VerificationController(
            self.driver,
            lambda: verification.create_presenter(self.service, self.driver),
            Reporter(json_mode=True, stream=stream),
            timeout_seconds=timeout,
            cancel_event=threading.Event(),
            poll_seconds=0.25,
        )
        return controller, stream

    def test_mock_pages_are_classified_by_the_real_detection_script(self):
        expected = {
            "/": ChallengeKind.NONE,
            "/login": ChallengeKind.NONE,
            "/forbidden": ChallengeKind.NONE,
            "/bad-gateway": ChallengeKind.NONE,
            "/stuck": ChallengeKind.CHALLENGE,
            "/header-only": ChallengeKind.CHALLENGE,
            "/blocked": ChallengeKind.BLOCKED,
            "/unsupported": ChallengeKind.UNSUPPORTED,
        }
        detector = ChallengeDetector()
        for path, kind in expected.items():
            with self.subTest(path=path):
                self.driver.get(self.base + path)
                if path == "/header-only":
                    # Classify before the mock "solves" itself.
                    self.driver.delete_all_cookies()
                self.assertIs(detector.detect(self.driver).kind, kind)

    def test_challenge_is_completed_in_the_same_session(self):
        self.driver.get(self.base + "/challenge?delay=2500")
        session = self.driver.session_id
        handle = self.driver.current_window_handle
        rect = self.driver.get_window_rect()
        controller, stream = self.controller()

        with patch.object(verification, "listen_for_commands"):
            self.assertTrue(controller.ensure_verified())

        self.assertEqual(self.driver.title, "Wrapper")
        self.assertEqual(self.driver.session_id, session)
        self.assertEqual(self.driver.current_window_handle, handle)
        self.assertEqual(self.driver.get_window_rect(), rect)
        self.assertEqual(self.driver.get_cookie("cf_clearance")["value"], "mock")
        events = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertEqual(
            [event["event"] for event in events],
            ["verification_required", "verification_complete"],
        )
        expected = "vnc" if self.service.display is not None else "window"
        self.assertEqual(events[0]["presentation"], expected)

        # The clearance survives: navigating again needs no verification.
        self.driver.get(self.base + "/challenge")
        self.assertFalse(self.controller()[0].ensure_verified())

    def test_header_confirmed_challenge_is_completed(self):
        self.driver.get(self.base + "/header-only")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        controller, _stream = self.controller()
        with patch.object(verification, "listen_for_commands"):
            self.assertTrue(controller.ensure_verified())
        self.assertEqual(self.driver.title, "Wrapper")

    def test_unsolved_challenge_times_out(self):
        self.driver.get(self.base + "/stuck?delay=600000")
        controller, stream = self.controller(timeout=2)
        with (
            patch.object(verification, "listen_for_commands"),
            self.assertRaisesRegex(VerificationError, "2 seconds"),
        ):
            controller.ensure_verified()
        self.assertEqual(
            json.loads(stream.getvalue().splitlines()[-1])["reason"], "timeout"
        )

    def test_ordinary_page_shows_nothing(self):
        self.driver.get(self.base + "/")
        controller, stream = self.controller()
        self.assertFalse(controller.ensure_verified())
        self.assertEqual(stream.getvalue(), "")


ANUBIS_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "anubis"
ANUBIS_PREFIX = "/.within.website/x/cmd/anubis/"
AUTH_COOKIE = "techaro.lol-anubis-auth-test"
# The difficulty FlashThemes used on 2026-11-11 (about a second in Chromium 87).
DIFFICULTY = 4


class MockAnubis(BaseHTTPRequestHandler):
    """A minimal Anubis: issues challenges and verifies the proof-of-work.

    Routes below /site/ are protected. Variants:
      /site/            pass sets the auth cookie (normal behavior)
      /loop/            the pass is never accepted (a new challenge each time)
      /bogus/           an algorithm the client does not know
      /no-workers/      a browser without Web Workers
      /stall/           the challenge script never starts; a timer stands in
                        for the user completing it in the shown browser
      /denied/          Anubis' access-denied error page
    """

    challenges: dict[str, tuple[str, int, str]] = {}
    tokens: set[str] = set()
    passes: list[str] = []

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path.startswith(ANUBIS_PREFIX + "static/"):
            return self._static(path[len(ANUBIS_PREFIX + "static/") :])
        if path == ANUBIS_PREFIX + "api/pass-challenge":
            return self._pass(parse_qs(query))
        route = "/" + path.strip("/").split("/", 1)[0] + "/"
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        if AUTH_COOKIE in cookie and cookie[AUTH_COOKIE].value in self.tokens:
            return self._html(200, self._fixture("site.html"))
        if route == "/denied/":
            return self._html(403, self._fixture("error.html"))
        return self._challenge(route)

    def _challenge(self, route):
        challenge_id = uuid.uuid4().hex
        random_data = secrets.token_hex(32)
        algorithm = "bogus" if route == "/bogus/" else "fast"
        self.challenges[challenge_id] = (random_data, DIFFICULTY, route)
        data = {
            "rules": {"algorithm": algorithm, "difficulty": DIFFICULTY},
            "challenge": {"id": challenge_id, "randomData": random_data},
        }
        head = ""
        if route == "/no-workers/":
            head = "<script>window.Worker = undefined;</script>"
        main = (
            '<script id="anubis-main" defer type="module" '
            f'src="{ANUBIS_PREFIX}static/js/main.mjs?cacheBuster=v1.28.3-test"></script>'
        )
        if route == "/stall/":
            main = (
                "<script>setTimeout(function () { location.replace("
                f"'{ANUBIS_PREFIX}api/pass-challenge?id=manual&redir=' + "
                "encodeURIComponent(location.href)); }, 6000);</script>"
            )
        page = (
            self._fixture("challenge.html")
            .replace("{{CHALLENGE}}", json.dumps(data))
            .replace("{{HEAD}}", head)
            .replace("{{MAIN}}", main)
        )
        self._html(200, page)

    def _pass(self, query):
        def value(name):
            return query.get(name, [""])[0]

        redirect = value("redir") or "/site/"
        challenge_id = value("id")
        if challenge_id == "manual":
            accepted = True
        else:
            random_data, difficulty, route = self.challenges.pop(
                challenge_id, ("", 0, "")
            )
            digest = hashlib.sha256((random_data + value("nonce")).encode()).hexdigest()
            accepted = (
                bool(random_data)
                and digest == value("response")
                and digest.startswith("0" * difficulty)
                and route != "/loop/"
            )
        self.passes.append(challenge_id)
        self.send_response(302)
        self.send_header("Location", redirect)
        if accepted:
            token = secrets.token_hex(16)
            self.tokens.add(token)
            self.send_header("Set-Cookie", f"{AUTH_COOKIE}={token}; Path=/; HttpOnly")
        self.end_headers()

    def _static(self, relative):
        path = (ANUBIS_FIXTURES / "static" / relative).resolve()
        if ANUBIS_FIXTURES not in path.parents or not path.is_file():
            self.send_error(404)
            return
        if path.name == "sha256.mjs":
            # A remote site's latency. The proof-of-work starts once its
            # worker source arrives; locally a lucky nonce could otherwise
            # finish before the challenge is first inspected.
            time.sleep(4.0)
        types = {".mjs": "text/javascript", ".json": "application/json"}
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", types.get(path.suffix, "text/plain"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    @staticmethod
    def _fixture(name):
        loader = (ANUBIS_FIXTURES / "cloudflare_loader.html").read_text(
            encoding="utf-8"
        )
        return (
            (ANUBIS_FIXTURES / name)
            .read_text(encoding="utf-8")
            .replace("{{CLOUDFLARE_LOADER}}", loader)
        )

    def _html(self, status, page):
        data = page.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args):
        pass


@unittest.skipUnless(
    _browser_available(),
    "Set GOEXPORT_BROWSER_TESTS=1 with the bundled Chromium installed.",
)
class AnubisBrowserTests(unittest.TestCase):
    """Anubis' real challenge code in GoExport's Chromium 87."""

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockAnubis)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.service = BrowserService(
            config.CHROME_PATH,
            config.CHROMEDRIVER_PATH,
            config.FLASH_PLUGIN_PATH,
            config.FLASH_PLUGIN_VERSION,
            width=800,
            height=600,
        )
        cls.driver = cls.service.create_driver()

    @classmethod
    def tearDownClass(cls):
        cls.service.close()
        cls.server.shutdown()

    def setUp(self):
        self.driver.delete_all_cookies()
        MockAnubis.passes.clear()

    def controller(self, timeout=60, automatic=30, interactive=True):
        stream = io.StringIO()
        presenters = []

        def presenter():
            presenters.append(verification.create_presenter(self.service, self.driver))
            return presenters[-1]

        controller = VerificationController(
            self.driver,
            presenter,
            Reporter(json_mode=True, stream=stream),
            timeout_seconds=timeout,
            interactive=interactive,
            cancel_event=threading.Event(),
            poll_seconds=0.25,
            automatic_timeout_seconds=automatic,
        )
        return controller, stream, presenters

    @staticmethod
    def events(stream):
        return [json.loads(line) for line in stream.getvalue().splitlines()]

    def wait_for(self, kind, path, seconds=15):
        detector = ChallengeDetector()
        self.driver.get(self.base + path)
        deadline = time.monotonic() + seconds
        while True:
            result = detector.detect(self.driver)
            if result.kind is kind or time.monotonic() > deadline:
                return result
            time.sleep(0.25)

    def test_proof_of_work_completes_automatically_in_the_same_session(self):
        self.driver.get(self.base + "/site/movie?id=42")
        session = self.driver.session_id
        rect = self.driver.get_window_rect()
        controller, stream, presenters = self.controller()

        with patch.object(verification, "listen_for_commands"):
            self.assertTrue(controller.ensure_verified())

        self.assertEqual(presenters, [])
        self.assertTrue(self.driver.title.startswith("FlashThemes"))
        self.assertEqual(self.driver.current_url, self.base + "/site/movie?id=42")
        self.assertEqual(self.driver.session_id, session)
        self.assertEqual(self.driver.get_window_rect(), rect)
        self.assertIsNotNone(self.driver.get_cookie(AUTH_COOKIE))
        self.assertEqual(len(MockAnubis.passes), 1)
        events = self.events(stream)
        self.assertEqual(
            [(e["event"], e.get("interaction")) for e in events],
            [("verification_required", "automatic"), ("verification_complete", None)],
        )
        self.assertEqual({e["provider"] for e in events}, {"anubis"})

        # The pass is kept: the page loads directly from now on.
        self.driver.get(self.base + "/site/other")
        self.assertFalse(self.controller()[0].ensure_verified())

    def test_real_detection_script_classifies_anubis_pages(self):
        stalled = self.wait_for(ChallengeKind.CHALLENGE, "/stall/")
        self.assertIs(stalled.provider, ChallengeProvider.ANUBIS)
        self.assertEqual(stalled.algorithm, "fast")
        self.assertIsNotNone(stalled.challenge_id)

        bogus = self.wait_for(ChallengeKind.FAILED, "/bogus/")
        self.assertIs(bogus.kind, ChallengeKind.FAILED)
        self.assertIn("Challenge error", bogus.detail)

        no_workers = self.wait_for(ChallengeKind.UNSUPPORTED, "/no-workers/")
        self.assertIs(no_workers.kind, ChallengeKind.UNSUPPORTED)
        self.assertIn("Web Workers", no_workers.detail)

        denied = self.wait_for(ChallengeKind.BLOCKED, "/denied/")
        self.assertIs(denied.kind, ChallengeKind.BLOCKED)
        self.assertIs(denied.provider, ChallengeProvider.ANUBIS)

    def test_verified_site_with_cloudflare_loader_is_not_a_challenge(self):
        self.driver.get(self.base + "/site/")
        controller, _stream, _presenters = self.controller()
        with patch.object(verification, "listen_for_commands"):
            controller.ensure_verified()
        time.sleep(0.5)  # let the stand-in loader insert its iframe script
        result = ChallengeDetector().detect(self.driver)
        self.assertIs(result.kind, ChallengeKind.NONE)

    def test_rejected_passes_stop_after_repeated_challenges(self):
        self.driver.get(self.base + "/loop/")
        controller, stream, presenters = self.controller()
        with (
            patch.object(verification, "listen_for_commands"),
            self.assertRaisesRegex(VerificationError, "not being accepted"),
        ):
            controller.ensure_verified()
        self.assertEqual(presenters, [])
        self.assertLessEqual(len(MockAnubis.passes), MAX_ANUBIS_CHALLENGES + 1)
        self.assertEqual(self.events(stream)[-1]["reason"], "repeated")

    def test_challenge_error_fails_without_showing_the_browser(self):
        self.driver.get(self.base + "/bogus/")
        controller, stream, presenters = self.controller()
        with (
            patch.object(verification, "listen_for_commands"),
            self.assertRaisesRegex(VerificationError, "Anubis verification failed"),
        ):
            controller.ensure_verified()
        self.assertEqual(presenters, [])

    def test_missing_browser_feature_reports_chromium_87_limitation(self):
        self.driver.get(self.base + "/no-workers/")
        controller, stream, _presenters = self.controller()
        with (
            patch.object(verification, "listen_for_commands"),
            self.assertRaisesRegex(VerificationError, "Chromium 87"),
        ):
            controller.ensure_verified()
        self.assertEqual(self.events(stream)[-1]["reason"], "unsupported")

    def test_stalled_challenge_is_shown_and_resumes_after_manual_completion(self):
        self.driver.get(self.base + "/stall/")
        controller, stream, presenters = self.controller(timeout=30)
        with (
            patch.object(verification, "listen_for_commands"),
            patch.object(verification, "ANUBIS_STALL_SECONDS", 2),
        ):
            self.assertTrue(controller.ensure_verified())
        self.assertEqual(len(presenters), 1)
        self.assertTrue(self.driver.title.startswith("FlashThemes"))
        interactions = [
            e.get("interaction")
            for e in self.events(stream)
            if e["event"] == "verification_required"
        ]
        self.assertEqual(interactions, ["automatic", "manual"])

    def test_unattended_mode_does_not_show_a_stalled_challenge(self):
        self.driver.get(self.base + "/stall/")
        controller, _stream, presenters = self.controller(interactive=False)
        with (
            patch.object(verification, "listen_for_commands"),
            patch.object(verification, "ANUBIS_STALL_SECONDS", 2),
            self.assertRaisesRegex(VerificationError, "did not complete automatically"),
        ):
            controller.ensure_verified()
        self.assertEqual(presenters, [])


if __name__ == "__main__":
    unittest.main()
