import io
import json
import threading
import unittest
from unittest.mock import Mock, patch

from goexport import cli, config
from goexport.reporting import Reporter
from goexport.services import verification
from goexport.services.challenge import (
    NO_CHALLENGE,
    ChallengeKind,
    ChallengeProvider,
    ChallengeResult,
    classify,
)
from goexport.services.verification import (
    ANUBIS_STALL_SECONDS,
    MAX_ANUBIS_CHALLENGES,
    VerificationCancelled,
    VerificationController,
    VerificationError,
    VerificationInterruptedError,
    VerificationState,
    explain_interruption,
)


def anubis(**overrides):
    values = {
        "challenge": True,
        "algorithm": "fast",
        "difficulty": 4,
        "challengeId": "01a1cd60",
        "version": True,
        "script": True,
        "assets": True,
        "booted": True,
        "rejected": False,
        "scriptError": False,
        "heading": "Making sure you're not a bot!",
        "status": "Calculating... Difficulty: 4, Speed: 812.000kH/s",
        "progress": "12.5",
    }
    values.update(overrides)
    return values


def page(anubis_signals=None, **overrides):
    values = {
        "url": "https://flashthemes.net/",
        "title": "Making sure you're not a bot!",
        "readyState": "complete",
        "strong": [],
        "weak": [],
        "challengeOptions": False,
        "text": "",
        "anubis": anubis_signals if anubis_signals is not None else anubis(),
    }
    values.update(overrides)
    return values


NOT_ANUBIS = {
    "challenge": False,
    "version": False,
    "script": False,
    "assets": False,
    "rejected": False,
    "scriptError": False,
}


