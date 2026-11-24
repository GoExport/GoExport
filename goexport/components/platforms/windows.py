"""Per-user goexport:// registration in HKEY_CURRENT_USER\\Software\\Classes."""

from __future__ import annotations

import json
import sys
from typing import Protocol

from goexport.components.launcher import handler_arguments, parse_launcher_record
from goexport.components.models import ComponentError, Registration

SCHEME_KEY = r"Software\Classes\goexport"
COMMAND_KEY = SCHEME_KEY + r"\shell\open\command"
ICON_KEY = SCHEME_KEY + r"\DefaultIcon"
OWNER_VALUE = "GoExport.Owner"
LAUNCHER_VALUE = "GoExport.Launcher"
OWNER = "GoExport"
DESCRIPTION = "URL:GoExport Protocol"


class Registry(Protocol):
    def read_values(self, hive: str, path: str) -> dict[str, str] | None:
        """Return a key's string values, or None when the key is absent."""

    def set_value(self, path: str, name: str, value: str) -> None:
        """Create the HKCU key if needed and set a REG_SZ value."""

    def delete_tree(self, path: str) -> None:
        """Delete an HKCU key and all of its subkeys."""


class WindowsRegistry:
    """Registry access through ``winreg``; HKCU writes only."""

    def read_values(self, hive: str, path: str) -> dict[str, str] | None:
        if sys.platform != "win32":
            raise OSError("The Windows registry is only available on Windows.")
        import winreg

        root = {
            "HKCU": winreg.HKEY_CURRENT_USER,
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
        }[hive]
        try:
            key = winreg.OpenKey(root, path)
        except FileNotFoundError:
            return None
        values: dict[str, str] = {}
        with key:
            index = 0
            while True:
                try:
                    name, value, _kind = winreg.EnumValue(key, index)
                except OSError:
                    break
                values[name] = "" if value is None else str(value)
                index += 1
        return values

    def set_value(self, path: str, name: str, value: str) -> None:
        if sys.platform != "win32":
            raise OSError("The Windows registry is only available on Windows.")
        import winreg

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)

    def delete_tree(self, path: str) -> None:
        if sys.platform != "win32":
            raise OSError("The Windows registry is only available on Windows.")
        import winreg

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_ALL_ACCESS
            )
        except FileNotFoundError:
            return
        with key:
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                except OSError:
                    break
                self.delete_tree(path + "\\" + child)
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)


def build_command(launcher: tuple[str, ...]) -> str:
    """Build the shell\\open\\command value.

    Every launcher path is quoted, and the URL is passed as one quoted
    argument after ``--``. Windows paths cannot contain ``"``; ``%`` is
    rejected because the shell expands ``%1``-style sequences in this value.
    """
    for part in launcher:
        if '"' in part or "%" in part:
            raise ComponentError(
                f"GoExport cannot register a launcher path containing '\"' or "
                f"'%': {part}. Move GoExport to a folder without these characters."
            )
    arguments = handler_arguments(launcher)
    fixed = arguments[len(launcher) :]
    quoted = " ".join(f'"{part}"' for part in launcher)
    return f'{quoted} {" ".join(fixed)} "%1"'


class WindowsProtocolBackend:
    system = "Windows"
    scope = "Current user (HKCU)"

    def __init__(self, registry: Registry | None = None):
        self.registry = registry or WindowsRegistry()

    @property
    def location(self) -> str:
        return "HKEY_CURRENT_USER\\" + SCHEME_KEY

    def inspect(self) -> Registration:
        values = self.registry.read_values("HKCU", SCHEME_KEY)
        notes: list[str] = []
        machine = self.registry.read_values("HKLM", SCHEME_KEY)
        if machine is not None:
            machine_command = (
                self.registry.read_values("HKLM", COMMAND_KEY) or {}
            ).get("", "")
            notes.append(
                "A machine-wide goexport:// registration also exists in "
                "HKEY_LOCAL_MACHINE (for example from a GoExport V1 installer"
                + (f": {machine_command}" if machine_command else "")
                + "). A per-user registration takes precedence for this user; "
                "GoExport never changes the machine-wide one."
            )
        if values is None:
            return Registration(
                exists=False, location=self.location, notes=tuple(notes)
            )

        command = (self.registry.read_values("HKCU", COMMAND_KEY) or {}).get("")
        owned = values.get(OWNER_VALUE) == OWNER
        launcher = parse_launcher_record(values.get(LAUNCHER_VALUE)) if owned else ()
        problems: list[str] = []
        if owned:
            if not launcher:
                problems.append("GoExport's launcher record is missing or invalid.")
            if "URL Protocol" not in values:
                problems.append("The key does not declare 'URL Protocol'.")
            if launcher:
                try:
                    expected = build_command(launcher)
                except ComponentError as error:
                    problems.append(str(error))
                else:
                    if command != expected:
                        problems.append(
                            f"The registered command was changed to: {command!r}"
                        )
        return Registration(
            exists=True,
            location=self.location,
            owned=owned,
            launcher=launcher,
            command=command,
            problems=tuple(problems),
            notes=tuple(notes),
        )

    def install(self, launcher: tuple[str, ...]) -> None:
        command = build_command(launcher)
        try:
            # The caller only reaches this point for an absent or
            # GoExport-owned key. Clear it so no stale verbs remain, then
            # write the ownership marker first: an interrupted write stays
            # recognisable as GoExport's and can be repaired.
            self.registry.delete_tree(SCHEME_KEY)
            self.registry.set_value(SCHEME_KEY, OWNER_VALUE, OWNER)
            self.registry.set_value(SCHEME_KEY, LAUNCHER_VALUE, json.dumps(launcher))
            self.registry.set_value(SCHEME_KEY, "", DESCRIPTION)
            self.registry.set_value(SCHEME_KEY, "URL Protocol", "")
            self.registry.set_value(ICON_KEY, "", f'"{launcher[0]}",0')
            self.registry.set_value(COMMAND_KEY, "", command)
        except OSError as error:
            raise ComponentError(f"Could not write {self.location}: {error}") from error

    def uninstall(self) -> None:
        try:
            self.registry.delete_tree(SCHEME_KEY)
        except OSError as error:
            raise ComponentError(
                f"Could not remove {self.location}: {error}"
            ) from error
