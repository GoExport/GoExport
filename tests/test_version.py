import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goexport import version


class VersionTests(unittest.TestCase):
    def test_version_is_loaded_from_runtime_file(self):
        version_path = version.application_directory() / "version.txt"
        self.assertEqual(
            version.VERSION, version_path.read_text(encoding="utf-8").strip()
        )

    def test_cli_reports_the_version_tag(self):
        project_root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            [sys.executable, "main.py", "--version"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stdout.strip(), version.VERSION)

    def test_frozen_application_loads_the_bundled_version_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            executable = root / "release" / "GoExport.exe"
            bundle_root = root / "bundle"
            bundle_root.mkdir()
            (bundle_root / "version.txt").write_text("v2.0.0b1\n", encoding="utf-8")
            (executable.parent / "version.txt").parent.mkdir()
            (executable.parent / "version.txt").write_text(
                "external\n", encoding="utf-8"
            )
            with (
                patch.object(version.sys, "frozen", True, create=True),
                patch.object(version.sys, "executable", str(executable)),
                patch.object(version.sys, "_MEIPASS", str(bundle_root), create=True),
            ):
                self.assertEqual(version.load_version(), "v2.0.0b1")