class AnubisDetectionTests(unittest.TestCase):
    def test_challenge_page_is_an_automatic_anubis_challenge(self):
        result = classify(page())
        self.assertIs(result.kind, ChallengeKind.CHALLENGE)
        self.assertIs(result.provider, ChallengeProvider.ANUBIS)
        self.assertTrue(result.automatic)
        self.assertEqual(result.algorithm, "fast")
        self.assertEqual(result.challenge_id, "01a1cd60")
        self.assertIn("difficulty 4", result.reason)

    def test_detection_does_not_depend_on_the_title(self):
        localized = page(
            title="Un instant…", anubis_signals=anubis(heading="Vérification")
        )
        self.assertTrue(classify(localized).automatic)

    def test_legacy_string_challenge_is_detected(self):
        legacy = page(anubis_signals=anubis(challengeId="9f8e7d", progress=None))
        self.assertEqual(classify(legacy).challenge_id, "9f8e7d")

    def test_version_and_script_without_challenge_data_is_a_challenge(self):
        result = classify(page(anubis_signals=anubis(challenge=False, algorithm=None)))
        self.assertIs(result.kind, ChallengeKind.CHALLENGE)
        self.assertIs(result.provider, ChallengeProvider.ANUBIS)

    def test_missing_web_workers_is_unsupported(self):
        rejected = anubis(
            rejected=True,
            heading="Missing feature Web Workers",
            status="Your browser doesn't support web workers.",
        )
        result = classify(page(anubis_signals=rejected))
        self.assertIs(result.kind, ChallengeKind.UNSUPPORTED)
        self.assertIn("Web Workers", result.detail)

    def test_worker_start_failure_is_unsupported(self):
        rejected = anubis(
            rejected=True,
            heading="Calculation error!",
            status=(
                "Failed to calculate challenge: anubis: could not start proof of "
                "work worker: SecurityError (is your browser out of date?)"
            ),
        )
        self.assertIs(
            classify(page(anubis_signals=rejected)).kind, ChallengeKind.UNSUPPORTED
        )

    def test_other_challenge_errors_fail(self):
        rejected = anubis(
            rejected=True,
            heading="Challenge error!",
            status="Failed to resolve check algorithm.",
        )
        result = classify(page(anubis_signals=rejected))
        self.assertIs(result.kind, ChallengeKind.FAILED)
        self.assertIs(result.provider, ChallengeProvider.ANUBIS)

    def test_script_load_failure_fails(self):
        failed = anubis(scriptError=True, status="Loading...")
        self.assertIs(classify(page(anubis_signals=failed)).kind, ChallengeKind.FAILED)

    def test_access_denied_error_page_is_a_block(self):
        denied = anubis(
            challenge=False,
            script=False,
            rejected=True,
            heading="Oh noes!",
            status="Access Denied: error code 4f2a",
        )
        result = classify(page(anubis_signals=denied, title="Oh noes!"))
        self.assertIs(result.kind, ChallengeKind.BLOCKED)
        self.assertIs(result.provider, ChallengeProvider.ANUBIS)

    def test_client_error_page_is_unsupported(self):
        client = anubis(
            challenge=False,
            script=False,
            rejected=True,
            heading="Oh noes!",
            status="Client Error: Please ensure your browser is up to date.",
        )
        self.assertIs(
            classify(page(anubis_signals=client)).kind, ChallengeKind.UNSUPPORTED
        )

    def test_pass_challenge_redirect_is_not_the_real_page(self):
        redirect = page(
            url="https://flashthemes.net/.within.website/x/cmd/anubis/api/pass-challenge?id=1",
            anubis_signals=NOT_ANUBIS,
            title="",
        )
        result = classify(redirect)
        self.assertIs(result.kind, ChallengeKind.NONE)
        self.assertFalse(result.ready)

    def test_real_flashthemes_page_is_not_a_challenge(self):
        real = page(
            title="FlashThemes - Make your own cartoons and animations easily.",
            anubis_signals=NOT_ANUBIS,
            text="Make your own cartoons. Protected by Anubis From Techaro.",
        )
        self.assertIs(classify(real).kind, ChallengeKind.NONE)

    def test_pages_mentioning_or_linking_to_anubis_are_not_challenges(self):
        article = page(
            title="Why we deployed Anubis",
            anubis_signals=dict(NOT_ANUBIS, assets=False),
            text="Making sure you're not a bot! Anubis proof-of-work Calculating...",
        )
        self.assertIs(classify(article).kind, ChallengeKind.NONE)
        assets_only = page(anubis_signals=dict(NOT_ANUBIS, assets=True), title="Blog")
        self.assertIs(classify(assets_only).kind, ChallengeKind.NONE)
        version_only = page(anubis_signals=dict(NOT_ANUBIS, version=True), title="Blog")
        self.assertIs(classify(version_only).kind, ChallengeKind.NONE)

    def test_reject_image_on_unrelated_page_is_ignored(self):
        unrelated = dict(NOT_ANUBIS, rejected=True)
        self.assertIs(classify(page(anubis_signals=unrelated)).kind, ChallengeKind.NONE)

    def test_cloudflare_results_keep_their_provider(self):
        cloudflare = page(anubis_signals=NOT_ANUBIS, title="Just a moment...")
        result = classify(cloudflare)
        self.assertIs(result.provider, ChallengeProvider.CLOUDFLARE)
        self.assertFalse(result.automatic)

    def test_missing_anubis_signals_keep_cloudflare_detection(self):
        signals = page(title="Just a moment...")
        del signals["anubis"]
        self.assertIs(classify(signals).provider, ChallengeProvider.CLOUDFLARE)


def challenge(challenge_id="c1", progress="10", status="Calculating..."):
    return ChallengeResult(
        ChallengeKind.CHALLENGE,
        "Anubis fast challenge (difficulty 4)",
        "https://flashthemes.net/",
        True,
        ChallengeProvider.ANUBIS,
        f"Making sure you're not a bot! {status}",
        "fast",
        challenge_id,
        progress,
    )


REDIRECTING = ChallengeResult(ChallengeKind.NONE, url="https://ft/", ready=False)
CLOUDFLARE = ChallengeResult(
    ChallengeKind.CHALLENGE,
    "title",
    "https://flashthemes.net/",
    provider=ChallengeProvider.CLOUDFLARE,
)


class Detector:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = 0

    def detect(self, _driver):
        self.calls += 1
        return self.results.pop(0) if len(self.results) > 1 else self.results[0]


