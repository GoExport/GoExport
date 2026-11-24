"""goexport:// registration through a generated Launch Services applet.

macOS delivers URLs to applications as Apple Events rather than command-line
arguments, and only application bundles that declare the scheme in their
Info.plist can receive them. GoExport therefore generates a small AppleScript
applet beside the portable application. Its ``open location`` handler opens
Terminal and runs ``GoExport handle-url -- <URL>`` so the confirmation prompt
and progress are visible.
"""

from __future__ import annotations

import ctypes
import plistlib
import shlex
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from goexport import config
from goexport.components.launcher import handler_arguments, parse_launcher_record
from goexport.components.models import ComponentError, Registration

SCHEME = "goexport"
BUNDLE_NAME = "GoExport URL Handler.app"
BUNDLE_ID = "io.github.goexport.url-handler"
OWNER_KEY = "GoExportOwner"
LAUNCHER_KEY = "GoExportLauncher"
OWNER = "GoExport"
LSREGISTER = (
    "/System/Library/Frameworks/CoreServices.framework/Frameworks/"
    "LaunchServices.framework/Support/lsregister"
)

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess]


def _run(arguments: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(arguments), capture_output=True, text=True, timeout=60, check=False
    )


class LaunchServices(Protocol):
    def default_handler(self, scheme: str) -> str | None:
        """Return the bundle identifier that opens ``scheme`` URLs."""

    def set_default_handler(self, scheme: str, bundle_id: str) -> None:
        """Make ``bundle_id`` the handler for ``scheme`` URLs."""


class CoreServicesLaunchServices:
    """Launch Services through CoreServices with ctypes (no extra packages)."""

    _UTF8 = 0x08000100

    def __init__(self) -> None:
        cf = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
        )
        cs = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/CoreServices.framework/CoreServices"
        )
        cf.CFStringCreateWithCString.restype = ctypes.c_void_p
        cf.CFStringCreateWithCString.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_uint32,
        ]
        cf.CFStringGetCString.restype = ctypes.c_bool
        cf.CFStringGetCString.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_long,
            ctypes.c_uint32,
        ]
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        cs.LSCopyDefaultHandlerForURLScheme.restype = ctypes.c_void_p
        cs.LSCopyDefaultHandlerForURLScheme.argtypes = [ctypes.c_void_p]
        cs.LSSetDefaultHandlerForURLScheme.restype = ctypes.c_int32
        cs.LSSetDefaultHandlerForURLScheme.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        self._cf = cf
        self._cs = cs

    def _string(self, value: str) -> int:
        return self._cf.CFStringCreateWithCString(None, value.encode(), self._UTF8)

    def default_handler(self, scheme: str) -> str | None:
        scheme_ref = self._string(scheme)
        try:
            handler = self._cs.LSCopyDefaultHandlerForURLScheme(scheme_ref)
        finally:
            self._cf.CFRelease(scheme_ref)
        if not handler:
            return None
        try:
            buffer = ctypes.create_string_buffer(1024)
            if not self._cf.CFStringGetCString(handler, buffer, 1024, self._UTF8):
                return None
            return buffer.value.decode()
        finally:
            self._cf.CFRelease(handler)

    def set_default_handler(self, scheme: str, bundle_id: str) -> None:
        scheme_ref = self._string(scheme)
        bundle_ref = self._string(bundle_id)
        try:
            status = self._cs.LSSetDefaultHandlerForURLScheme(scheme_ref, bundle_ref)
        finally:
            self._cf.CFRelease(scheme_ref)
            self._cf.CFRelease(bundle_ref)
        if status != 0:
            raise ComponentError(
                f"Launch Services refused to set the goexport:// handler "
                f"(OSStatus {status})."
            )


def build_applescript(launcher: tuple[str, ...]) -> str:
    """AppleScript source for the applet.

    The command is a local variable (applets write ``property`` values back
    into their bundle) and the URL is shell-quoted with ``quoted form of``.
    """
    command = " ".join(shlex.quote(part) for part in handler_arguments(launcher))
    literal = '"' + command.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return (
        "on open location requestURL\n"
        f"\tset goexportCommand to {literal}\n"
        '\ttell application "Terminal"\n'
        "\t\tactivate\n"
        '\t\tdo script goexportCommand & " " & quoted form of requestURL\n'
        "\tend tell\n"
        "end open location\n"
        "\n"
        "on run\n"
        '\tdisplay dialog "GoExport URL Handler opens goexport:// links with '
        "GoExport. Manage it with GoExport's install protocol and uninstall "
        "protocol commands or the GUI's Components page.\" "
        'buttons {"OK"} default button "OK" with title "GoExport"\n'
        "end run\n"
    )


