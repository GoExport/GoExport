import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from goexport.services import chromium


class ChromiumDependencyTests(unittest.TestCase):
    def test_parses_missing_libraries_from_ldd_output(self):
        output = """\
linux-vdso.so.1 (0x00007fff)
libasound.so.2 => not found
libpci.so.3 => not found
libc.so.6 => /lib/libc.so.6 (0x00007f)
"""
        self.assertEqual(
            chromium.parse_ldd_missing_dependencies(output),
            ("libasound.so.2", "libpci.so.3"),
        )

    def test_validation_succeeds_when_all_libraries_resolve(self):
        result = Mock(returncode=0, stdout="libc.so.6 => /lib/libc.so.6", stderr="")
        with patch.object(chromium.subprocess, "run", return_value=result):
            self.assertEqual(
                chromium.find_linux_chromium_missing_dependencies(Path("chrome")), ()
            )

    def test_validation_returns_missing_libraries(self):
        result = Mock(
            returncode=0,
            stdout="libpci.so.3 => not found\nlibasound.so.2 => not found\n",
            stderr="",
        )
        with patch.object(chromium.subprocess, "run", return_value=result):
            self.assertEqual(
                chromium.find_linux_chromium_missing_dependencies(Path("chrome")),
                ("libpci.so.3", "libasound.so.2"),
            )

    def test_validation_reports_when_ldd_cannot_run(self):
        with patch.object(chromium.subprocess, "run", side_effect=FileNotFoundError()):
            with self.assertRaisesRegex(
                chromium.ChromiumDependencyCheckError, "ldd.*unavailable"
            ):
                chromium.find_linux_chromium_missing_dependencies(Path("chrome"))

    def test_validation_reports_when_ldd_cannot_inspect_chromium(self):
        result = Mock(returncode=1, stdout="", stderr="not a dynamic executable")
        with patch.object(chromium.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(
                chromium.ChromiumDependencyCheckError, "could not inspect"
            ):
                chromium.find_linux_chromium_missing_dependencies(Path("chrome"))


if __name__ == "__main__":
    unittest.main()
