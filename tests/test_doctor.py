import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from goexport.commands import doctor


class DoctorTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
