import os
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch

import capturekit

from goexport.commands import doctor


class DoctorTests(unittest.TestCase):
    @staticmethod
    def capabilities(**overrides):
        supported = capturekit.Capability(capturekit.Support.SUPPORTED, "ok")
        values = dict(
            platform="linux",
            os_version="test",
            display_server="xvfb",
            monitor_capture=supported,
            window_capture=supported,
            window_capture_borderless=supported,
            window_capture_minimized=supported,
            cursor_capture=supported,
            microphone_audio=supported,
            system_audio=supported,
            process_audio=supported,
            audio_session_enumeration=supported,
            recording=supported,
        )
        values.update(overrides)
        return capturekit.Capabilities(**values)

    def test_linux_display_reports_owned_xvfb_display_to_capturekit(self):
        display = Mock()
        display.start.return_value = ":99"
        display.active = True
        with (
            patch.object(doctor.config, "SYSTEM", "Linux"),
            patch.object(doctor.shutil, "which", return_value="/usr/bin/Xvfb"),
            patch.object(doctor, "LinuxDisplay", return_value=display),
            patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True),
            patch.object(
                capturekit, "get_capabilities", return_value=self.capabilities()
            ) as get_capabilities,
        ):
            checks = list(doctor._check_platform())
        get_capabilities.assert_called_once_with(":99")
        self.assertIn(doctor.Check("Inherited DISPLAY", "ok", ":0"), checks)
        self.assertIn(doctor.Check("Virtual display", "ok", ":99"), checks)
        self.assertIn(doctor.Check("Capture display", "ok", ":99"), checks)
        self.assertIn(doctor.Check("CaptureKit window capture", "ok", "ok"), checks)
        self.assertIn(doctor.Check("CaptureKit recording", "ok", "ok"), checks)
        display.stop.assert_called_once()

    def test_capturekit_gaps_are_reported_with_guidance(self):
        unavailable = capturekit.Capability(
            capturekit.Support.UNAVAILABLE, "no Composite"
        )
        caps = self.capabilities(window_capture=unavailable, process_audio=unavailable)
        with patch.object(capturekit, "get_capabilities", return_value=caps):
            owned = {c.name: c for c in doctor._check_capturekit(":99", True)}
            foreign = {c.name: c for c in doctor._check_capturekit(":0", False)}
        self.assertEqual(owned["CaptureKit window capture"].status, "warning")
        self.assertEqual(foreign["CaptureKit window capture"].status, "error")
        self.assertIn(
            "--capturekit-audio", owned["CaptureKit application audio"].detail
        )

    def test_macos_points_to_obs_backend(self):
        with patch.object(doctor.config, "SYSTEM", "Darwin"):
            (check,) = doctor._check_platform()
        self.assertEqual(check.status, "warning")
        self.assertIn("--capture-backend obs", check.detail)

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
