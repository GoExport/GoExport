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
from goexport.helpers import add_runtime_arguments
from goexport.reporting import get_reporter
from goexport.services.capture import configure_backend
from goexport.services.chromium import (
    ChromiumDependencyCheckError,
    find_linux_chromium_missing_dependencies,
)
from goexport.services.display import LinuxDisplay

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
    add_runtime_arguments(parser)
    parser.set_defaults(func=entry)


def entry(args: argparse.Namespace) -> int:
    reporter = get_reporter(args)
    checks = list(run_checks(args))

    for check in checks:
        icon = {"ok": "OK", "warning": "WARNING", "error": "ERROR"}[check.status]
        color = {"ok": "green", "warning": "yellow", "error": "red"}[check.status]
        level = {
            "ok": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
        }[check.status]
        reporter.diagnostic(
            level,
            f"[{color}][{icon}][/{color}] %s: %s",
            check.name,
            check.detail,
            logger=logger,
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


def run_checks(args: argparse.Namespace | None = None) -> Iterable[Check]:
    """Yield checks required by the dependency installer and runtime."""

    args = args or argparse.Namespace()
    runtime_paths = {
        "chrome": getattr(args, "chrome_path", config.CHROME_PATH),
        "chromedriver": getattr(args, "chromedriver_path", config.CHROMEDRIVER_PATH),
        "flash": getattr(args, "flash_plugin_path", config.FLASH_PLUGIN_PATH),
        "ffmpeg": getattr(args, "ffmpeg_path", config.FFMPEG_PATH),
    }

    yield from _check_python()
    yield from _check_requirements()
    yield from _check_runtime_files(runtime_paths)
    yield from _check_chromium_dependencies(runtime_paths["chrome"])
    yield from _check_executables(runtime_paths)
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


def _check_runtime_files(runtime_paths: dict[str, Path] | None = None) -> Iterable[Check]:
    runtime_paths = runtime_paths or {
        "chrome": config.CHROME_PATH,
        "chromedriver": config.CHROMEDRIVER_PATH,
        "flash": config.FLASH_PLUGIN_PATH,
        "ffmpeg": config.FFMPEG_PATH,
    }
    required = {
        "Chromium": runtime_paths["chrome"],
        "ChromeDriver": runtime_paths["chromedriver"],
        "Pepper Flash": runtime_paths["flash"],
        "FFmpeg": runtime_paths["ffmpeg"],
    }
    for name, path in required.items():
        if path.is_file() or (name == "Pepper Flash" and path.is_dir()):
            yield Check(name, "ok", str(path))
        else:
            yield Check(name, "error", f"Missing: {path}")


def _check_executables(runtime_paths: dict[str, Path] | None = None) -> Iterable[Check]:
    runtime_paths = runtime_paths or {
        "chrome": config.CHROME_PATH,
        "chromedriver": config.CHROMEDRIVER_PATH,
        "ffmpeg": config.FFMPEG_PATH,
    }
    for name, path in (
        ("ChromeDriver", runtime_paths["chromedriver"]),
        ("FFmpeg", runtime_paths["ffmpeg"]),
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

    if runtime_paths["chrome"].is_file():
        yield Check(
            "Chromium launch",
            "warning",
            "Not started by doctor; Chromium 87 can open a GUI for version probes.",
        )


def _check_chromium_dependencies(chrome_path: Path | None = None) -> Iterable[Check]:
    """Check the bundled Chromium shared libraries on Linux with ``ldd``."""

    chrome_path = chrome_path or config.CHROME_PATH
    if config.SYSTEM != "Linux" or not chrome_path.is_file():
        return

    try:
        missing = find_linux_chromium_missing_dependencies(chrome_path)
    except ChromiumDependencyCheckError as error:
        yield Check("Chromium dependencies", "error", str(error))
        return

    if missing:
        libraries = "\n        ".join(missing)
        yield Check(
            "Chromium dependencies",
            "error",
            f"Missing required shared libraries:\n        {libraries}",
        )
    else:
        yield Check(
            "Chromium dependencies",
            "ok",
            "All required shared libraries are available.",
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
        yield from _check_linux_display()
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


def _check_linux_display() -> Iterable[Check]:
    """Validate the same display lifecycle used by recording, without xdpyinfo."""
    inherited_display = os.environ.get("DISPLAY")
    xvfb_available = bool(shutil.which("Xvfb"))
    yield Check(
        "Xvfb",
        "ok" if xvfb_available else "warning",
        "Available" if xvfb_available else "Unavailable",
    )
    yield Check(
        "Inherited DISPLAY",
        "ok" if inherited_display else "warning",
        inherited_display or "Not set",
    )

    virtual_display = None
    capture_display = inherited_display
    if xvfb_available:
        virtual_display = LinuxDisplay(size=(config.WIDTH, config.HEIGHT))
        try:
            capture_display = virtual_display.start()
        except Exception as error:
            yield Check("Virtual display", "warning", f"Could not start: {error}")
        else:
            yield Check("Virtual display", "ok", capture_display)
    else:
        yield Check("Virtual display", "warning", "Not active; Xvfb is unavailable.")

    try:
        if not capture_display:
            yield Check(
                "Capture display", "error", "No X display is available for capture."
            )
            return
        yield Check("Capture display", "ok", capture_display)
        configure_backend()
        import scap

        supported = scap.is_supported()
        yield Check(
            "Scap capture support",
            "ok" if supported else "error",
            "Available" if supported else f"Unavailable on {capture_display}",
        )
    except Exception as error:
        yield Check("Scap capture support", "error", str(error))
    finally:
        if virtual_display is not None and virtual_display.active:
            virtual_display.stop()
