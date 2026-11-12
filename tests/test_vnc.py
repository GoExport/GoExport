import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from goexport import config
from goexport.services import vnc
from goexport.services.verification import PresentationError
from goexport.services.vnc import (
    VNCPresenter,
    VNCTools,
    des_encrypt_block,
    find_tools,
    obfuscate_password,
    tool_environment,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import bundle_linux_vnc  # noqa: E402

TOOLS = VNCTools(
    Path("/opt/goexport/bin/vnc/x11vnc"),
    Path("/opt/goexport/bin/vnc/vncviewer"),
    Path("/opt/goexport/bin/vnc/lib"),
)


class FakeProcess:
    _next_pid = 1000

    def __init__(self, command, ready=True, exit_code=None, **kwargs):
        FakeProcess._next_pid += 1
        self.pid = FakeProcess._next_pid
        self.command = command
        self.kwargs = kwargs
        self.returncode = exit_code
        self.terminated = False
        self.killed = False
        lines = ["x11vnc starting\n", "PORT=5901\n"] if ready else ["x11vnc failed\n"]
        self.stdout = io.StringIO("".join(lines) if "x11vnc" in command[0] else "")

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, _timeout=None):
        return self.returncode


class FakePopen:
    def __init__(self, server_ready=True, server_exit=None, fail_viewer=False):
        self.processes = []
        self.server_ready = server_ready
        self.server_exit = server_exit
        self.fail_viewer = fail_viewer
        self.password_files = {}

    def __call__(self, command, **kwargs):
        for argument in command:
            for prefix in ("rm:", "-PasswordFile="):
                if prefix in argument:
                    path = Path(argument.split(prefix, 1)[1])
                    self.password_files[command[0]] = (
                        path,
                        path.read_bytes(),
                        stat.S_IMODE(path.stat().st_mode),
                    )
        if self.fail_viewer and "vncviewer" in command[0]:
            raise OSError("cannot execute binary file")
        is_server = "x11vnc" in command[0]
        process = FakeProcess(
            command,
            ready=self.server_ready if is_server else True,
            exit_code=self.server_exit if is_server else None,
            **kwargs,
        )
        self.processes.append(process)
        return process


def display(inherited=":0", xauthority="/home/user/.Xauthority"):
    return SimpleNamespace(
        capture_display=":99",
        inherited_display=inherited,
        inherited_xauthority=xauthority,
        active=True,
    )


class PasswordTests(unittest.TestCase):
    def test_des_matches_fips_test_vector(self):
        ciphertext = des_encrypt_block(
            bytes.fromhex("133457799BBCDFF1"), bytes.fromhex("0123456789ABCDEF")
        )
        self.assertEqual(ciphertext.hex(), "85e813540f0ab405")

    def test_password_file_matches_vncpasswd(self):
        # ``printf password | tigervncpasswd -f | xxd -p``
        self.assertEqual(obfuscate_password("password").hex(), "dbd83cfd727a1458")

    def test_generated_passwords_use_all_vnc_auth_characters(self):
        password = vnc.generate_password()
        self.assertEqual(len(password), 8)
        self.assertNotEqual(password, vnc.generate_password())


class EnvironmentTests(unittest.TestCase):
    def test_viewer_uses_preserved_desktop_and_bundled_libraries(self):
        env = tool_environment(
            TOOLS,
            ":0",
            "/home/user/.Xauthority",
            base={"DISPLAY": ":99", "LD_LIBRARY_PATH": "/usr/local/lib"},
        )
        self.assertEqual(env["DISPLAY"], ":0")
        self.assertEqual(env["XAUTHORITY"], "/home/user/.Xauthority")
        self.assertEqual(
            env["LD_LIBRARY_PATH"],
            os.pathsep.join([str(TOOLS.library_dir), "/usr/local/lib"]),
        )

    def test_pyinstaller_library_path_is_not_inherited(self):
        env = tool_environment(
            TOOLS,
            ":0",
            None,
            base={
                "LD_LIBRARY_PATH": "/tmp/_MEI123:/usr/lib/custom",
                "LD_LIBRARY_PATH_ORIG": "/usr/lib/custom",
                "XAUTHORITY": "/tmp/other",
            },
        )
        self.assertNotIn("_MEI", env["LD_LIBRARY_PATH"])
        self.assertTrue(env["LD_LIBRARY_PATH"].endswith("/usr/lib/custom"))
        self.assertNotIn("LD_LIBRARY_PATH_ORIG", env)
        self.assertNotIn("XAUTHORITY", env)

    def test_server_environment_is_x11_only(self):
        env = tool_environment(
            TOOLS,
            ":99",
            None,
            base={"WAYLAND_DISPLAY": "wayland-0", "XDG_SESSION_TYPE": "wayland"},
            x11_only=True,
        )
        self.assertNotIn("WAYLAND_DISPLAY", env)
        self.assertEqual(env["XDG_SESSION_TYPE"], "x11")
        self.assertEqual(env["DISPLAY"], ":99")


