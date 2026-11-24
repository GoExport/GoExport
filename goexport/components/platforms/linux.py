"""Per-user goexport:// registration through an XDG desktop entry."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from collections.abc import Callable, Sequence
from pathlib import Path

from goexport.components.launcher import handler_arguments, parse_launcher_record
from goexport.components.models import ComponentError, Registration

DESKTOP_ID = "goexport-url-handler.desktop"
MIME_TYPE = "x-scheme-handler/goexport"
OWNER_KEY = "X-GoExport-Owner"
LAUNCHER_KEY = "X-GoExport-Launcher"
OWNER = "GoExport"
ASSOCIATION_GROUPS = ("[Default Applications]", "[Added Associations]")

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess]
Which = Callable[[str], str | None]


def _run(arguments: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(arguments), capture_output=True, text=True, timeout=30, check=False
    )


def _xdg_home(variable: str, fallback: str) -> Path:
    value = os.environ.get(variable)
    # The XDG specification ignores relative values.
    if value and Path(value).is_absolute():
        return Path(value)
    return Path.home() / fallback


def escape_string(value: str) -> str:
    """Escape a desktop-entry string value (the spec's general escape rule)."""
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .replace("\r", "\\r")
    )


def unescape_string(value: str) -> str:
    result: list[str] = []
    characters = iter(value)
    for character in characters:
        if character != "\\":
            result.append(character)
            continue
        following = next(characters, "")
        result.append(
            {"s": " ", "n": "\n", "t": "\t", "r": "\r", "\\": "\\"}.get(
                following, "\\" + following
            )
        )
    return "".join(result)


def quote_exec_argument(argument: str) -> str:
    """Quote one Exec argument per the Desktop Entry specification."""
    quoted = "".join(
        "\\" + character if character in '"`$\\' else character
        for character in argument
    )
    return '"' + quoted.replace("%", "%%") + '"'


def build_exec(launcher: tuple[str, ...]) -> str:
    """The Exec value (before string escaping); ``%u`` is the single URL."""
    arguments = handler_arguments(launcher)
    fixed = arguments[len(launcher) :]
    return " ".join([*(quote_exec_argument(part) for part in launcher), *fixed, "%u"])


def build_desktop_entry(launcher: tuple[str, ...]) -> str:
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        "Version=1.0",
        "Name=GoExport URL Handler",
        "Comment=Opens goexport:// links with GoExport",
        "Exec=" + escape_string(build_exec(launcher)),
        # A terminal shows GoExport's confirmation prompt and progress.
        "Terminal=true",
        "NoDisplay=true",
        f"MimeType={MIME_TYPE};",
        f"{OWNER_KEY}={OWNER}",
        f"{LAUNCHER_KEY}=" + escape_string(json.dumps(list(launcher))),
        "",
    ]
    return "\n".join(lines)


def parse_desktop_entry(text: str) -> dict[str, str]:
    """Read the keys of the [Desktop Entry] group (values unescaped)."""
    values: dict[str, str] = {}
    in_group = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            in_group = line == "[Desktop Entry]"
            continue
        if in_group and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = unescape_string(value.strip())
    return values


def read_default_handler(mimeapps: Path, mime_type: str = MIME_TYPE) -> str | None:
    """Return the first [Default Applications] entry for ``mime_type``."""
    try:
        text = mimeapps.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    group = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("["):
            group = line
            continue
        if group == "[Default Applications]" and "=" in line:
            key, value = line.split("=", 1)
            if key.strip() == mime_type:
                entries = [entry for entry in value.strip().split(";") if entry]
                return entries[0] if entries else None
    return None


def set_default_handler(text: str, desktop_id: str, mime_type: str = MIME_TYPE) -> str:
    """Make ``desktop_id`` the default for ``mime_type``; keep all other lines."""
    lines = text.splitlines()
    group_start = None
    for index, line in enumerate(lines):
        if line.strip() == "[Default Applications]":
            group_start = index
            break
    if group_start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["[Default Applications]", f"{mime_type}={desktop_id};"])
        return "\n".join(lines) + "\n"

    index = group_start + 1
    while index < len(lines) and not lines[index].strip().startswith("["):
        key, separator, value = lines[index].partition("=")
        if separator and key.strip() == mime_type:
            others = [
                entry
                for entry in value.strip().split(";")
                if entry and entry != desktop_id
            ]
            lines[index] = f"{mime_type}=" + "".join(
                f"{entry};" for entry in [desktop_id, *others]
            )
            return "\n".join(lines) + "\n"
        index += 1
    lines.insert(group_start + 1, f"{mime_type}={desktop_id};")
    return "\n".join(lines) + "\n"


def remove_association(text: str, desktop_id: str, mime_type: str = MIME_TYPE) -> str:
    """Remove only ``desktop_id`` from ``mime_type`` association lines."""
    result: list[str] = []
    group = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            group = stripped
            result.append(line)
            continue
        key, separator, value = line.partition("=")
        if separator and group in ASSOCIATION_GROUPS and key.strip() == mime_type:
            entries = [entry for entry in value.strip().split(";") if entry]
            remaining = [entry for entry in entries if entry != desktop_id]
            if not remaining:
                continue
            if remaining != entries:
                line = f"{mime_type}=" + "".join(f"{entry};" for entry in remaining)
        result.append(line)
    return "\n".join(result) + ("\n" if result else "")


def _write_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.pending-{uuid.uuid4().hex}")
    try:
        pending.write_text(text, encoding="utf-8")
        pending.chmod(0o644)
        pending.replace(path)
    finally:
        if pending.exists():
            pending.unlink()


