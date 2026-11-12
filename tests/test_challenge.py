import unittest
from unittest.mock import Mock

from selenium.common.exceptions import (
    JavascriptException,
    NoSuchWindowException,
    WebDriverException,
)

from goexport.services.challenge import (
    BrowserUnavailableError,
    ChallengeDetector,
    ChallengeKind,
    classify,
    needs_header_probe,
)


def signals(**overrides):
    values = {
        "url": "https://wrapper.example/",
        "title": "Wrapper",
        "readyState": "complete",
        "strong": [],
        "weak": [],
        "challengeOptions": False,
        "text": "",
    }
    values.update(overrides)
    return values


class ClassificationTests(unittest.TestCase):
    def test_ordinary_page_is_not_a_challenge(self):
        self.assertIs(classify(signals()).kind, ChallengeKind.NONE)

    def test_challenge_title_is_detected(self):
        result = classify(signals(title="Just a moment..."))
        self.assertIs(result.kind, ChallengeKind.CHALLENGE)
        self.assertIn("title", result.reason)

    def test_unicode_ellipsis_title_is_detected(self):
        self.assertTrue(classify(signals(title="Just a moment…")).is_challenge)

    def test_challenge_options_are_detected_without_the_english_title(self):
        result = classify(signals(title="Un instant…", challengeOptions=True))
        self.assertTrue(result.is_challenge)

    def test_challenge_dom_markers_are_detected(self):
        result = classify(signals(strong=["#challenge-running"]))
        self.assertTrue(result.is_challenge)

    def test_mitigated_header_is_detected(self):
        result = classify(signals(weak=[".cf-turnstile"]), mitigated="challenge")
        self.assertTrue(result.is_challenge)
        self.assertIn("cf-mitigated", result.reason)

    def test_plain_403_page_is_not_a_challenge(self):
        page = signals(title="403 Forbidden", text="Forbidden. You don't have access.")
        self.assertIs(classify(page).kind, ChallengeKind.NONE)
        self.assertFalse(needs_header_probe(page))

    def test_cloudflare_error_page_is_not_a_challenge(self):
        page = signals(
            title="example.com | 502: Bad gateway",
            weak=["#cf-wrapper", ".cf-error-details"],
            text="Bad gateway Error code 502 Cloudflare Ray ID: 8c1",
        )
        self.assertIs(classify(page).kind, ChallengeKind.NONE)
        self.assertTrue(needs_header_probe(page))

    def test_embedded_turnstile_widget_is_not_a_challenge(self):
        page = signals(title="Sign in", weak=[".cf-turnstile"])
        self.assertIs(classify(page).kind, ChallengeKind.NONE)
        self.assertIs(classify(page, mitigated=None).kind, ChallengeKind.NONE)

    def test_other_mitigation_header_values_are_not_challenges(self):
        page = signals(weak=["#cf-wrapper"])
        self.assertIs(classify(page, mitigated="block").kind, ChallengeKind.NONE)

    def test_access_denied_page_is_a_block(self):
        page = signals(
            title="Attention Required! | Cloudflare",
            weak=["#cf-wrapper"],
            text="Sorry, you have been blocked. You are unable to access example.com",
        )
        self.assertIs(classify(page).kind, ChallengeKind.BLOCKED)

    def test_legacy_attention_required_challenge_is_detected(self):
        page = signals(
            title="Attention Required! | Cloudflare",
            text="Please complete the security check to access example.com",
        )
        self.assertTrue(classify(page).is_challenge)

    def test_unsupported_browser_challenge_is_reported(self):
        page = signals(
            title="Just a moment...",
            text="Your browser is out of date. Please update your browser.",
        )
        self.assertIs(classify(page).kind, ChallengeKind.UNSUPPORTED)

    def test_browser_internal_pages_are_ignored(self):
        page = signals(url="chrome://settings/content", title="Just a moment...")
        self.assertIs(classify(page).kind, ChallengeKind.NONE)

    def test_loading_pages_are_not_ready(self):
        self.assertFalse(classify(signals(readyState="loading")).ready)


class DetectorTests(unittest.TestCase):
    def test_detector_probes_headers_only_for_ambiguous_pages(self):
        driver = Mock()
        driver.execute_script.return_value = signals()
        ChallengeDetector().detect(driver)
        driver.execute_async_script.assert_not_called()

        driver.execute_script.return_value = signals(weak=["#cf-wrapper"])
        driver.execute_async_script.return_value = {
            "status": 403,
            "mitigated": "challenge",
        }
        self.assertTrue(ChallengeDetector().detect(driver).is_challenge)

    def test_failed_header_probe_is_not_a_challenge(self):
        driver = Mock()
        driver.execute_script.return_value = signals(weak=["#cf-wrapper"])
        driver.execute_async_script.side_effect = JavascriptException("blocked")
        self.assertIs(ChallengeDetector().detect(driver).kind, ChallengeKind.NONE)

    def test_navigating_page_is_not_ready(self):
        driver = Mock()
        driver.execute_script.side_effect = JavascriptException("document unloaded")
        result = ChallengeDetector().detect(driver)
        self.assertIs(result.kind, ChallengeKind.NONE)
        self.assertFalse(result.ready)

    def test_closed_browser_is_reported(self):
        for error in (
            NoSuchWindowException("no such window"),
            WebDriverException("chrome not reachable"),
        ):
            driver = Mock()
            driver.execute_script.side_effect = error
            with self.assertRaises(BrowserUnavailableError):
                ChallengeDetector().detect(driver)

    def test_unexpected_script_result_is_not_a_challenge(self):
        driver = Mock()
        driver.execute_script.return_value = None
        self.assertIs(ChallengeDetector().detect(driver).kind, ChallengeKind.NONE)


if __name__ == "__main__":
    unittest.main()
