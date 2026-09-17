import os
import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch

from goexport.commands import doctor


class DoctorTests(unittest.TestCase):
    def test_linux_display_reports_owned_xvfb_display_to_scap(self):
        display = Mock()
        display.start.side_effect = lambda: (
            os.environ.__setitem__("DISPLAY", ":99") or ":99"
        )
        display.active = True
        scap = Mock()
        scap.is_supported.side_effect = lambda: os.environ.get("DISPLAY") == ":99"
        with (
            patch.object(doctor.config, "SYSTEM", "Linux"),
            patch.object(doctor.shutil, "which", return_value="/usr/bin/Xvfb"),
            patch.object(doctor, "LinuxDisplay", return_value=display),
            patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True),
            patch.dict(sys.modules, {"scap": scap}),
        ):
            checks = list(doctor._check_platform())
        self.assertIn(doctor.Check("Inherited DISPLAY", "ok", ":0"), checks)
        self.assertIn(doctor.Check("Virtual display", "ok", ":99"), checks)
        self.assertIn(doctor.Check("Capture display", "ok", ":99"), checks)
        self.assertIn(doctor.Check("Scap capture support", "ok", "Available"), checks)
        display.stop.assert_called_once()

    def test_missing_runtime_file_is_reported(self):
        with patch.object(doctor.config, "CHROME_PATH", Path("missing-chrome")):
            checks = list(doctor._check_runtime_files())
        self.assertIn(
            doctor.Check("Chromium", "error", "Missing: missing-chrome"), checks
        )

    def test_entry_fails_when_a_check_has_an_error(self):
        with patch.object(
            doctor,
            "run_checks",
            return_value=[doctor.Check("FFmpeg", "error", "Missing")],
        ):
            self.assertEqual(doctor.entry(Namespace()), 1)

    def test_entry_succeeds_when_only_warnings_are_present(self):
        with patch.object(
            doctor,
            "run_checks",
            return_value=[
                doctor.Check("Screen capture", "warning", "Permission needed")
            ],
        ):
            self.assertEqual(doctor.entry(Namespace()), 0)

    def test_linux_chromium_dependencies_report_missing_libraries(self):
        with (
            patch.object(doctor.config, "SYSTEM", "Linux"),
            patch.object(doctor.config, "CHROME_PATH", Path("chrome")),
            patch.object(Path, "is_file", return_value=True),
            patch.object(
                doctor,
                "find_linux_chromium_missing_dependencies",
                return_value=("libpci.so.3", "libasound.so.2"),
            ),
        ):
            checks = list(doctor._check_chromium_dependencies())
        self.assertEqual(
            checks,
            [
                doctor.Check(
                    "Chromium dependencies",
                    "error",
                    "Missing required shared libraries:\n"
                    "        libpci.so.3\n        libasound.so.2",
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
