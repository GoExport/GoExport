import os
import tempfile
import unittest
from pathlib import Path

from scripts import download_dependencies


class FlashDownloadTests(unittest.TestCase):
    def test_uses_goexport_flash_release_assets(self):
        for system, asset in [
            ("Windows", "pepflashplayer.zip"),
            ("Linux", "libpepflashplayer.zip"),
            ("Darwin", "PepperFlashPlayer.plugin.zip"),
        ]:
            self.assertEqual(
                download_dependencies.DOWNLOADS[system]["flash"],
                "https://github.com/GoExport/goexport-flash-player/releases/latest/download/"
                + asset,
            )


class ExecutableTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "Windows does not expose Unix execute bits")
    def test_make_executable_adds_unix_execute_bits(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "chromedriver"
            path.touch(mode=0o644)

            download_dependencies.make_executable(path)

            self.assertEqual(path.stat().st_mode & 0o111, 0o111)
