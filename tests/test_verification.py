import io
import json
import threading
import time
import unittest
from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import Mock, patch

from goexport import cli, config
from goexport.reporting import Reporter
from goexport.services import verification
from goexport.services.browser import BrowserService
from goexport.services.challenge import (
    NO_CHALLENGE,
    BrowserUnavailableError,
    ChallengeKind,
    ChallengeResult,
)
from goexport.services.flash import PlayerReplacedError, await_stopped
from goexport.services.recorder import RecordingService
from goexport.services.verification import (
    PresentationError,
    VerificationCancelled,
    VerificationController,
    VerificationError,
    VerificationInterruptedError,
    VerificationState,
    create_presenter,
    explain_interruption,
)

CHALLENGE = ChallengeResult(ChallengeKind.CHALLENGE, "title", "https://w.example/")
LOADING = ChallengeResult(ChallengeKind.NONE, url="https://w.example/", ready=False)


class FakeDetector:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = 0

    def detect(self, _driver):
        self.calls += 1
        result = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        if isinstance(result, BaseException):
            raise result
        return result


class FakePresenter:
    presentation = "window"
    instructions = "Complete the check in the Chromium window."

    def __init__(self, polls=()):
        self.polls = list(polls)
        self.shown = 0
        self.restored = 0

    def show(self):
        self.shown += 1

    def poll(self):
        return self.polls.pop(0) if self.polls else None

    def restore(self):
        self.restored += 1


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class InstantEvent(threading.Event):
    """Advance a fake clock instead of sleeping between polls."""

    def __init__(self, clock):
        super().__init__()
        self.clock = clock

    def wait(self, timeout=None):
        self.clock.now += timeout or 0
        return self.is_set()


