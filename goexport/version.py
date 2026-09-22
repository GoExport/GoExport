"""Release version loaded from the file shipped with the application."""

from __future__ import annotations

import sys
from pathlib import Path


def application_directory() -> Path:
    """Return the directory containing the runtime files."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def load_version() -> str:
    """Load the release tag from version.txt."""
    if getattr(sys, "frozen", False):
        bundle_root = getattr(sys, "_MEIPASS", None)
        if not bundle_root:
            raise RuntimeError("Unable to locate the bundled GoExport version.")
        version_path = Path(bundle_root) / "version.txt"
    else:
        version_path = application_directory() / "version.txt"
    try:
        version = version_path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise RuntimeError(
            f"Unable to read GoExport version: {version_path}"
        ) from error
    if not version:
        raise RuntimeError(f"GoExport version file is empty: {version_path}")
    return version


VERSION = load_version()