class MacOSProtocolBackend:
    system = "macOS"
    scope = "Current user (Launch Services)"

    def __init__(
        self,
        bundle_path: Path | None = None,
        runner: Runner = _run,
        launch_services: LaunchServices | None = None,
    ):
        self.bundle_path = bundle_path or config.BASE_DIR / BUNDLE_NAME
        self.runner = runner
        self._launch_services = launch_services

    @property
    def launch_services(self) -> LaunchServices:
        if self._launch_services is None:
            self._launch_services = CoreServicesLaunchServices()
        return self._launch_services

    @property
    def info_plist(self) -> Path:
        return self.bundle_path / "Contents" / "Info.plist"

    def _read_plist(self) -> dict:
        try:
            with self.info_plist.open("rb") as source:
                data = plistlib.load(source)
        except FileNotFoundError:
            return {}
        except (OSError, plistlib.InvalidFileException) as error:
            raise ComponentError(
                f"Could not read {self.info_plist}: {error}"
            ) from error
        return data if isinstance(data, dict) else {}

    def inspect(self) -> Registration:
        handler = self.launch_services.default_handler(SCHEME)
        location = str(self.bundle_path)
        if not self.bundle_path.exists():
            if handler and handler != BUNDLE_ID:
                return Registration(
                    exists=True,
                    location=handler,
                    owned=False,
                    command=f"{handler} is the default goexport:// handler",
                )
            notes = (
                (
                    "goexport:// is registered to a GoExport URL Handler "
                    "generated by another GoExport copy.",
                )
                if handler == BUNDLE_ID
                else ()
            )
            return Registration(exists=False, location=location, notes=notes)

        plist = self._read_plist()
        owned = plist.get(OWNER_KEY) == OWNER
        launcher = parse_launcher_record(plist.get(LAUNCHER_KEY)) if owned else ()
        problems: list[str] = []
        if owned:
            if not launcher:
                problems.append("GoExport's launcher record is missing or invalid.")
            schemes = [
                scheme
                for url_type in plist.get("CFBundleURLTypes", [])
                if isinstance(url_type, dict)
                for scheme in url_type.get("CFBundleURLSchemes", [])
            ]
            if SCHEME not in schemes:
                problems.append("The applet does not declare the goexport scheme.")
            if plist.get("CFBundleIdentifier") != BUNDLE_ID:
                problems.append("The applet's bundle identifier was changed.")
            if handler != BUNDLE_ID:
                problems.append(
                    f"Launch Services opens goexport:// with {handler}, not GoExport."
                    if handler
                    else "Launch Services has no goexport:// handler."
                )
        return Registration(
            exists=True,
            location=location,
            owned=owned,
            launcher=launcher,
            command=" ".join(handler_arguments(launcher)) if launcher else None,
            handler_ok=handler == BUNDLE_ID,
            problems=tuple(problems),
        )

    def install(self, launcher: tuple[str, ...]) -> None:
        if "AppTranslocation" in self.bundle_path.parts:
            raise ComponentError(
                "macOS is running GoExport from a temporary App Translocation "
                "location. Move the GoExport folder (for example with Finder) and "
                "start it again before installing the protocol."
            )
        if self.bundle_path.exists():
            self.uninstall()
        with tempfile.TemporaryDirectory(prefix="goexport-applet-") as temp:
            source = Path(temp) / "handler.applescript"
            source.write_text(build_applescript(launcher), encoding="utf-8")
            self._check(
                ["osacompile", "-o", str(self.bundle_path), str(source)],
                "osacompile could not create the URL handler applet",
            )
        try:
            plist = self._read_plist()
            plist.update(
                {
                    "CFBundleIdentifier": BUNDLE_ID,
                    "CFBundleName": "GoExport URL Handler",
                    "CFBundleURLTypes": [
                        {
                            "CFBundleURLName": "GoExport URL",
                            "CFBundleURLSchemes": [SCHEME],
                        }
                    ],
                    "LSUIElement": True,
                    OWNER_KEY: OWNER,
                    LAUNCHER_KEY: list(launcher),
                }
            )
            with self.info_plist.open("wb") as output:
                plistlib.dump(plist, output)
        except OSError as error:
            raise ComponentError(
                f"Could not write {self.info_plist}: {error}"
            ) from error
        # Editing Info.plist invalidates the applet's signature.
        self._check(
            ["codesign", "--force", "--sign", "-", str(self.bundle_path)],
            "codesign could not sign the URL handler applet",
        )
        self._check(
            [LSREGISTER, "-f", str(self.bundle_path)],
            "Launch Services could not register the URL handler applet",
        )
        self.launch_services.set_default_handler(SCHEME, BUNDLE_ID)

    def uninstall(self) -> None:
        if not self.bundle_path.exists():
            return
        if self._read_plist().get(OWNER_KEY) != OWNER:
            raise ComponentError(
                f"{self.bundle_path} is not owned by GoExport; leaving it."
            )
        # Unregistering is best effort: the bundle is removed either way.
        self.runner([LSREGISTER, "-u", str(self.bundle_path)])
        try:
            shutil.rmtree(self.bundle_path)
        except OSError as error:
            raise ComponentError(
                f"Could not remove {self.bundle_path}: {error}"
            ) from error

    def _check(self, arguments: list[str], message: str) -> None:
        try:
            result = self.runner(arguments)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ComponentError(f"{message}: {error}") from error
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise ComponentError(f"{message}" + (f": {detail}" if detail else "."))
