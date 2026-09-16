import tempfile
import unittest
from pathlib import Path

from scripts.download_dependencies import find_windows_pepper_flash


class WindowsPepperFlashTests(unittest.TestCase):
    def test_selects_release_x64_dll_over_debug_and_32_bit_builds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            expected = root / "flash64" / "pepflashplayer64_34_0_0_376.dll"

            for path in [
                root / "debug-flash32" / "pepflashplayer32_34_0_0_376.dll",
                root / "debug-flash64" / "pepflashplayer64_34_0_0_376.dll",
                root / "flash32" / "pepflashplayer32_34_0_0_376.dll",
                expected,
            ]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()

            self.assertEqual(find_windows_pepper_flash(root), expected)

    def test_rejects_ambiguous_release_x64_dll(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            for name in [
                "pepflashplayer64_34_0_0_376.dll",
                "pepflashplayer64_34_0_0_377.dll",
            ]:
                path = root / "nested" / "flash64" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()

            with self.assertRaisesRegex(FileNotFoundError, "exactly one"):
                find_windows_pepper_flash(root)
