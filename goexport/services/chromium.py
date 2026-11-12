"""Linux runtime validation for the bundled Chromium executable."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

MISSING_LIBRARY_PATTERN = re.compile(
    r"^\s*(?P<library>\S+)\s+=>\s+not found(?:\s|$)", re.MULTILINE
)


class ChromiumDependencyCheckError(RuntimeError):
    """Raised when ``ldd`` cannot inspect the bundled Chromium executable."""


def parse_ldd_missing_dependencies(output: str) -> tuple[str, ...]:
    """Return the library names that ``ldd`` reports as unresolved."""

    return tuple(
        match.group("library") for match in MISSING_LIBRARY_PATTERN.finditer(output)
    )


def find_linux_chromium_missing_dependencies(chrome_path: Path) -> tuple[str, ...]:
    """Inspect Chromium with ``ldd`` and return any unavailable shared libraries."""

    return find_linux_missing_libraries(chrome_path)


def find_linux_missing_libraries(
    executable: Path, library_dirs: Iterable[Path] = ()
) -> tuple[str, ...]:
    """Return the shared libraries ``ldd`` cannot resolve for ``executable``.

    ``library_dirs`` are searched first, as the executable's launcher does
    through LD_LIBRARY_PATH for bundled private libraries.
    """

    env = None
    directories = [str(directory) for directory in library_dirs]
    if directories:
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [*directories, *filter(None, [env.get("LD_LIBRARY_PATH")])]
        )
    try:
        result = subprocess.run(
            ["ldd", str(executable)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env=env,
        )
    except FileNotFoundError as error:
        raise ChromiumDependencyCheckError(
            "The 'ldd' command is unavailable."
        ) from error
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ChromiumDependencyCheckError(f"Could not run ldd: {error}") from error

    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    missing = parse_ldd_missing_dependencies(output)
    if missing:
        return missing

    if result.returncode:
        detail = output.strip().splitlines()
        message = detail[0] if detail else f"ldd exited with {result.returncode}."
        raise ChromiumDependencyCheckError(
            f"ldd could not inspect {executable}: {message}"
        )

    return ()