class ControllerTests(unittest.TestCase):
    def make(self, detector, presenter=None, timeout=60, interactive=True):
        stream = io.StringIO()
        clock = FakeClock()
        presenter = presenter or FakePresenter()
        factory = Mock(return_value=presenter)
        controller = VerificationController(
            driver=Mock(name="driver"),
            presenter_factory=factory,
            reporter=Reporter(json_mode=True, stream=stream),
            timeout_seconds=timeout,
            interactive=interactive,
            detector=detector,
            cancel_event=InstantEvent(clock),
            clock=clock,
        )
        return controller, presenter, factory, stream

    @staticmethod
    def events(stream):
        return [json.loads(line) for line in stream.getvalue().splitlines()]

    def test_no_challenge_shows_nothing(self):
        controller, _presenter, factory, stream = self.make(FakeDetector(NO_CHALLENGE))

        self.assertFalse(controller.ensure_verified())

        factory.assert_not_called()
        self.assertEqual(stream.getvalue(), "")
        self.assertIs(controller.state, VerificationState.IDLE)

    def test_successful_verification_resumes_after_stable_page(self):
        detector = FakeDetector(
            CHALLENGE, CHALLENGE, LOADING, NO_CHALLENGE, NO_CHALLENGE
        )
        controller, presenter, _factory, stream = self.make(detector)

        with patch.object(verification, "listen_for_commands") as listen:
            self.assertTrue(controller.ensure_verified())

        listen.assert_called_once_with()
        self.assertEqual((presenter.shown, presenter.restored), (1, 1))
        self.assertIs(controller.state, VerificationState.RESUMED)
        self.assertEqual(detector.calls, 5)
        events = self.events(stream)
        self.assertEqual(
            [event["event"] for event in events],
            ["verification_required", "verification_complete"],
        )
        self.assertEqual(events[0]["reason"], "cloudflare")
        self.assertEqual(events[0]["presentation"], "window")
        self.assertEqual(events[0]["timeout"], 60)
        self.assertIn("Chromium window", events[0]["message"])

    def test_single_clean_poll_during_reload_does_not_resume(self):
        detector = FakeDetector(
            CHALLENGE, NO_CHALLENGE, CHALLENGE, NO_CHALLENGE, NO_CHALLENGE
        )
        controller, _presenter, _factory, _stream = self.make(detector)
        with patch.object(verification, "listen_for_commands"):
            controller.ensure_verified()
        self.assertEqual(detector.calls, 5)

    def test_timeout_fails_and_restores_presentation(self):
        controller, presenter, _factory, stream = self.make(
            FakeDetector(CHALLENGE), timeout=5
        )
        with (
            patch.object(verification, "listen_for_commands"),
            self.assertRaises(VerificationError) as raised,
        ):
            controller.ensure_verified()

        self.assertIs(raised.exception.state, VerificationState.TIMEOUT)
        self.assertIn("5 seconds", str(raised.exception))
        self.assertIn("Chromium 87", str(raised.exception))
        self.assertEqual(presenter.restored, 1)
        failed = self.events(stream)[-1]
        self.assertEqual(failed["event"], "verification_failed")
        self.assertEqual(failed["reason"], "timeout")

    def test_zero_timeout_waits_indefinitely(self):
        results = [CHALLENGE] * 500 + [NO_CHALLENGE]
        controller, _presenter, _factory, stream = self.make(
            FakeDetector(*results), timeout=0
        )
        with patch.object(verification, "listen_for_commands"):
            self.assertTrue(controller.ensure_verified())
        self.assertIsNone(self.events(stream)[0]["timeout"])

    def test_cancellation_stops_waiting(self):
        controller, presenter, _factory, stream = self.make(FakeDetector(CHALLENGE))
        controller.cancel_event.set()
        with (
            patch.object(verification, "listen_for_commands"),
            self.assertRaises(VerificationCancelled),
        ):
            controller.ensure_verified()
        self.assertIs(controller.state, VerificationState.CANCELLED)
        self.assertEqual(presenter.restored, 1)
        self.assertEqual(self.events(stream)[-1]["reason"], "cancelled")

    def test_closing_the_viewer_cancels(self):
        presenter = FakePresenter(polls=[None, "closed"])
        controller, _presenter, _factory, _stream = self.make(
            FakeDetector(CHALLENGE), presenter
        )
        with (
            patch.object(verification, "listen_for_commands"),
            self.assertRaisesRegex(VerificationCancelled, "window was closed"),
        ):
            controller.ensure_verified()
        self.assertEqual(presenter.restored, 1)

    def test_presentation_failure_is_reported(self):
        presenter = FakePresenter(polls=["the VNC server stopped"])
        controller, _presenter, _factory, stream = self.make(
            FakeDetector(CHALLENGE), presenter
        )
        with (
            patch.object(verification, "listen_for_commands"),
            self.assertRaisesRegex(VerificationError, "VNC server stopped"),
        ):
            controller.ensure_verified()
        self.assertIs(controller.state, VerificationState.FAILED)
        self.assertEqual(self.events(stream)[-1]["reason"], "failed")

    def test_presenter_that_cannot_start_fails_without_waiting(self):
        controller, _presenter, factory, stream = self.make(FakeDetector(CHALLENGE))
        factory.side_effect = PresentationError("No desktop display")
        with self.assertRaisesRegex(VerificationError, "No desktop display"):
            controller.ensure_verified()
        self.assertEqual(
            [event["event"] for event in self.events(stream)],
            ["verification_failed"],
        )

    def test_closed_browser_fails(self):
        detector = FakeDetector(CHALLENGE, BrowserUnavailableError("closed"))
        controller, presenter, _factory, _stream = self.make(detector)
        with (
            patch.object(verification, "listen_for_commands"),
            self.assertRaisesRegex(VerificationError, "cannot continue"),
        ):
            controller.ensure_verified()
        self.assertEqual(presenter.restored, 1)

    def test_blocked_and_unsupported_pages_fail_immediately(self):
        for kind, text in (
            (ChallengeKind.BLOCKED, "denied access"),
            (ChallengeKind.UNSUPPORTED, "Chromium 87"),
        ):
            controller, _presenter, factory, _stream = self.make(
                FakeDetector(ChallengeResult(kind, "x", "https://w.example/"))
            )
            with self.assertRaisesRegex(VerificationError, text):
                controller.ensure_verified()
            factory.assert_not_called()

    def test_unsupported_page_during_wait_fails(self):
        unsupported = ChallengeResult(ChallengeKind.UNSUPPORTED, "x", "https://w/")
        controller, presenter, _factory, _stream = self.make(
            FakeDetector(CHALLENGE, unsupported)
        )
        with (
            patch.object(verification, "listen_for_commands"),
            self.assertRaisesRegex(VerificationError, "unsupported"),
        ):
            controller.ensure_verified()
        self.assertEqual(presenter.restored, 1)

    def test_non_interactive_mode_fails_fast(self):
        controller, _presenter, factory, _stream = self.make(
            FakeDetector(CHALLENGE), interactive=False
        )
        with self.assertRaisesRegex(VerificationError, "interactive verification"):
            controller.ensure_verified()
        factory.assert_not_called()

    def test_controller_keeps_the_original_driver(self):
        detector = FakeDetector(CHALLENGE, NO_CHALLENGE, NO_CHALLENGE)
        controller, _presenter, _factory, _stream = self.make(detector)
        driver = controller.driver
        with patch.object(verification, "listen_for_commands"):
            controller.ensure_verified()
        self.assertIs(controller.driver, driver)

    def test_normal_mode_logs_instead_of_json(self):
        stream = io.StringIO()
        clock = FakeClock()
        controller = VerificationController(
            Mock(),
            FakePresenter,
            Reporter(json_mode=False, stream=stream),
            timeout_seconds=30,
            detector=FakeDetector(CHALLENGE, NO_CHALLENGE, NO_CHALLENGE),
            cancel_event=InstantEvent(clock),
            clock=clock,
        )
        with (
            patch.object(verification, "listen_for_commands") as listen,
            self.assertLogs("goexport.verification", "WARNING") as logs,
        ):
            controller.ensure_verified()
        listen.assert_not_called()
        self.assertEqual(stream.getvalue(), "")
        self.assertIn("Ctrl+C", logs.output[0])