class ToolDiscoveryTests(unittest.TestCase):
    def test_bundled_tools_are_preferred(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lib").mkdir()
            for name in ("x11vnc", "vncviewer"):
                (root / name).write_bytes(b"\x7fELF")
            tools = find_tools(root)
        self.assertEqual(tools.server, root / "x11vnc")
        self.assertEqual(tools.library_dir, root / "lib")

    def test_missing_tools_explain_reinstall(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(vnc.shutil, "which", return_value=None),
            self.assertRaisesRegex(PresentationError, "Reinstall GoExport"),
        ):
            find_tools(Path(directory))


class PresenterTests(unittest.TestCase):
    def test_show_starts_localhost_server_and_viewer_without_exposing_password(self):
        popen = FakePopen()
        presenter = VNCPresenter(display(), tools=TOOLS, popen=popen)
        presenter.show()
        workdir = presenter.workdir
        try:
            server, viewer = popen.processes
            self.assertIn("-localhost", server.command)
            self.assertEqual(
                server.command[server.command.index("-display") + 1], ":99"
            )
            self.assertEqual(
                server.command[server.command.index("-rfbportv6") + 1], "-1"
            )
            self.assertIn("-nevershared", server.command)
            self.assertEqual(viewer.command[-1], f"127.0.0.1::{presenter.port}")
            self.assertIn("-RemoteResize=0", viewer.command)
            self.assertEqual(server.kwargs["env"]["DISPLAY"], ":99")
            self.assertEqual(viewer.kwargs["env"]["DISPLAY"], ":0")
            self.assertEqual(
                viewer.kwargs["env"]["XAUTHORITY"], "/home/user/.Xauthority"
            )
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(workdir.stat().st_mode), 0o700)

            server_file, server_secret, server_mode = popen.password_files[
                str(TOOLS.server)
            ]
            _viewer_file, viewer_secret, viewer_mode = popen.password_files[
                str(TOOLS.viewer)
            ]
            password = server_secret.decode().strip()
            self.assertEqual(obfuscate_password(password), viewer_secret)
            if os.name != "nt":
                self.assertEqual((server_mode, viewer_mode), (0o600, 0o600))
            for process in popen.processes:
                self.assertFalse(
                    any(password in argument for argument in process.command)
                )
            self.assertEqual(server_file.parent, workdir)
            self.assertIsNone(presenter.poll())
        finally:
            presenter.restore()
        self.assertTrue(all(process.terminated for process in popen.processes))
        self.assertFalse(workdir.exists())
        self.assertIsNone(presenter.workdir)

    def test_closed_viewer_is_reported(self):
        popen = FakePopen()
        presenter = VNCPresenter(display(), tools=TOOLS, popen=popen)
        presenter.show()
        try:
            popen.processes[1].returncode = 0
            self.assertEqual(presenter.poll(), "closed")
        finally:
            presenter.restore()

    def test_server_exit_is_a_failure(self):
        popen = FakePopen()
        presenter = VNCPresenter(display(), tools=TOOLS, popen=popen)
        presenter.show()
        try:
            popen.processes[0].returncode = 1
            self.assertIn("stopped unexpectedly", presenter.poll())
        finally:
            presenter.restore()

    def test_server_that_fails_to_start_is_cleaned_up(self):
        popen = FakePopen(server_ready=False, server_exit=1)
        presenter = VNCPresenter(display(), tools=TOOLS, popen=popen, ready_timeout=1)
        with self.assertRaisesRegex(PresentationError, "exited with code 1"):
            presenter.show()
        self.assertEqual(len(popen.processes), 1)
        self.assertIsNone(presenter.workdir)

    def test_viewer_that_cannot_start_stops_the_server(self):
        popen = FakePopen(fail_viewer=True)
        presenter = VNCPresenter(display(), tools=TOOLS, popen=popen)
        with self.assertRaisesRegex(PresentationError, "verification viewer"):
            presenter.show()
        self.assertTrue(popen.processes[0].terminated)
        self.assertIsNone(presenter.workdir)

    def test_missing_desktop_is_a_clear_error(self):
        popen = FakePopen()
        presenter = VNCPresenter(display(inherited=None), tools=TOOLS, popen=popen)
        with (
            patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}),
            self.assertRaisesRegex(PresentationError, "DISPLAY was not set.*XWayland"),
        ):
            presenter.show()
        self.assertEqual(popen.processes, [])

    def test_unresponsive_processes_are_killed(self):
        process = FakeProcess(["vncviewer"])
        process.terminate = lambda: None

        def wait(timeout=None):
            if not process.killed:
                raise subprocess.TimeoutExpired("vncviewer", timeout)
            return -9

        process.wait = wait
        vnc._stop_process(process)
        self.assertTrue(process.killed)


