"""Component management and platform protocol registration.

No test here changes the real registry, MIME associations, or Launch
Services: every backend runs against fakes and temporary directories.
"""

import json
import os
import plistlib
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path

from goexport.components import ComponentError, ComponentState, ProtocolComponent
from goexport.components.launcher import parse_launcher_record, validate_launcher
from goexport.components.platforms import linux, macos, windows


class FakeRegistry:
    """An in-memory registry keyed by (hive, path)."""

    def __init__(self):
        self.keys: dict[tuple[str, str], dict[str, str]] = {}
        self.writes: list[tuple[str, str, str]] = []

    def read_values(self, hive, path):
        values = self.keys.get((hive, path.lower()))
        return dict(values) if values is not None else None

    def set_value(self, path, name, value):
        self.writes.append((path, name, value))
        parts = path.split("\\")
        for index in range(1, len(parts) + 1):
            self.keys.setdefault(("HKCU", "\\".join(parts[:index]).lower()), {})
        self.keys[("HKCU", path.lower())][name] = value

    def delete_tree(self, path):
        prefix = path.lower()
        for key in list(self.keys):
            if key[0] == "HKCU" and (
                key[1] == prefix or key[1].startswith(prefix + "\\")
            ):
                del self.keys[key]


def completed(arguments, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(arguments, returncode, stdout, stderr)


class LauncherMixin:
    def make_launcher(self, *names: str) -> tuple[str, ...]:
        directory = Path(self.temp.name) / "Go Export Folder"
        directory.mkdir(exist_ok=True)
        paths = []
        for name in names or ("GoExport.exe",):
            path = directory / name
            path.write_text("x", encoding="utf-8")
            paths.append(str(path))
        return tuple(paths)


class LauncherTests(LauncherMixin, unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp.cleanup()

    def test_launcher_must_exist_and_be_absolute(self):
        launcher = self.make_launcher()
        validate_launcher(launcher)
        with self.assertRaises(ComponentError):
            validate_launcher(("relative/GoExport",))
        with self.assertRaises(ComponentError):
            validate_launcher((launcher[0] + ".missing",))
        with self.assertRaises(ComponentError):
            validate_launcher((launcher[0] + "\nevil",))

    def test_launcher_records_reject_invalid_values(self):
        self.assertEqual(parse_launcher_record('["a", "b"]'), ("a", "b"))
        self.assertEqual(parse_launcher_record(["a"]), ("a",))
        for value in (None, "", "not json", "[]", '[""]', "[1]", '{"a": 1}'):
            with self.subTest(value=value):
                self.assertEqual(parse_launcher_record(value), ())


class WindowsBackendTests(LauncherMixin, unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.registry = FakeRegistry()
        self.backend = windows.WindowsProtocolBackend(self.registry)

    def tearDown(self):
        self.temp.cleanup()

    def component(self, launcher):
        return ProtocolComponent(self.backend, launcher=launcher, system="Windows")

    def test_command_quotes_paths_with_spaces_and_passes_url_as_one_argument(self):
        command = windows.build_command(
            (r"C:\Program Files\Python\python.exe", r"D:\My Tools\GoExport\main.py")
        )
        self.assertEqual(
            command,
            r'"C:\Program Files\Python\python.exe" "D:\My Tools\GoExport\main.py" '
            r'handle-url -- "%1"',
        )

    def test_command_rejects_percent_and_quote_characters(self):
        for path in (r"C:\100%\GoExport.exe", 'C:\\a"b\\GoExport.exe'):
            with self.subTest(path=path), self.assertRaises(ComponentError):
                windows.build_command((path,))

    def test_install_writes_owned_url_protocol_with_marker_first(self):
        launcher = self.make_launcher()
        result = self.component(launcher).install()

        self.assertEqual(result.action, "installed")
        self.assertEqual(self.registry.writes[0][1], windows.OWNER_VALUE)
        scheme = self.registry.read_values("HKCU", windows.SCHEME_KEY)
        self.assertEqual(scheme[""], "URL:GoExport Protocol")
        self.assertIn("URL Protocol", scheme)
        self.assertEqual(json.loads(scheme[windows.LAUNCHER_VALUE]), list(launcher))
        command = self.registry.read_values("HKCU", windows.COMMAND_KEY)[""]
        self.assertEqual(command, f'"{launcher[0]}" handle-url -- "%1"')
        self.assertTrue(result.status.valid)
        self.assertTrue(result.status.current)

    def test_install_is_idempotent(self):
        launcher = self.make_launcher()
        component = self.component(launcher)
        component.install()
        writes = len(self.registry.writes)

        result = component.install()

        self.assertEqual(result.action, "unchanged")
        self.assertEqual(len(self.registry.writes), writes)

    def test_reinstall_rewrites_a_valid_registration(self):
        launcher = self.make_launcher()
        component = self.component(launcher)
        component.install()

        self.assertEqual(component.install(reinstall=True).action, "repaired")

    def test_moved_installation_is_stale_and_repairable(self):
        old = self.make_launcher("Old.exe")
        self.component(old).install()
        Path(old[0]).unlink()
        new = self.make_launcher("GoExport.exe")
        component = self.component(new)

        status = component.status()
        self.assertIs(status.state, ComponentState.STALE)
        self.assertEqual(status.label, "Stale registration")
        self.assertEqual(status.actions, ("repair", "uninstall"))
        self.assertIn(old[0], status.detail)

        result = component.install()
        self.assertEqual(result.action, "repaired")
        command = self.registry.read_values("HKCU", windows.COMMAND_KEY)[""]
        self.assertIn(new[0], command)

    def test_other_copy_is_not_silently_redirected(self):
        other = self.make_launcher("Other.exe")
        self.component(other).install()
        component = self.component(self.make_launcher("GoExport.exe"))

        status = component.status()
        self.assertIs(status.state, ComponentState.INSTALLED)
        self.assertFalse(status.current)
        with self.assertRaisesRegex(ComponentError, "--reinstall"):
            component.install()
        self.assertEqual(component.install(reinstall=True).action, "repaired")

    def test_foreign_registration_is_a_conflict_and_never_changed(self):
        self.registry.set_value(windows.SCHEME_KEY, "", "URL:Other")
        self.registry.set_value(windows.COMMAND_KEY, "", '"C:\\Other.exe" "%1"')
        before = dict(self.registry.keys)
        component = self.component(self.make_launcher())

        status = component.status()
        self.assertIs(status.state, ComponentState.ERROR)
        self.assertFalse(status.owned)
        self.assertEqual(status.actions, ())
        self.assertIn("another application", status.detail)
        with self.assertRaises(ComponentError):
            component.install()
        self.assertEqual(component.uninstall().action, "unchanged")
        self.assertEqual(self.registry.keys, before)

    def test_changed_command_is_reported_and_repaired(self):
        launcher = self.make_launcher()
        component = self.component(launcher)
        component.install()
        self.registry.set_value(windows.COMMAND_KEY, "", '"C:\\evil.exe" "%1"')

        status = component.status()
        self.assertIs(status.state, ComponentState.ERROR)
        self.assertTrue(status.owned)
        self.assertEqual(status.actions, ("repair", "uninstall"))
        self.assertTrue(any("changed" in problem for problem in status.problems))
        self.assertEqual(component.install().action, "repaired")
        self.assertTrue(component.status().valid)

    def test_uninstall_removes_only_owned_key_and_is_idempotent(self):
        self.registry.set_value(r"Software\Classes\other", "", "keep")
        component = self.component(self.make_launcher())
        component.install()

        self.assertEqual(component.uninstall().action, "removed")
        self.assertIsNone(self.registry.read_values("HKCU", windows.SCHEME_KEY))
        self.assertIsNotNone(
            self.registry.read_values("HKCU", r"Software\Classes\other")
        )
        self.assertEqual(component.uninstall().action, "unchanged")

    def test_machine_wide_registration_is_reported_but_untouched(self):
        self.registry.keys[("HKLM", windows.SCHEME_KEY.lower())] = {"": "URL:V1"}
        self.registry.keys[("HKLM", windows.COMMAND_KEY.lower())] = {
            "": '"C:\\GoExport_CLI.exe" --protocol "%1"'
        }
        component = self.component(self.make_launcher())

        status = component.status()
        self.assertIs(status.state, ComponentState.NOT_INSTALLED)
        self.assertTrue(any("HKEY_LOCAL_MACHINE" in note for note in status.notes))
        component.install()
        self.assertIn(("HKLM", windows.SCHEME_KEY.lower()), self.registry.keys)


@unittest.skipUnless(
    os.name == "nt" and os.environ.get("GOEXPORT_PROTOCOL_INTEGRATION") == "1",
    "Set GOEXPORT_PROTOCOL_INTEGRATION=1 on Windows to use the real registry.",
)
class WindowsRegistryIntegrationTests(unittest.TestCase):
    """Exercises winreg under a temporary HKCU\\Software key only."""

    def test_round_trip_under_temporary_key(self):
        import uuid

        registry = windows.WindowsRegistry()
        root = rf"Software\GoExport-test-{uuid.uuid4().hex}"
        try:
            registry.set_value(root + r"\shell\open\command", "", '"x" "%1"')
            registry.set_value(root, "URL Protocol", "")
            self.assertEqual(registry.read_values("HKCU", root), {"URL Protocol": ""})
            self.assertEqual(
                registry.read_values("HKCU", root + r"\shell\open\command"),
                {"": '"x" "%1"'},
            )
        finally:
            registry.delete_tree(root)
        self.assertIsNone(registry.read_values("HKCU", root))


class LinuxBackendTests(LauncherMixin, unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.data_home = root / "data"
        self.config_home = root / "config"
        self.commands: list[list[str]] = []
        self.tools = {"xdg-open"}

    def tearDown(self):
        self.temp.cleanup()

    def backend(self):
        return linux.LinuxProtocolBackend(
            data_home=self.data_home,
            config_home=self.config_home,
            runner=self.run_tool,
            which=lambda name: f"/usr/bin/{name}" if name in self.tools else None,
        )

    def run_tool(self, arguments):
        arguments = list(arguments)
        self.commands.append(arguments)
        mimeapps = self.config_home / "mimeapps.list"
        if arguments[:3] == ["xdg-mime", "query", "default"]:
            return completed(
                arguments, stdout=(linux.read_default_handler(mimeapps) or "") + "\n"
            )
        if arguments[:2] == ["xdg-mime", "default"]:
            current = mimeapps.read_text(encoding="utf-8") if mimeapps.exists() else ""
            mimeapps.parent.mkdir(parents=True, exist_ok=True)
            mimeapps.write_text(
                linux.set_default_handler(current, arguments[2]), encoding="utf-8"
            )
        return completed(arguments)

    def component(self, launcher):
        return ProtocolComponent(self.backend(), launcher=launcher, system="Linux")

    def test_exec_quotes_paths_with_spaces_and_special_characters(self):
        launcher = ('/opt/Go Export/$HOME`x`/Go"Export', "/srv/100%/main.py")
        self.assertEqual(
            linux.build_exec(launcher),
            '"/opt/Go Export/\\$HOME\\`x\\`/Go\\"Export" "/srv/100%%/main.py" '
            "handle-url -- %u",
        )
        entry = linux.build_desktop_entry(launcher)
        parsed = linux.parse_desktop_entry(entry)
        self.assertEqual(parsed["Exec"], linux.build_exec(launcher))
        self.assertEqual(
            linux.parse_launcher_record(parsed[linux.LAUNCHER_KEY]), launcher
        )

    def test_desktop_entry_declares_scheme_handler(self):
        entry = linux.parse_desktop_entry(linux.build_desktop_entry(("/a/GoExport",)))
        self.assertEqual(entry["MimeType"], "x-scheme-handler/goexport;")
        self.assertEqual(entry["Type"], "Application")
        self.assertEqual(entry["Terminal"], "true")
        self.assertEqual(entry[linux.OWNER_KEY], "GoExport")

    def test_install_with_xdg_mime_preserves_other_associations(self):
        self.tools |= {"xdg-mime", "update-desktop-database"}
        mimeapps = self.config_home / "mimeapps.list"
        mimeapps.parent.mkdir(parents=True)
        mimeapps.write_text(
            "[Default Applications]\ntext/html=firefox.desktop;\n\n"
            "[Added Associations]\nimage/png=gimp.desktop;\n",
            encoding="utf-8",
        )
        launcher = self.make_launcher("GoExport")

        result = self.component(launcher).install()

        self.assertEqual(result.action, "installed")
        self.assertTrue(result.status.valid)
        self.assertIn(
            ["xdg-mime", "default", linux.DESKTOP_ID, linux.MIME_TYPE], self.commands
        )
        self.assertTrue(any(c[0] == "update-desktop-database" for c in self.commands))
        text = mimeapps.read_text(encoding="utf-8")
        self.assertIn("text/html=firefox.desktop;", text)
        self.assertIn("image/png=gimp.desktop;", text)
        if os.name != "nt":
            desktop = self.data_home / "applications" / linux.DESKTOP_ID
            self.assertEqual(desktop.stat().st_mode & 0o777, 0o644)

    def test_install_without_xdg_mime_edits_mimeapps_list(self):
        launcher = self.make_launcher("GoExport")
        result = self.component(launcher).install()

        self.assertTrue(result.status.valid)
        self.assertEqual(
            linux.read_default_handler(self.config_home / "mimeapps.list"),
            linux.DESKTOP_ID,
        )

    def test_other_default_handler_is_a_conflict(self):
        mimeapps = self.config_home / "mimeapps.list"
        mimeapps.parent.mkdir(parents=True)
        mimeapps.write_text(
            "[Default Applications]\nx-scheme-handler/goexport=other.desktop;\n",
            encoding="utf-8",
        )
        component = self.component(self.make_launcher("GoExport"))

        status = component.status()
        self.assertIs(status.state, ComponentState.ERROR)
        self.assertFalse(status.owned)
        self.assertIn("other.desktop", status.detail)
        with self.assertRaises(ComponentError):
            component.install()
        self.assertFalse((self.data_home / "applications" / linux.DESKTOP_ID).exists())

    def test_uninstall_removes_only_goexport_entries(self):
        component = self.component(self.make_launcher("GoExport"))
        component.install()
        mimeapps = self.config_home / "mimeapps.list"
        mimeapps.write_text(
            mimeapps.read_text(encoding="utf-8")
            + "text/html=firefox.desktop;\n[Added Associations]\n"
            f"x-scheme-handler/goexport={linux.DESKTOP_ID};other.desktop;\n",
            encoding="utf-8",
        )

        self.assertEqual(component.uninstall().action, "removed")

        self.assertFalse((self.data_home / "applications" / linux.DESKTOP_ID).exists())
        text = mimeapps.read_text(encoding="utf-8")
        self.assertNotIn(linux.DESKTOP_ID, text)
        self.assertIn("x-scheme-handler/goexport=other.desktop;", text)
        self.assertIn("text/html=firefox.desktop;", text)
        self.assertEqual(component.uninstall().action, "unchanged")

    def test_foreign_desktop_file_is_left_alone(self):
        desktop = self.data_home / "applications" / linux.DESKTOP_ID
        desktop.parent.mkdir(parents=True)
        desktop.write_text("[Desktop Entry]\nName=Other\n", encoding="utf-8")
        component = self.component(self.make_launcher("GoExport"))

        self.assertFalse(component.status().owned)
        self.assertEqual(component.uninstall().action, "unchanged")
        self.assertTrue(desktop.exists())

    def test_moved_installation_is_stale(self):
        old = self.make_launcher("Old")
        self.component(old).install()
        Path(old[0]).unlink()

        status = self.component(self.make_launcher("GoExport")).status()

        self.assertIs(status.state, ComponentState.STALE)

    def test_missing_xdg_open_is_reported(self):
        self.tools = set()
        status = self.component(self.make_launcher("GoExport")).status()
        self.assertTrue(any("xdg-open" in note for note in status.notes))

    def test_mimeapps_helpers_keep_unrelated_lines(self):
        text = "# comment\n[Default Applications]\na/b=x.desktop;\n"
        updated = linux.set_default_handler(text, "g.desktop")
        self.assertEqual(
            updated,
            "# comment\n[Default Applications]\n"
            "x-scheme-handler/goexport=g.desktop;\na/b=x.desktop;\n",
        )
        self.assertEqual(linux.remove_association(updated, "g.desktop"), text)
        promoted = linux.set_default_handler(
            "[Default Applications]\nx-scheme-handler/goexport=o.desktop;g.desktop;\n",
            "g.desktop",
        )
        self.assertIn("x-scheme-handler/goexport=g.desktop;o.desktop;", promoted)


class FakeLaunchServices:
    def __init__(self, handler=None):
        self.handler = handler

    def default_handler(self, scheme):
        return self.handler

    def set_default_handler(self, scheme, bundle_id):
        self.handler = bundle_id


class MacOSBackendTests(LauncherMixin, unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.bundle = Path(self.temp.name) / "Go Export" / macos.BUNDLE_NAME
        self.commands: list[list[str]] = []
        self.scripts: list[str] = []
        self.launch_services = FakeLaunchServices()
        self.failing_tool = None

    def tearDown(self):
        self.temp.cleanup()

    def run_tool(self, arguments):
        arguments = list(arguments)
        self.commands.append(arguments)
        if self.failing_tool and arguments[0] == self.failing_tool:
            return completed(arguments, 1, stderr=f"{self.failing_tool} failed")
        if arguments[0] == "osacompile":
            self.scripts.append(Path(arguments[3]).read_text(encoding="utf-8"))
            contents = Path(arguments[2]) / "Contents"
            contents.mkdir(parents=True)
            with (contents / "Info.plist").open("wb") as output:
                plistlib.dump({"CFBundleExecutable": "applet"}, output)
        return completed(arguments)

    def component(self, launcher, bundle=None):
        backend = macos.MacOSProtocolBackend(
            bundle_path=bundle or self.bundle,
            runner=self.run_tool,
            launch_services=self.launch_services,
        )
        return ProtocolComponent(backend, launcher=launcher, system="Darwin")

    def test_install_generates_signed_registered_applet(self):
        launcher = self.make_launcher("GoExport")
        result = self.component(launcher).install()

        self.assertEqual(result.action, "installed")
        self.assertTrue(result.status.valid)
        with (self.bundle / "Contents" / "Info.plist").open("rb") as source:
            plist = plistlib.load(source)
        self.assertEqual(plist["CFBundleIdentifier"], macos.BUNDLE_ID)
        self.assertEqual(
            plist["CFBundleURLTypes"][0]["CFBundleURLSchemes"], ["goexport"]
        )
        self.assertEqual(plist[macos.OWNER_KEY], "GoExport")
        self.assertEqual(plist[macos.LAUNCHER_KEY], list(launcher))
        tools = [command[0] for command in self.commands]
        self.assertEqual(tools, ["osacompile", "codesign", macos.LSREGISTER])
        self.assertEqual(self.launch_services.handler, macos.BUNDLE_ID)

    def test_applescript_shell_quotes_launcher_and_url(self):
        script = macos.build_applescript(("/Users/a b/Go'Export",))
        self.assertIn("on open location requestURL", script)
        self.assertIn("quoted form of requestURL", script)
        line = next(row for row in script.splitlines() if "goexportCommand to" in row)
        literal = line.split(" to ", 1)[1]
        command = literal[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        self.assertEqual(
            shlex.split(command), ["/Users/a b/Go'Export", "handle-url", "--"]
        )
        self.assertNotIn("property", script)

    def test_other_default_handler_is_a_conflict(self):
        self.launch_services.handler = "com.example.other"
        component = self.component(self.make_launcher("GoExport"))

        status = component.status()
        self.assertIs(status.state, ComponentState.ERROR)
        self.assertFalse(status.owned)
        with self.assertRaises(ComponentError):
            component.install()
        self.assertEqual(self.commands, [])

    def test_failed_tool_is_reported_and_not_claimed_as_success(self):
        self.failing_tool = macos.LSREGISTER
        with self.assertRaisesRegex(ComponentError, "Launch Services"):
            self.component(self.make_launcher("GoExport")).install()

    def test_handler_not_resolved_is_not_reported_as_installed(self):
        component = self.component(self.make_launcher("GoExport"))
        component.install()
        self.launch_services.handler = None

        status = component.status()
        self.assertIs(status.state, ComponentState.ERROR)
        self.assertTrue(status.owned)

    def test_uninstall_removes_owned_bundle_and_is_idempotent(self):
        component = self.component(self.make_launcher("GoExport"))
        component.install()

        self.assertEqual(component.uninstall().action, "removed")
        self.assertFalse(self.bundle.exists())
        self.assertIn([macos.LSREGISTER, "-u", str(self.bundle)], self.commands)
        self.launch_services.handler = None
        self.assertEqual(component.uninstall().action, "unchanged")

    def test_foreign_bundle_is_not_removed(self):
        contents = self.bundle / "Contents"
        contents.mkdir(parents=True)
        with (contents / "Info.plist").open("wb") as output:
            plistlib.dump({"CFBundleIdentifier": "com.example"}, output)
        component = self.component(self.make_launcher("GoExport"))

        self.assertEqual(component.uninstall().action, "unchanged")
        self.assertTrue(self.bundle.exists())

    def test_app_translocation_is_refused(self):
        bundle = (
            Path("/private/var/folders/x/AppTranslocation/abc/d") / macos.BUNDLE_NAME
        )
        with self.assertRaisesRegex(ComponentError, "App Translocation"):
            self.component(self.make_launcher("GoExport"), bundle).install()


class UnsupportedPlatformTests(unittest.TestCase):
    def test_unsupported_system_reports_and_refuses(self):
        component = ProtocolComponent(backend=None, launcher=("/x",), system="Plan9")

        status = component.status()

        self.assertIs(status.state, ComponentState.UNSUPPORTED)
        self.assertEqual(status.actions, ())
        self.assertIn("Plan9", status.detail)
        with self.assertRaises(ComponentError):
            component.install()
        with self.assertRaises(ComponentError):
            component.uninstall()

    def test_status_serializes_for_json_output(self):
        component = ProtocolComponent(backend=None, launcher=("/x",), system="Plan9")
        data = component.status().to_dict()
        self.assertEqual(data["state"], "unsupported")
        self.assertEqual(data["label"], "Unsupported")
        self.assertEqual(data["actions"], [])
        json.dumps(data)


if __name__ == "__main__":
    unittest.main()