class CommandListenerTests(unittest.TestCase):
    def test_cancel_command_sets_cancel_event(self):
        event = verification.CANCEL_EVENT
        event.clear()
        try:
            verification._read_commands(
                io.StringIO('not json\n{"command": "other"}\n{"command": "cancel"}\n')
            )
            self.assertTrue(event.is_set())
        finally:
            event.clear()

    def test_unrelated_commands_do_not_cancel(self):
        event = verification.CANCEL_EVENT
        event.clear()
        verification._read_commands(io.StringIO('{"command": "pause"}\n[]\n'))
        self.assertFalse(event.is_set())


class PresenterSelectionTests(unittest.TestCase):
    def test_linux_xvfb_uses_vnc(self):
        display = SimpleNamespace(active=True)
        with patch.object(config, "SYSTEM", "Linux"):
            presenter = create_presenter(SimpleNamespace(display=display), Mock())
        self.assertEqual(presenter.presentation, "vnc")

    def test_windows_and_linux_desktop_use_the_browser_window(self):
        for system, display in (("Windows", None), ("Linux", None)):
            with patch.object(config, "SYSTEM", system):
                presenter = create_presenter(SimpleNamespace(display=display), Mock())
            self.assertEqual(presenter.presentation, "window")


class InterruptionTests(unittest.TestCase):
    def test_challenge_after_start_is_explained(self):
        driver = Mock()
        driver.execute_script.return_value = {
            "url": "https://w.example/",
            "title": "Just a moment...",
            "readyState": "complete",
        }
        with self.assertRaisesRegex(VerificationInterruptedError, "Run the export"):
            explain_interruption(driver, RuntimeError("seek failed"))

    def test_other_failures_are_left_alone(self):
        driver = Mock()
        driver.execute_script.return_value = {"url": "https://w.example/"}
        explain_interruption(driver, RuntimeError("seek failed"))

    def test_stop_watcher_reports_a_replaced_player(self):
        driver = Mock()
        driver.execute_script.return_value = "replaced"
        with self.assertRaises(PlayerReplacedError):
            await_stopped(driver, poll_frequency=0.01)

    def test_stop_watcher_returns_on_stop(self):
        driver = Mock()
        driver.execute_script.side_effect = ["", "", "stopped"]
        await_stopped(driver, poll_frequency=0.01)
        self.assertEqual(driver.execute_script.call_count, 3)


