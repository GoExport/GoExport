"""Environment diagnostics for GoExport."""

from __future__ import annotations

import argparse
import importlib.metadata
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from goexport import config
from goexport.reporting import get_reporter

logger = logging.getLogger(__name__)

REQUIREMENT_PATTERN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s]+)$")


@dataclass(frozen=True)
class Check:
    """The result of one diagnostic check."""

    name: str
    status: str
    detail: str


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "doctor",
        help="Check whether this computer is ready to run GoExport.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(func=entry)


def entry(args: argparse.Namespace) -> int:
    reporter = get_reporter(args)
    checks = list(run_checks())

    for check in checks:
        icon = {"ok": "OK", "warning": "WARNING", "error": "ERROR"}[check.status]
        level = {
            "ok": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
        }[check.status]
        reporter.diagnostic(
            level, "[%s] %s: %s", icon, check.name, check.detail, logger=logger
        )

    errors = sum(check.status == "error" for check in checks)
    warnings = sum(check.status == "warning" for check in checks)
    if errors:
        reporter.diagnostic(
            logging.ERROR,
            "GoExport is not ready: %d error(s), %d warning(s).",
            errors,
            warnings,
            logger=logger,
        )
        reporter.diagnostic(
            logging.ERROR,
            "Run 'python scripts/download_dependencies.py' to install bundled dependencies.",
            logger=logger,
        )
    elif warnings:
        reporter.diagnostic(
            logging.WARNING,
            "GoExport is ready with %d warning(s).",
            warnings,
            logger=logger,
        )
    else:
        reporter.diagnostic(logging.INFO, "GoExport is ready to use.", logger=logger)

    reporter.result(
        command="doctor",
        ok=not errors,
        checks=[
            {"name": check.name, "status": check.status, "detail": check.detail}
            for check in checks
        ],
    )
    return 1 if errors else 0


def run_checks() -> Iterable[Check]:
    """Yield checks required by the dependency installer and runtime."""

    yield from _check_python()
    yield from _check_requirements()
    yield from _check_runtime_files()
    yield from _check_executables()
    yield from _check_resources()
    yield from _check_platform()


def _check_python() -> Iterable[Check]:
    version = sys.version_info
    if version >= (3, 13):
        yield Check("Python", "ok", f"Python {platform.python_version()}")
    else:
        yield Check("Python", "error", "Python 3.13 or newer is required.")


def _check_requirements() -> Iterable[Check]:
    requirements = config.BASE_DIR / "requirements.txt"
    if not requirements.is_file():
        yield Check(
            "Python packages",
            "warning",
            "requirements.txt is unavailable in this installation.",
        )
        return

    missing: list[str] = []
    mismatched: list[str] = []
    for line in _read_requirements(requirements).splitlines():
        match = REQUIREMENT_PATTERN.match(line.strip())
        if match is None:
            continue
        package, expected = match.groups()
        try:
            installed = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            missing.append(package)
        else:
            if installed != expected:
                mismatched.append(f"{package} ({installed}, expected {expected})")

    if missing:
        yield Check("Python packages", "error", "Missing: " + ", ".join(missing))
    elif mismatched:
        yield Check(
            "Python packages",
            "warning",
            "Version differences: " + ", ".join(mismatched),
        )
    else:
        yield Check("Python packages", "ok", "All pinned requirements are installed.")


def _read_requirements(requirements: Path) -> str:
    """Read the source requirements file, including Windows UTF-16 files."""

    data = requirements.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    return data.decode("utf-8-sig")


def _check_runtime_files() -> Iterable[Check]:
    required = {
        "Chromium": config.CHROME_PATH,
        "ChromeDriver": config.CHROMEDRIVER_PATH,
        "Pepper Flash": config.FLASH_PLUGIN_PATH,
        "FFmpeg": config.FFMPEG_PATH,
    }
    for name, path in required.items():
        if path.is_file() or (name == "Pepper Flash" and path.is_dir()):
            yield Check(name, "ok", str(path))
        else:
            yield Check(name, "error", f"Missing: {path}")


def _check_executables() -> Iterable[Check]:
    for name, path in (
        ("ChromeDriver", config.CHROMEDRIVER_PATH),
        ("FFmpeg", config.FFMPEG_PATH),
    ):
        if not path.is_file():
            continue
        if os.name != "nt" and not os.access(path, os.X_OK):
            yield Check(name + " permissions", "error", f"Not executable: {path}")
            continue
        try:
            result = subprocess.run(
                [str(path), "-version" if name == "FFmpeg" else "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            yield Check(name + " launch", "error", f"Could not run {path}: {error}")
            continue
        if result.returncode:
            detail = (result.stderr or result.stdout).strip().splitlines()
            yield Check(
                name + " launch",
                "warning",
                detail[0] if detail else f"Exited with {result.returncode}.",
            )
        else:
            version = (result.stdout or result.stderr).strip().splitlines()
            yield Check(
                name + " launch",
                "ok",
                version[0] if version else "Responded to --version.",
            )

    if config.CHROME_PATH.is_file():
        yield Check(
            "Chromium launch",
            "warning",
            "Not started by doctor; Chromium 87 can open a GUI for version probes.",
        )


def _check_resources() -> Iterable[Check]:
    for name, path in (
        ("Player template", config.TEMPLATE_HTML_PATH),
        ("Default outro", config.OUTRO_PATH),
    ):
        if path.is_file():
            yield Check(name, "ok", str(path))
        else:
            yield Check(name, "error", f"Missing: {path}")


def _check_platform() -> Iterable[Check]:
    if config.SYSTEM == "Linux":
        if shutil.which("Xvfb"):
            yield Check("Linux display", "ok", "Xvfb is available for browser capture.")
        elif os.environ.get("DISPLAY"):
            yield Check(
                "Linux display",
                "warning",
                "Xvfb is unavailable; GoExport will use DISPLAY.",
            )
        else:
            yield Check(
                "Linux display", "error", "Install Xvfb or set DISPLAY for X11 capture."
            )
    elif config.SYSTEM == "Darwin":
        yield Check(
            "macOS screen capture",
            "warning",
            "Grant screen-recording permission to the terminal or GoExport app before recording.",
        )
    elif config.SYSTEM == "Windows":
        yield Check("Windows capture", "ok", "Native Windows capture will be used.")
    else:
        yield Check(
            "Platform", "error", f"Unsupported operating system: {config.SYSTEM}"
        )
