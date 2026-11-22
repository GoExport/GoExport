import unittest
from unittest.mock import Mock, patch

from selenium.common.exceptions import WebDriverException

from modules.exceptions import BotProtectionError, BrowserClosedError
from modules.navigator import Interface


class BotProtectionTests(unittest.TestCase):
    def make_interface(self, *detections):
        interface = Interface.__new__(Interface)
        interface.driver = Mock()
        interface.driver.get_log.return_value = []
        interface.driver.execute_script.side_effect = list(detections)
        return interface

    def test_unprotected_page_continues_immediately(self):
        interface = self.make_interface(None)
        self.assertTrue(interface.await_verification(timeout_seconds=1, poll_interval=0))

    def test_cloudflare_challenge_is_refused(self):
        interface = self.make_interface("cloudflare")
        with self.assertRaises(BotProtectionError) as ctx:
            interface.await_verification(timeout_seconds=1, poll_interval=0)
        self.assertEqual(ctx.exception.protection, "cloudflare")

    @patch("modules.navigator.logger")
    def test_anubis_is_awaited_until_it_passes(self, logger):
        interface = self.make_interface("anubis", "anubis", "loading", None)
        self.assertTrue(interface.await_verification(timeout_seconds=5, poll_interval=0))
        self.assertEqual(interface.driver.execute_script.call_count, 4)
        logger.info.assert_any_call("Anubis verification complete, continuing with the export")

    def test_cloudflare_after_anubis_is_refused(self):
        interface = self.make_interface("anubis", "cloudflare")
        with self.assertRaises(BotProtectionError):
            interface.await_verification(timeout_seconds=5, poll_interval=0)

    def test_anubis_timeout_raises(self):
        interface = Interface.__new__(Interface)
        interface.driver = Mock()
        interface.driver.get_log.return_value = []
        interface.driver.execute_script.return_value = "anubis"
        with self.assertRaises(BotProtectionError) as ctx:
            interface.await_verification(timeout_seconds=0, poll_interval=0)
        self.assertEqual(ctx.exception.protection, "anubis")

    def test_navigation_errors_during_redirect_are_retried(self):
        interface = self.make_interface(
            WebDriverException("javascript error: document unloaded while waiting for result"),
            None,
        )
        self.assertTrue(interface.await_verification(timeout_seconds=5, poll_interval=0))

    def test_closed_browser_during_verification_is_reported(self):
        interface = self.make_interface(WebDriverException("chrome not reachable"))
        with self.assertRaises(BrowserClosedError):
            interface.await_verification(timeout_seconds=5, poll_interval=0)


if __name__ == "__main__":
    unittest.main()