class Presenter:
    presentation = "vnc"
    instructions = "Complete the check in the GoExport verification viewer window."

    def __init__(self):
        self.shown = self.restored = 0

    def show(self):
        self.shown += 1

    def poll(self):
        return None

    def restore(self):
        self.restored += 1


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class SteppingEvent(threading.Event):
    def __init__(self, clock):
        super().__init__()
        self.clock = clock

    def wait(self, timeout=None):
        self.clock.now += timeout or 0
        return self.is_set()


class AnubisControllerTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(verification, "listen_for_commands")
        patcher.start()
        self.addCleanup(patcher.stop)

    def make(self, *results, timeout=300, automatic=60, interactive=True):
        clock = Clock()
        self.stream = io.StringIO()
        self.presenter = Presenter()
        self.factory = Mock(return_value=self.presenter)
        self.detector = Detector(*results)
        return VerificationController(
            Mock(name="driver"),
            self.factory,
            Reporter(json_mode=True, stream=self.stream),
            timeout_seconds=timeout,
            interactive=interactive,
            detector=self.detector,
            cancel_event=SteppingEvent(clock),
            clock=clock,
            automatic_timeout_seconds=automatic,
        )

    def events(self):
        return [json.loads(line) for line in self.stream.getvalue().splitlines()]

    def test_proof_of_work_completes_without_showing_the_browser(self):
        controller = self.make(
            challenge(progress="10"),
            challenge(progress="60"),
            REDIRECTING,
            NO_CHALLENGE,
            NO_CHALLENGE,
        )

        self.assertTrue(controller.ensure_verified())

        self.factory.assert_not_called()
        self.assertIs(controller.state, VerificationState.RESUMED)
        events = self.events()
        self.assertEqual(
            [event["event"] for event in events],
            ["verification_required", "verification_complete"],
        )
        self.assertEqual(events[0]["provider"], "anubis")
        self.assertEqual(events[0]["reason"], "anubis")
        self.assertEqual(events[0]["interaction"], "automatic")
        self.assertIsNone(events[0]["presentation"])
        self.assertEqual(events[0]["message"], "Anubis verification is in progress.")
        self.assertEqual(events[1]["provider"], "anubis")

    def test_stalled_proof_of_work_falls_back_to_manual_verification(self):
        stalled = [challenge(progress="40")] * (ANUBIS_STALL_SECONDS + 2)
        controller = self.make(*stalled, NO_CHALLENGE, NO_CHALLENGE)

        self.assertTrue(controller.ensure_verified())

        self.assertEqual((self.presenter.shown, self.presenter.restored), (1, 1))
        required = [e for e in self.events() if e["event"] == "verification_required"]
        self.assertEqual([e["interaction"] for e in required], ["automatic", "manual"])
        self.assertEqual(required[1]["provider"], "anubis")
        self.assertEqual(required[1]["presentation"], "vnc")
        self.assertIn("no progress", required[1]["message"])
        self.assertIn("verification viewer", required[1]["message"])

    def test_progressing_challenge_is_not_considered_stalled(self):
        moving = [challenge(progress=str(n)) for n in range(40)]
        controller = self.make(*moving, NO_CHALLENGE, NO_CHALLENGE, automatic=0)
        self.assertTrue(controller.ensure_verified())
        self.factory.assert_not_called()

    def test_automatic_window_expiry_asks_for_manual_help(self):
        moving = [challenge(progress=str(n)) for n in range(15)]
        controller = self.make(*moving, NO_CHALLENGE, NO_CHALLENGE, automatic=10)
        self.assertTrue(controller.ensure_verified())
        self.assertEqual(self.presenter.shown, 1)
        manual = self.events()[1]
        self.assertIn("did not finish within 10 seconds", manual["message"])
        self.assertLessEqual(manual["timeout"], 290)

    def test_non_interactive_mode_fails_when_automatic_verification_stalls(self):
        stalled = [challenge(progress="40")] * (ANUBIS_STALL_SECONDS + 2)
        controller = self.make(*stalled, interactive=False)
        with self.assertRaisesRegex(
            VerificationError, "did not complete automatically"
        ):
            controller.ensure_verified()
        self.factory.assert_not_called()

    def test_non_interactive_mode_still_completes_automatic_challenges(self):
        controller = self.make(
            challenge(), NO_CHALLENGE, NO_CHALLENGE, interactive=False
        )
        self.assertTrue(controller.ensure_verified())

    def test_repeated_challenges_stop_instead_of_looping(self):
        loop = []
        for number in range(MAX_ANUBIS_CHALLENGES + 2):
            loop += [challenge(challenge_id=f"c{number}"), REDIRECTING]
        controller = self.make(*loop)

        with self.assertRaisesRegex(VerificationError, "not being accepted"):
            controller.ensure_verified()

        self.factory.assert_not_called()
        failed = self.events()[-1]
        self.assertEqual(failed["reason"], "repeated")
        self.assertEqual(failed["provider"], "anubis")

    def test_reappearing_challenge_without_ids_counts_as_repeated(self):
        loop = []
        for _ in range(MAX_ANUBIS_CHALLENGES + 2):
            loop += [challenge(challenge_id=None), REDIRECTING]
        with self.assertRaisesRegex(VerificationError, "not being accepted"):
            self.make(*loop).ensure_verified()

    def test_one_reissued_challenge_is_tolerated(self):
        controller = self.make(
            challenge(challenge_id="c1"),
            REDIRECTING,
            challenge(challenge_id="c2"),
            REDIRECTING,
            NO_CHALLENGE,
            NO_CHALLENGE,
        )
        self.assertTrue(controller.ensure_verified())

    def test_chromium_87_incompatibility_fails_with_a_diagnostic(self):
        unsupported = ChallengeResult(
            ChallengeKind.UNSUPPORTED,
            "Anubis reports that this browser cannot run its check",
            "https://flashthemes.net/",
            provider=ChallengeProvider.ANUBIS,
            detail="Missing feature Web Workers",
        )
        controller = self.make(challenge(), unsupported)
        with self.assertRaises(VerificationError) as raised:
            controller.ensure_verified()
        message = str(raised.exception)
        self.assertIn("Chromium 87", message)
        self.assertIn("Missing feature Web Workers", message)
        self.factory.assert_not_called()
        self.assertEqual(self.detector.calls, 2)
        self.assertEqual(self.events()[-1]["reason"], "unsupported")

    def test_javascript_errors_fail_without_retrying(self):
        failed = ChallengeResult(
            ChallengeKind.FAILED,
            "Anubis challenge error",
            "https://flashthemes.net/",
            provider=ChallengeProvider.ANUBIS,
            detail="Calculation error! all proof of work workers failed at runtime",
        )
        controller = self.make(failed)
        with self.assertRaisesRegex(VerificationError, "workers failed at runtime"):
            controller.ensure_verified()
        self.assertEqual(self.detector.calls, 1)

    def test_access_denied_is_reported_as_an_anubis_block(self):
        blocked = ChallengeResult(
            ChallengeKind.BLOCKED,
            "Anubis access-denied page",
            "https://flashthemes.net/",
            provider=ChallengeProvider.ANUBIS,
            detail="Oh noes! Access Denied: error code 4f2a",
        )
        with self.assertRaisesRegex(VerificationError, "Anubis denied access"):
            self.make(blocked).ensure_verified()

    def test_overall_timeout_reports_the_last_anubis_status(self):
        moving = [
            challenge(progress=str(n), status=f"Speed: {n}kH/s") for n in range(30)
        ]
        controller = self.make(*moving, timeout=10, automatic=0)
        with self.assertRaises(VerificationError) as raised:
            controller.ensure_verified()
        self.assertIs(raised.exception.state, VerificationState.TIMEOUT)
        self.assertIn(
            "Anubis verification was not completed within 10", str(raised.exception)
        )
        self.assertIn("Speed:", str(raised.exception))

    def test_cancellation_during_automatic_verification(self):
        controller = self.make(challenge())
        controller.cancel_event.set()
        with self.assertRaises(VerificationCancelled):
            controller.ensure_verified()
        self.assertEqual(self.events()[-1]["provider"], "anubis")

    def test_cloudflare_challenge_after_anubis_is_shown_to_the_user(self):
        controller = self.make(challenge(), CLOUDFLARE, NO_CHALLENGE, NO_CHALLENGE)
        self.assertTrue(controller.ensure_verified())
        self.assertEqual(self.presenter.shown, 1)
        manual = self.events()[1]
        self.assertEqual(manual["provider"], "cloudflare")
        self.assertEqual(manual["interaction"], "manual")

    def test_page_still_redirecting_is_settled_before_deciding(self):
        # The pass was already being submitted when the page was first read.
        controller = self.make(REDIRECTING, REDIRECTING, NO_CHALLENGE)
        self.assertFalse(controller.ensure_verified())
        self.assertEqual(self.detector.calls, 3)

    def test_redirect_into_a_challenge_is_handled(self):
        controller = self.make(REDIRECTING, challenge(), NO_CHALLENGE, NO_CHALLENGE)
        self.assertTrue(controller.ensure_verified())
        self.assertEqual(self.events()[0]["interaction"], "automatic")

    def test_settling_is_bounded(self):
        controller = self.make(REDIRECTING)
        self.assertFalse(controller.ensure_verified())
        self.assertLessEqual(controller.clock(), verification.SETTLE_SECONDS + 1)

    def test_cloudflare_flow_is_unchanged(self):
        controller = self.make(CLOUDFLARE, NO_CHALLENGE, NO_CHALLENGE)
        self.assertTrue(controller.ensure_verified())
        events = self.events()
        self.assertEqual(len(events), 2)
        required = events[0]
        self.assertEqual(required["reason"], "cloudflare")
        self.assertEqual(required["interaction"], "manual")
        self.assertEqual(required["presentation"], "vnc")
        self.assertTrue(required["message"].startswith("Manual browser verification"))


