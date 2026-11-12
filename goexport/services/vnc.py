"""Show GoExport's private Xvfb display on the user's desktop through VNC.

Linux only. Chromium keeps running on the Xvfb display that PyVirtualDisplay
started; nothing about that display or the browser changes. For the duration
of a verification, a bundled ``x11vnc`` serves that display on localhost and a
bundled TigerVNC viewer opens on the desktop GoExport was started from.

Security: the server listens on 127.0.0.1 only, refuses a second client and
requires a random single-use password. The password exists only in a private
temporary directory: x11vnc deletes its copy after reading it, and the
directory is removed when verification ends. It is never logged or reported.
"""

from __future__ import annotations

import logging
import os
import secrets
import shutil
import signal
import socket
import string
import subprocess
import sys
import tempfile
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from goexport import config
from goexport.services.verification import PresentationError

logger = logging.getLogger(__name__)

SERVER_READY_TIMEOUT_SECONDS = 10.0
PROCESS_STOP_TIMEOUT_SECONDS = 3.0
# x11vnc exits when no viewer has connected within this many seconds.
SERVER_CONNECT_TIMEOUT_SECONDS = 60
# Classic VNC authentication only uses the first eight password characters.
PASSWORD_LENGTH = 8
PASSWORD_ALPHABET = string.ascii_letters + string.digits
DESKTOP_NAME = "GoExport browser verification"

NO_DESKTOP_MESSAGE = (
    "Cloudflare verification must be completed in GoExport's browser, which "
    "runs on a private virtual display, but no desktop display was available "
    "when GoExport started (DISPLAY was not set), so the verification viewer "
    "cannot be shown. Run GoExport from a graphical desktop session."
)
WAYLAND_ONLY_MESSAGE = (
    " This Wayland session does not provide an X11 display; enable XWayland."
)


@dataclass(frozen=True)
class VNCTools:
    server: Path
    viewer: Path
    library_dir: Path | None = None


def find_tools(vnc_dir: Path | None = None) -> VNCTools:
    """Locate the bundled VNC tools, falling back to PATH for source checkouts."""
    vnc_dir = vnc_dir or config.VNC_DIR
    server = vnc_dir / "x11vnc"
    viewer = vnc_dir / "vncviewer"
    if server.is_file() and viewer.is_file():
        library_dir = vnc_dir / "lib"
        return VNCTools(server, viewer, library_dir if library_dir.is_dir() else None)

    system_server = shutil.which("x11vnc")
    system_viewer = shutil.which("xtigervncviewer") or shutil.which("vncviewer")
    if system_server and system_viewer:
        return VNCTools(Path(system_server), Path(system_viewer))
    raise PresentationError(
        f"GoExport's bundled VNC tools are missing from {vnc_dir}, so the "
        "verification browser cannot be shown. Reinstall GoExport from the "
        "release archive (source checkouts may install x11vnc and TigerVNC's "
        "vncviewer instead)."
    )


def tool_environment(
    tools: VNCTools,
    display: str,
    xauthority: str | None,
    base: dict[str, str] | None = None,
    x11_only: bool = False,
) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    if x11_only:
        # x11vnc refuses to run when it believes it is in a Wayland session,
        # even though it serves GoExport's Xvfb display, not the desktop.
        env.pop("WAYLAND_DISPLAY", None)
        env["XDG_SESSION_TYPE"] = "x11"
    if getattr(sys, "frozen", False) or "LD_LIBRARY_PATH_ORIG" in env:
        # PyInstaller prepends its private libraries to LD_LIBRARY_PATH; the
        # VNC tools must not load them.
        original = env.pop("LD_LIBRARY_PATH_ORIG", None)
        if original:
            env["LD_LIBRARY_PATH"] = original
        else:
            env.pop("LD_LIBRARY_PATH", None)
    if tools.library_dir is not None:
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part
            for part in (str(tools.library_dir), env.get("LD_LIBRARY_PATH"))
            if part
        )
    env["DISPLAY"] = display
    if xauthority:
        env["XAUTHORITY"] = xauthority
    else:
        env.pop("XAUTHORITY", None)
    return env