class WorkflowTests(unittest.TestCase):
    def args(self, **values):
        defaults = dict(
            url="https://w.example/",
            output="final",
            format="mp4",
            resolution=(1280, 720),
            capture_backend="capturekit",
            verification_timeout=10,
            interactive_verification=True,
        )
        defaults.update(values)
        return Namespace(**defaults)

    def test_recording_verifies_before_any_browser_setup(self):
        recording = RecordingService(self.args())
        service = Mock()
        driver = service.create_driver.return_value
        order = []
        driver.get.side_effect = lambda _url: order.append("navigate")
        with (
            patch.object(recording, "_create_browser_service", return_value=service),
            patch(
                "goexport.services.recorder.verify_browser",
                side_effect=lambda *_a: order.append("verify"),
            ),
        ):
            recording._prepare_browser()
        self.assertEqual(order, ["navigate", "verify"])

    def test_flash_settings_round_trip_is_verified_before_injection(self):
        recording = RecordingService(self.args())
        service = Mock(spec=BrowserService)
        order = []
        service.enable_flash.side_effect = lambda _d: order.append("flash")
        service.inject_dom.side_effect = lambda *_a: order.append("inject")
        with (
            patch(
                "goexport.services.recorder.verify_browser",
                side_effect=lambda *_a: order.append("verify"),
            ),
            patch("goexport.services.recorder.await_player_ready"),
            patch.object(recording, "_build_replacements", return_value={}),
        ):
            recording._finish_browser_setup(service, Mock())
        self.assertEqual(order, ["flash", "verify", "inject"])

    def test_failed_verification_closes_the_browser(self):
        recording = RecordingService(self.args())
        service = Mock()
        with (
            patch.object(recording, "_create_browser_service", return_value=service),
            patch(
                "goexport.services.recorder.verify_browser",
                side_effect=VerificationError("timeout", VerificationState.TIMEOUT),
            ),
            self.assertRaises(VerificationError),
        ):
            recording._prepare_browser()
        service.close.assert_called_once_with()

    def test_challenge_during_recording_is_not_silently_recorded(self):
        recording = RecordingService(self.args())
        driver = Mock()
        backend = Mock()

        def capture(_started, stopped, _total):
            stopped.wait(5)
            return Mock()

        backend.capture_until_stopped.side_effect = capture
        with (
            patch("goexport.services.recorder.await_started"),
            patch("goexport.services.recorder.get_total_frames", return_value=24),
            patch(
                "goexport.services.recorder.await_stopped",
                side_effect=PlayerReplacedError("gone"),
            ),
            patch(
                "goexport.services.recorder.explain_interruption",
                side_effect=VerificationInterruptedError("challenge"),
            ) as explain,
            self.assertRaises(VerificationInterruptedError),
        ):
            recording._record_playback(driver, backend)
        explain.assert_called_once()

    def test_export_verifies_after_navigation_and_flash_setup(self):
        from goexport.commands import export

        order = []
        args = Namespace(
            ugc_path="ugc",
            assets="assets",
            ffmpeg_path="ffmpeg",
            movie_xml="movie.xml",
            chrome_path="chrome",
            chromedriver_path="driver",
            flash_plugin_path="flash",
            flash_plugin_version="32",
            resolution=(1280, 720),
            url="https://w.example/",
            swf_url="swf",
            is_wide=True,
            api_url="api",
            store_path="store",
            client_theme_path="theme",
            movie_id="m",
            format="mp4",
        )
        browser = Mock(spec=BrowserService)
        driver = browser.create_driver.return_value
        driver.get.side_effect = lambda _u: order.append("navigate")
        browser.enable_flash.side_effect = lambda _d: order.append("flash")
        browser.inject_dom.side_effect = lambda *_a: order.append("inject")
        with (
            patch.object(export, "BrowserService", return_value=browser),
            patch.object(export, "TimelineBuilder"),
            patch.object(export, "AudioProcessor"),
            patch.object(export, "FFmpegAudioEncoder"),
            patch.object(export, "FFmpegVideoEncoder"),
            patch.object(export, "FFmpegMuxer"),
            patch.object(export, "Renderer"),
            patch.object(export, "await_started"),
            patch.object(
                export,
                "verify_browser",
                side_effect=lambda *_a: order.append("verify"),
            ),
        ):
            export.export_video(args)
        self.assertEqual(order, ["navigate", "verify", "flash", "verify", "inject"])


class CliTests(unittest.TestCase):
    def test_cancelled_verification_exits_130_with_json_error(self):
        stdout = io.StringIO()
        command = Mock(side_effect=VerificationCancelled("closed the viewer"))
        args = Namespace(json=True, verbose=False, func=command)
        with (
            patch.object(cli, "build_parser") as parser,
            patch.object(cli, "setup_logging"),
            patch.object(cli, "install_termination_handler"),
            patch("sys.stdout", stdout),
        ):
            parser.return_value.parse_args.return_value = args
            self.assertEqual(cli.main(), 130)
        event = json.loads(stdout.getvalue().splitlines()[-1])
        self.assertEqual(
            event, {"event": "error", "message": "closed the viewer", "code": 130}
        )

    def test_verification_options_parse(self):
        parser = cli.build_parser()
        args = parser.parse_args(
            [
                "record",
                "-id",
                "1",
                "--verification-timeout",
                "0",
                "--no-interactive-verification",
            ]
        )
        self.assertEqual(args.verification_timeout, 0)
        self.assertFalse(args.interactive_verification)
        defaults = parser.parse_args(["record", "-id", "1"])
        self.assertEqual(defaults.verification_timeout, config.VERIFICATION_TIMEOUT)
        self.assertTrue(defaults.interactive_verification)
        with (
            patch("sys.stderr", io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            parser.parse_args(["record", "-id", "1", "--verification-timeout", "-1"])


class ListenerThreadTests(unittest.TestCase):
    def test_listener_starts_once(self):
        stream = io.StringIO("")
        with patch.object(verification, "_listener", None):
            verification.listen_for_commands(stream)
            first = verification._listener
            verification.listen_for_commands(stream)
            self.assertIs(verification._listener, first)
            first.join(1)
        time.sleep(0)


if __name__ == "__main__":
    unittest.main()