class AnubisReportingTests(unittest.TestCase):
    def test_normal_mode_logs_automatic_progress_at_info(self):
        reporter = Reporter(json_mode=False, stream=io.StringIO())
        with self.assertLogs("goexport.verification", "INFO") as logs:
            reporter.verification_required(
                "anubis",
                "Anubis verification is in progress.",
                None,
                300,
                interaction="automatic",
            )
            reporter.verification_complete("anubis")
        self.assertEqual([r.levelname for r in logs.records], ["INFO", "INFO"])
        self.assertIn("Anubis verification complete", logs.output[1])

    def test_interruption_names_anubis(self):
        driver = Mock()
        driver.execute_script.return_value = page()
        with self.assertRaisesRegex(
            VerificationInterruptedError, "An? Anubis challenge"
        ):
            explain_interruption(driver, RuntimeError("seek failed"))

    def test_automatic_timeout_option_and_config(self):
        args = cli.build_parser().parse_args(
            ["record", "-id", "1", "--automatic-verification-timeout", "0"]
        )
        self.assertEqual(args.automatic_verification_timeout, 0)
        defaults = cli.build_parser().parse_args(["record", "-id", "1"])
        self.assertEqual(
            defaults.automatic_verification_timeout,
            config.VERIFICATION_AUTOMATIC_TIMEOUT,
        )

    def test_config_file_accepts_automatic_timeout(self):
        import tempfile
        from pathlib import Path

        from goexport.configuration.loader import ConfigurationError, load_overrides

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                "[verification]\nautomatic_timeout = 15\n", encoding="utf-8"
            )
            overrides = load_overrides(path, Path(directory), {"mp4"})
            self.assertEqual(overrides["VERIFICATION_AUTOMATIC_TIMEOUT"], 15)
            path.write_text(
                "[verification]\nautomatic_timeout = -1\n", encoding="utf-8"
            )
            with self.assertRaises(ConfigurationError):
                load_overrides(path, Path(directory), {"mp4"})


if __name__ == "__main__":
    unittest.main()
