import unittest
from unittest.mock import Mock, patch

from selenium.common.exceptions import NoSuchWindowException, WebDriverException

from modules.exceptions import BrowserClosedError
from modules.navigator import Interface


class BrowserDiagnosticsTests(unittest.TestCase):
    def make_interface(self):
        interface = Interface.__new__(Interface)
        interface.driver = Mock()
        return interface

    def test_chrome_not_reachable_is_reported_as_browser_closed(self):
        interface = self.make_interface()
        error = WebDriverException("chrome not reachable")

        with self.assertRaisesRegex(
            BrowserClosedError,
            "Chromium was closed before GoExport finished",
        ):
            interface._translate_webdriver_error(error)

    def test_no_such_window_is_reported_as_browser_closed(self):
        interface = self.make_interface()

        with self.assertRaises(BrowserClosedError):
            interface._translate_webdriver_error(NoSuchWindowException("window closed"))

    @patch("modules.navigator.logger")
    def test_browser_console_entries_are_forwarded(self, logger):
        interface = self.make_interface()
        interface.driver.get_log.return_value = [
            {"level": "INFO", "message": 'console-api 1:1 "hello"'},
            {"level": "WARNING", "message": "warning message"},
            {"level": "SEVERE", "message": "Uncaught TypeError: boom"},
        ]

        interface.log_browser_console()

        logger.info.assert_called_once_with(
            '[Chromium console][INFO] console-api 1:1 "hello"'
        )
        logger.warning.assert_called_once_with(
            "[Chromium console][WARNING] warning message"
        )
        logger.error.assert_called_once_with(
            "[Chromium console][SEVERE] Uncaught TypeError: boom"
        )

    def test_console_read_detects_closed_browser(self):
        interface = self.make_interface()
        interface.driver.get_log.side_effect = WebDriverException("chrome not reachable")

        with self.assertRaises(BrowserClosedError):
            interface.log_browser_console()


if __name__ == "__main__":
    unittest.main()