def generate_password() -> str:
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(PASSWORD_LENGTH))


def free_localhost_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def write_private_file(path: Path, data: bytes) -> Path:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as private:
        private.write(data)
    return path


def _die_with_parent() -> None:  # pragma: no cover - runs in the child
    """Ask Linux to stop the VNC tools if GoExport itself is killed."""
    try:
        import ctypes

        ctypes.CDLL(None).prctl(1, signal.SIGTERM)  # PR_SET_PDEATHSIG
    except Exception:
        pass


class VNCPresenter:
    presentation = "vnc"
    instructions = (
        "Complete the check in the GoExport verification viewer window; the "
        "export resumes automatically."
    )

    def __init__(
        self,
        display,
        tools: VNCTools | None = None,
        popen=subprocess.Popen,
        ready_timeout: float = SERVER_READY_TIMEOUT_SECONDS,
    ):
        self.display = display
        self.tools = tools
        self.popen = popen
        self.ready_timeout = ready_timeout
        self.server: subprocess.Popen | None = None
        self.viewer: subprocess.Popen | None = None
        self.port: int | None = None
        self.workdir: Path | None = None
        self._ready = threading.Event()
        self._server_output: deque[str] = deque(maxlen=20)
        self._readers: list[threading.Thread] = []

    def server_command(self, password_file: Path) -> list[str]:
        assert self.tools is not None and self.port is not None
        return [
            str(self.tools.server),
            "-display",
            str(self.display.capture_display),
            "-localhost",
            "-noipv6",
            "-rfbport",
            str(self.port),
            # libvncserver otherwise also listens on [::1]:5900.
            "-rfbportv6",
            "-1",
            # rm: makes x11vnc delete the plain-text password after reading it.
            "-passwdfile",
            f"rm:{password_file}",
            "-nevershared",
            "-dontdisconnect",
            "-timeout",
            str(SERVER_CONNECT_TIMEOUT_SECONDS),
            "-norc",
            "-nolookup",
            "-nosel",
            "-xkb",
            "-desktop",
            DESKTOP_NAME,
        ]

    def viewer_command(self, password_file: Path) -> list[str]:
        assert self.tools is not None and self.port is not None
        return [
            str(self.tools.viewer),
            f"-PasswordFile={password_file}",
            "-SecurityTypes=VncAuth",
            # Never resize GoExport's Xvfb display or the browser on it.
            "-RemoteResize=0",
            "-FullScreen=0",
            "-Shared=0",
            "-ReconnectOnError=0",
            "-AcceptClipboard=0",
            "-SendClipboard=0",
            "-SendPrimary=0",
            "-DotWhenNoCursor=1",
            f"127.0.0.1::{self.port}",
        ]

    def show(self) -> None:
        desktop = self.display.inherited_display
        if not desktop:
            message = NO_DESKTOP_MESSAGE
            if os.environ.get("WAYLAND_DISPLAY"):
                message += WAYLAND_ONLY_MESSAGE
            raise PresentationError(message)
        self.tools = self.tools or find_tools()

        try:
            self.workdir = Path(tempfile.mkdtemp(prefix="goexport-vnc-"))
            password = generate_password()
            server_password = write_private_file(
                self.workdir / "x11vnc.pass", (password + "\n").encode("ascii")
            )
            viewer_password = write_private_file(
                self.workdir / "viewer.passwd", obfuscate_password(password)
            )
            self.port = free_localhost_port()
            self.server = self._start(
                self.server_command(server_password),
                tool_environment(
                    self.tools,
                    str(self.display.capture_display),
                    None,
                    x11_only=True,
                ),
                "x11vnc",
                self._watch_server_line,
            )
            self._wait_for_server()
            self.viewer = self._start(
                self.viewer_command(viewer_password),
                tool_environment(
                    self.tools, desktop, self.display.inherited_xauthority
                ),
                "vncviewer",
            )
        except OSError as error:
            self.restore()
            raise PresentationError(
                f"Could not start the verification viewer: {error}"
            ) from error
        except BaseException:
            self.restore()
            raise
        logger.info(
            "Showing GoExport's virtual display %s on desktop %s for verification.",
            self.display.capture_display,
            desktop,
        )

    def _start(self, command, env, name, on_line=None) -> subprocess.Popen:
        logger.debug("Starting %s: %s", name, command[0])
        process = self.popen(
            command,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            start_new_session=True,
            preexec_fn=_die_with_parent,
        )
        stream = getattr(process, "stdout", None)
        if stream is not None:
            reader = threading.Thread(
                target=self._read_output,
                args=(stream, name, on_line),
                name=f"goexport-{name}-output",
                daemon=True,
            )
            reader.start()
            self._readers.append(reader)
        return process

    @staticmethod
    def _read_output(stream, name, on_line) -> None:
        try:
            for line in stream:
                line = line.rstrip()
                logger.debug("%s: %s", name, line)
                if on_line is not None:
                    on_line(line)
        except (OSError, ValueError):
            pass

    def _watch_server_line(self, line: str) -> None:
        self._server_output.append(line)
        if line.startswith("PORT=") or "The VNC desktop is" in line:
            self._ready.set()

    def _wait_for_server(self) -> None:
        assert self.server is not None
        waited = 0.0
        while not self._ready.wait(0.1):
            waited += 0.1
            code = self.server.poll()
            if code is not None or waited >= self.ready_timeout:
                detail = "\n".join(self._server_output) or "no output"
                problem = (
                    f"exited with code {code}"
                    if code is not None
                    else f"did not start within {self.ready_timeout:.0f} seconds"
                )
                raise PresentationError(
                    f"The verification VNC server {problem}:\n{detail}"
                )

    def poll(self) -> str | None:
        if self.viewer is not None and self.viewer.poll() is not None:
            return "closed"
        if self.server is not None and (code := self.server.poll()) is not None:
            return (
                f"the verification VNC server stopped unexpectedly (exit code {code})."
            )
        return None

    def restore(self) -> None:
        """Stop the viewer and server and remove the temporary credentials."""
        for process in (self.viewer, self.server):
            if process is not None:
                _stop_process(process)
        self.viewer = self.server = None
        for reader in self._readers:
            reader.join(1)
        self._readers.clear()
        if self.workdir is not None:
            shutil.rmtree(self.workdir, ignore_errors=True)
            self.workdir = None