class BundleScriptTests(unittest.TestCase):
    def test_ldd_parsing_and_system_library_exclusions(self):
        output = """
        linux-vdso.so.1 (0x00007ffd)
        libvncserver.so.1 => /lib/x86_64-linux-gnu/libvncserver.so.1 (0x00007f1)
        libX11.so.6 => /lib/x86_64-linux-gnu/libX11.so.6 (0x00007f2)
        libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f3)
        libmissing.so.1 => not found
        /lib64/ld-linux-x86-64.so.2 (0x00007f4)
        """
        libraries = bundle_linux_vnc.parse_ldd(output)
        self.assertEqual(
            set(libraries), {"libvncserver.so.1", "libX11.so.6", "libc.so.6"}
        )
        self.assertEqual(
            [name for name in libraries if bundle_linux_vnc.should_bundle(name)],
            ["libvncserver.so.1"],
        )
        self.assertFalse(bundle_linux_vnc.should_bundle("libnss_files.so.2"))


def _real_vnc_available():
    if config.SYSTEM != "Linux" or not os.environ.get("DISPLAY"):
        return False
    try:
        find_tools()
    except PresentationError:
        return False
    return bool(shutil.which("Xvfb"))


@unittest.skipUnless(
    _real_vnc_available() and os.environ.get("GOEXPORT_VNC_INTEGRATION") == "1",
    "Set GOEXPORT_VNC_INTEGRATION=1 on Linux with a desktop, Xvfb and VNC tools.",
)
class RealVNCIntegrationTests(unittest.TestCase):
    def test_viewer_connects_to_the_existing_xvfb_display_and_cleans_up(self):
        from goexport.services.display import LinuxDisplay

        desktop = os.environ["DISPLAY"]
        virtual = LinuxDisplay(size=(640, 480))
        virtual.start()
        try:
            presenter = VNCPresenter(virtual)
            # x11vnc logs dozens of lines once a client connects, so "Got
            # connection" quickly leaves the presenter's short output buffer;
            # record every line instead.
            server_lines: list[str] = []
            watch = presenter._watch_server_line

            def record(line: str) -> None:
                server_lines.append(line)
                watch(line)

            with patch.object(presenter, "_watch_server_line", side_effect=record):
                presenter.show()
            workdir = presenter.workdir
            server, viewer = presenter.server, presenter.viewer
            try:
                self.assertEqual(virtual.inherited_display, desktop)
                self.assertEqual(os.listdir(workdir), ["viewer.passwd"])
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and not any(
                    "Got connection" in line for line in server_lines
                ):
                    time.sleep(0.2)
                self.assertIsNone(presenter.poll())
                self.assertTrue(
                    any("Got connection" in line for line in server_lines),
                    "x11vnc output:\n" + "\n".join(server_lines),
                )
            finally:
                presenter.restore()
            self.assertIsNotNone(server.poll())
            self.assertIsNotNone(viewer.poll())
            self.assertFalse(workdir.exists())
            self.assertTrue(virtual.active)
        finally:
            virtual.stop()


if __name__ == "__main__":
    unittest.main()
