"""Resolve the command that starts this copy of GoExport."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from goexport import config
from goexport.components.models import ComponentError

# The CLI subcommand that receives goexport:// URLs from the operating system.
HANDLER_COMMAND = "handle-url"


def current_launcher() -> tuple[str, ...]:
    """Return the absolute program (and script) that starts this GoExport.

    Packaged builds start their own executable. Source checkouts and virtual
    environments start ``main.py`` with the interpreter running now; the venv
    interpreter path is kept unresolved so it still selects the venv.
    """
    if getattr(sys, "frozen", False):
        launcher: tuple[str, ...] = (str(Path(sys.executable).resolve()),)
    else:
        launcher = (
            str(Path(sys.executable).absolute()),
            str((config.BASE_DIR / "main.py").resolve()),
        )
    validate_launcher(launcher)
    return launcher


def validate_launcher(launcher: tuple[str, ...]) -> None:
    """Refuse launcher paths that cannot be registered safely."""
    if not launcher:
        raise ComponentError("GoExport could not determine its own executable.")
    for part in launcher:
        path = Path(part)
        if not path.is_absolute():
            raise ComponentError(f"GoExport's launcher path is not absolute: {part}")
        if any(character in part for character in "\0\r\n"):
            raise ComponentError(
                f"GoExport's launcher path contains a control character: {part!r}"
            )
        if not path.is_file():
            raise ComponentError(f"GoExport's launcher does not exist: {part}")


def parse_launcher_record(value: object) -> tuple[str, ...]:
    """Read a launcher stored in a registration (a JSON list or a list)."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return ()
    if not isinstance(value, list) or not value:
        return ()
    if not all(isinstance(part, str) and part for part in value):
        return ()
    return tuple(value)


def handler_arguments(launcher: tuple[str, ...]) -> list[str]:
    """The fixed arguments placed before the URL in every registration.

    ``--`` ends option parsing so a URL can never be read as an option.
    """
    return [*launcher, HANDLER_COMMAND, "--"]