class LinuxProtocolBackend:
    system = "Linux"
    scope = "Current user (XDG)"

    def __init__(
        self,
        data_home: Path | None = None,
        config_home: Path | None = None,
        runner: Runner = _run,
        which: Which = shutil.which,
    ):
        self.data_home = data_home or _xdg_home("XDG_DATA_HOME", ".local/share")
        self.config_home = config_home or _xdg_home("XDG_CONFIG_HOME", ".config")
        self.runner = runner
        self.which = which

    @property
    def applications_dir(self) -> Path:
        return self.data_home / "applications"

    @property
    def desktop_path(self) -> Path:
        return self.applications_dir / DESKTOP_ID

    @property
    def mimeapps_paths(self) -> tuple[Path, ...]:
        # The first is the current location; the second is the deprecated
        # location some older desktops still write.
        return (
            self.config_home / "mimeapps.list",
            self.applications_dir / "mimeapps.list",
        )

    def default_handler(self) -> str | None:
        if self.which("xdg-mime"):
            result = self.runner(["xdg-mime", "query", "default", MIME_TYPE])
            if result.returncode == 0:
                return (result.stdout or "").strip() or None
        for path in self.mimeapps_paths:
            handler = read_default_handler(path)
            if handler:
                return handler
        return None

    def inspect(self) -> Registration:
        notes: list[str] = []
        if not self.which("xdg-open"):
            notes.append(
                "xdg-open is not installed, so desktop applications may be unable "
                "to open goexport:// links. Install your distribution's xdg-utils "
                "package."
            )
        handler = self.default_handler()

        if not self.desktop_path.is_file():
            if handler and handler != DESKTOP_ID:
                return Registration(
                    exists=True,
                    location=handler,
                    owned=False,
                    command=f"{handler} is the default goexport:// handler",
                    notes=tuple(notes),
                )
            if handler == DESKTOP_ID:
                # GoExport's own association whose desktop file is gone.
                return Registration(
                    exists=True,
                    location=str(self.desktop_path),
                    owned=True,
                    handler_ok=False,
                    problems=(
                        f"The default goexport:// handler is {DESKTOP_ID}, but "
                        f"{self.desktop_path} does not exist.",
                    ),
                    notes=tuple(notes),
                )
            return Registration(
                exists=False, location=str(self.desktop_path), notes=tuple(notes)
            )

        try:
            entry = parse_desktop_entry(self.desktop_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as error:
            raise ComponentError(
                f"Could not read {self.desktop_path}: {error}"
            ) from error
        owned = entry.get(OWNER_KEY) == OWNER
        launcher = parse_launcher_record(entry.get(LAUNCHER_KEY)) if owned else ()
        problems: list[str] = []
        if owned:
            if not launcher:
                problems.append("GoExport's launcher record is missing or invalid.")
            elif entry.get("Exec") != build_exec(launcher):
                problems.append(f"The Exec line was changed to: {entry.get('Exec')!r}")
            if MIME_TYPE not in entry.get("MimeType", "").split(";"):
                problems.append(f"The desktop entry does not declare {MIME_TYPE}.")
            if handler != DESKTOP_ID:
                problems.append(
                    f"The default goexport:// handler is {handler}, not GoExport."
                    if handler
                    else "No default goexport:// handler is set."
                )
        return Registration(
            exists=True,
            location=str(self.desktop_path),
            owned=owned,
            launcher=launcher,
            command=entry.get("Exec"),
            handler_ok=handler == DESKTOP_ID,
            problems=tuple(problems),
            notes=tuple(notes),
        )

    def install(self, launcher: tuple[str, ...]) -> None:
        try:
            _write_atomically(self.desktop_path, build_desktop_entry(launcher))
        except OSError as error:
            raise ComponentError(
                f"Could not write {self.desktop_path}: {error}"
            ) from error

        if self.which("xdg-mime"):
            result = self.runner(["xdg-mime", "default", DESKTOP_ID, MIME_TYPE])
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "").strip()
                raise ComponentError(
                    "xdg-mime could not make GoExport the goexport:// handler"
                    + (f": {detail}" if detail else ".")
                )
        else:
            # xdg-mime is unavailable: edit the XDG mimeapps.list directly.
            mimeapps = self.mimeapps_paths[0]
            try:
                current = mimeapps.read_text(encoding="utf-8")
            except FileNotFoundError:
                current = ""
            except OSError as error:
                raise ComponentError(f"Could not read {mimeapps}: {error}") from error
            try:
                _write_atomically(mimeapps, set_default_handler(current, DESKTOP_ID))
            except OSError as error:
                raise ComponentError(f"Could not update {mimeapps}: {error}") from error
        self._refresh_database()

    def uninstall(self) -> None:
        try:
            if self.desktop_path.is_file():
                entry = parse_desktop_entry(
                    self.desktop_path.read_text(encoding="utf-8")
                )
                if entry.get(OWNER_KEY) != OWNER:
                    raise ComponentError(
                        f"{self.desktop_path} is not owned by GoExport; leaving it."
                    )
                self.desktop_path.unlink()
            for mimeapps in self.mimeapps_paths:
                if not mimeapps.is_file():
                    continue
                current = mimeapps.read_text(encoding="utf-8")
                updated = remove_association(current, DESKTOP_ID)
                if updated != current:
                    _write_atomically(mimeapps, updated)
        except OSError as error:
            raise ComponentError(
                f"Could not remove the registration: {error}"
            ) from error
        self._refresh_database()

    def _refresh_database(self) -> None:
        # Optional: only refreshes mimeinfo.cache for desktops that read it.
        if self.which("update-desktop-database"):
            self.runner(["update-desktop-database", str(self.applications_dir)])