def _stop_process(process: subprocess.Popen) -> None:
    try:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(PROCESS_STOP_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(PROCESS_STOP_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        logger.warning("Could not stop VNC process %s", process.pid, exc_info=True)
    finally:
        stream = getattr(process, "stdout", None)
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass


# -- VNC password file -------------------------------------------------------
# TigerVNC's -PasswordFile uses the classic VNC format: the password, padded
# to eight bytes, DES-encrypted with a fixed, publicly known key. It is
# obfuscation, not protection; the file's 0600 permissions protect it.

# VNC's d3des treats each key byte with its bits reversed.
_VNC_KEY = bytes(
    int(f"{byte:08b}"[::-1], 2) for byte in b"\x17\x52\x6b\x06\x23\x4e\x58\x07"
)


def obfuscate_password(password: str) -> bytes:
    data = password.encode("latin-1")[:PASSWORD_LENGTH].ljust(PASSWORD_LENGTH, b"\0")
    return des_encrypt_block(_VNC_KEY, data)


_IP = (58, 50, 42, 34, 26, 18, 10, 2, 60, 52, 44, 36, 28, 20, 12, 4,
       62, 54, 46, 38, 30, 22, 14, 6, 64, 56, 48, 40, 32, 24, 16, 8,
       57, 49, 41, 33, 25, 17, 9, 1, 59, 51, 43, 35, 27, 19, 11, 3,
       61, 53, 45, 37, 29, 21, 13, 5, 63, 55, 47, 39, 31, 23, 15, 7)  # fmt: skip
_FP = (40, 8, 48, 16, 56, 24, 64, 32, 39, 7, 47, 15, 55, 23, 63, 31,
       38, 6, 46, 14, 54, 22, 62, 30, 37, 5, 45, 13, 53, 21, 61, 29,
       36, 4, 44, 12, 52, 20, 60, 28, 35, 3, 43, 11, 51, 19, 59, 27,
       34, 2, 42, 10, 50, 18, 58, 26, 33, 1, 41, 9, 49, 17, 57, 25)  # fmt: skip
_E = (32, 1, 2, 3, 4, 5, 4, 5, 6, 7, 8, 9, 8, 9, 10, 11, 12, 13, 12, 13,
      14, 15, 16, 17, 16, 17, 18, 19, 20, 21, 20, 21, 22, 23, 24, 25,
      24, 25, 26, 27, 28, 29, 28, 29, 30, 31, 32, 1)  # fmt: skip
_P = (16, 7, 20, 21, 29, 12, 28, 17, 1, 15, 23, 26, 5, 18, 31, 10,
      2, 8, 24, 14, 32, 27, 3, 9, 19, 13, 30, 6, 22, 11, 4, 25)  # fmt: skip
_PC1 = (57, 49, 41, 33, 25, 17, 9, 1, 58, 50, 42, 34, 26, 18,
        10, 2, 59, 51, 43, 35, 27, 19, 11, 3, 60, 52, 44, 36,
        63, 55, 47, 39, 31, 23, 15, 7, 62, 54, 46, 38, 30, 22,
        14, 6, 61, 53, 45, 37, 29, 21, 13, 5, 28, 20, 12, 4)  # fmt: skip
_PC2 = (14, 17, 11, 24, 1, 5, 3, 28, 15, 6, 21, 10, 23, 19, 12, 4,
        26, 8, 16, 7, 27, 20, 13, 2, 41, 52, 31, 37, 47, 55, 30, 40,
        51, 45, 33, 48, 44, 49, 39, 56, 34, 53, 46, 42, 50, 36, 29, 32)  # fmt: skip
_SHIFTS = (1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1)
_SBOXES = (
    (14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7,
     0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8,
     4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0,
     15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13),
    (15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10,
     3, 13, 4, 7, 15, 2, 8, 14, 12, 0, 1, 10, 6, 9, 11, 5,
     0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15,
     13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9),
    (10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8,
     13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1,
     13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7,
     1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12),
    (7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15,
     13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9,
     10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4,
     3, 15, 0, 6, 10, 1, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14),
    (2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9,
     14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6,
     4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14,
     11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3),
    (12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11,
     10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8,
     9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6,
     4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13),
    (4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1,
     13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6,
     1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2,
     6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12),
    (13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7,
     1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2,
     7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8,
     2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11),
)  # fmt: skip


def _permute(value: int, table: tuple[int, ...], width: int) -> int:
    result = 0
    for position in table:
        result = (result << 1) | ((value >> (width - position)) & 1)
    return result


def des_encrypt_block(key: bytes, block: bytes) -> bytes:
    """Encrypt one 8-byte block with single DES (FIPS 46-3)."""
    if len(key) != 8 or len(block) != 8:
        raise ValueError("DES uses 8-byte keys and blocks")
    permuted_key = _permute(int.from_bytes(key, "big"), _PC1, 64)
    left_key, right_key = permuted_key >> 28, permuted_key & 0xFFFFFFF
    subkeys = []
    for shift in _SHIFTS:
        left_key = ((left_key << shift) | (left_key >> (28 - shift))) & 0xFFFFFFF
        right_key = ((right_key << shift) | (right_key >> (28 - shift))) & 0xFFFFFFF
        subkeys.append(_permute((left_key << 28) | right_key, _PC2, 56))

    state = _permute(int.from_bytes(block, "big"), _IP, 64)
    left, right = state >> 32, state & 0xFFFFFFFF
    for subkey in subkeys:
        mixed = _permute(right, _E, 32) ^ subkey
        substituted = 0
        for index, sbox in enumerate(_SBOXES):
            chunk = (mixed >> (42 - 6 * index)) & 0x3F
            row = ((chunk & 0x20) >> 4) | (chunk & 1)
            substituted = (substituted << 4) | sbox[row * 16 + ((chunk >> 1) & 0xF)]
        left, right = right, left ^ _permute(substituted, _P, 32)
    return _permute((right << 32) | left, _FP, 64).to_bytes(8, "big")
