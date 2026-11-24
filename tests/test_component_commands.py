"""CLI behaviour of install, uninstall, status, and handle-url."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import MagicMock, patch

from goexport import cli
from goexport.commands import components as commands
from goexport.commands import handle_url
from goexport.components import ComponentError, ComponentState, ProtocolComponent
from goexport.helpers import ConfirmationDeclined
from goexport.reporting import Reporter
from tests.test_components import FakeRegistry


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = cli.build_parser()

    def test_yes_is_accepted_before_or_after_the_command(self):
        before = self.parser.parse_args(["-y", "install", "protocol"])
        after = self.parser.parse_args(["install", "protocol", "--yes"])
        neither = self.parser.parse_args(["install", "protocol"])
        self.assertTrue(before.yes)
        self.assertTrue(after.yes)
        self.assertFalse(neither.yes)
        self.assertIs(before.func, commands.install_entry)

    def test_component_commands(self):
        self.assertTrue(
            self.parser.parse_args(["install", "protocol", "--reinstall"]).reinstall
        )
        self.assertIs(
            self.parser.parse_args(["uninstall", "protocol"]).func,
            commands.uninstall_entry,
        )
        self.assertIsNone(self.parser.parse_args(["status"]).component)
        self.assertEqual(
            self.parser.parse_args(["status", "protocol"]).component, "protocol"
        )

    def test_invalid_arguments_exit_with_usage_error(self):
        for argv in (
            ["install"],
            ["install", "chromium"],
            ["uninstall", "protocol", "--reinstall"],
            ["status", "ffmpeg"],
            ["handle-url"],
        ):
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    self.parser.parse_args(argv)
                self.assertEqual(raised.exception.code, 2)

    def test_component_commands_do_not_bootstrap_runtime_dependencies(self):
        for argv in (["install", "protocol"], ["uninstall", "protocol"], ["status"]):
            with self.subTest(argv=argv):
                args = self.parser.parse_args(argv)
                self.assertFalse(getattr(args, "runtime_dependencies", ()))


class ComponentCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        launcher = Path(self.temp.name) / "Go Export" / "GoExport.exe"
        launcher.parent.mkdir()
        launcher.write_text("x", encoding="utf-8")
        from goexport.components.platforms.windows import WindowsProtocolBackend

        self.registry = FakeRegistry()
        self.component = ProtocolComponent(
            WindowsProtocolBackend(self.registry),
            launcher=(str(launcher),),
            system="Windows",
        )
        patcher = patch.object(commands, "get_component", return_value=self.component)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.temp.cleanup)

    def run_command(self, argv, interactive=False, answer=False):
        """Run the full CLI and return (exit code, JSON events)."""
        stream = io.StringIO()
        args = cli.build_parser().parse_args(argv)
        with (
            patch.object(cli, "setup_logging"),
            patch.object(
                cli, "Reporter", lambda json_mode, stream=None: Reporter(json_mode, out)
            ),
            patch("goexport.helpers.interactive_terminal", return_value=interactive),
            patch("goexport.helpers.Confirm.ask", return_value=answer) as ask,
            patch("goexport.helpers.Console"),
        ):
            out = stream
            code = cli.run(args)
        self.asked = ask.called
        events = [json.loads(line) for line in stream.getvalue().splitlines() if line]
        return code, events

    def test_status_reports_json_result(self):
        code, events = self.run_command(["--json", "status"])
        self.assertEqual(code, 0)
        self.assertEqual(events[-1]["command"], "status")
        self.assertEqual(events[-1]["components"][0]["state"], "not_installed")
        self.assertEqual(events[-1]["components"][0]["actions"], ["install"])

    def test_install_with_yes_installs_without_prompting(self):
        code, events = self.run_command(["--json", "-y", "install", "protocol"])
        self.assertEqual(code, 0)
        self.assertFalse(self.asked)
        self.assertEqual(events[-1]["action"], "installed")
        self.assertEqual(events[-1]["status"]["state"], "installed")

    def test_noninteractive_without_yes_fails_safely(self):
        code, events = self.run_command(["install", "protocol"], interactive=False)
        self.assertEqual(code, 1)
        self.assertFalse(self.asked)
        self.assertIs(self.component.status().state, ComponentState.NOT_INSTALLED)

    def test_json_without_yes_fails_without_prompting(self):
        code, events = self.run_command(
            ["--json", "install", "protocol"], interactive=True
        )
        self.assertEqual(code, 1)
        self.assertEqual(events[-1]["event"], "error")
        self.assertIn("--yes", events[-1]["message"])
        self.assertFalse(self.asked)

    def test_interactive_confirmation_is_required(self):
        code, _ = self.run_command(
            ["install", "protocol"], interactive=True, answer=False
        )
        self.assertEqual(code, 1)
        self.assertTrue(self.asked)
        self.assertIs(self.component.status().state, ComponentState.NOT_INSTALLED)

        code, _ = self.run_command(
            ["install", "protocol"], interactive=True, answer=True
        )
        self.assertEqual(code, 0)
        self.assertIs(self.component.status().state, ComponentState.INSTALLED)

    def test_repeated_install_and_uninstall_are_idempotent_and_quiet(self):
        self.run_command(["-y", "install", "protocol"])
        code, events = self.run_command(["--json", "install", "protocol"])
        self.assertEqual(code, 0)
        self.assertEqual(events[-1]["action"], "unchanged")

        code, events = self.run_command(["--json", "-y", "uninstall", "protocol"])
        self.assertEqual(events[-1]["action"], "removed")
        code, events = self.run_command(["--json", "uninstall", "protocol"])
        self.assertEqual(code, 0)
        self.assertEqual(events[-1]["action"], "unchanged")

    def test_repair_of_stale_registration_requires_confirmation(self):
        self.run_command(["-y", "install", "protocol"])
        from goexport.components.platforms import windows

        self.registry.set_value(
            windows.SCHEME_KEY, windows.LAUNCHER_VALUE, '["C:\\\\gone.exe"]'
        )
        code, _ = self.run_command(["install", "protocol"])
        self.assertEqual(code, 1)
        code, events = self.run_command(["--json", "install", "protocol", "--yes"])
        self.assertEqual(code, 0)
        self.assertEqual(events[-1]["action"], "repaired")

    def test_unsupported_platform_is_an_error(self):
        self.component.backend = None
        code, events = self.run_command(["--json", "-y", "install", "protocol"])
        self.assertEqual(code, 1)
        self.assertIn("cannot register", events[-1]["message"])
        code, events = self.run_command(["--json", "status"])
        self.assertEqual(code, 0)
        self.assertEqual(events[-1]["components"][0]["state"], "unsupported")


class HandleUrlTests(unittest.TestCase):
    def args(self, url, yes=False, json_mode=False):
        args = cli.build_parser().parse_args(
            [
                *(["--json"] if json_mode else []),
                *(["-y"] if yes else []),
                "handle-url",
                url,
            ]
        )
        args.reporter = Reporter(json_mode, io.StringIO())
        return args

    def test_registered_command_shape_is_parsed(self):
        args = cli.build_parser().parse_args(
            ["handle-url", "--", "goexport://record?movie_id=1"]
        )
        self.assertEqual(args.url, "goexport://record?movie_id=1")
        self.assertTrue(args.pause_on_exit)

    def test_request_runs_the_existing_record_command(self):
        args = self.args(
            "goexport://record?movie_id=abc&format=mov&url=https://example.com/",
            yes=True,
        )
        record_func = MagicMock(return_value=0)
        with (
            patch.object(handle_url, "DependencyManager") as manager,
            patch("goexport.commands.record.entry", record_func),
            patch.object(handle_url.config, "PROTOCOL_OUTPUT_DIR", Path("exports")),
        ):
            self.assertEqual(handle_url.entry(args), 0)

        record_args = record_func.call_args.args[0]
        self.assertEqual(record_args.movie_id, "abc")
        self.assertEqual(record_args.format, "mov")
        self.assertEqual(record_args.url, "https://example.com/")
        self.assertEqual(record_args.output.parent, Path("exports"))
        self.assertTrue(record_args.output.name.startswith("abc-"))
        self.assertIs(record_args.reporter, args.reporter)
        self.assertTrue(record_args.yes)
        manager.return_value.bootstrap.assert_called_once_with(
            record_args, ("chromium", "chromedriver", "pepper_flash", "ffmpeg")
        )

    def test_request_needs_confirmation_before_anything_runs(self):
        args = self.args("goexport://record?movie_id=abc")
        with (
            patch.object(handle_url, "DependencyManager") as manager,
            patch("goexport.helpers.interactive_terminal", return_value=False),
        ):
            with self.assertRaises(ConfirmationDeclined):
                handle_url.entry(args)
        manager.assert_not_called()

    def test_declined_request_does_not_record(self):
        args = self.args("goexport://record?movie_id=abc")
        with (
            patch.object(handle_url, "DependencyManager") as manager,
            patch("goexport.helpers.interactive_terminal", return_value=True),
            patch("goexport.helpers.Confirm.ask", return_value=False),
            patch("goexport.helpers.Console"),
        ):
            with self.assertRaises(ConfirmationDeclined):
                handle_url.entry(args)
        manager.assert_not_called()

    def test_invalid_url_fails_through_cli_without_traceback(self):
        args = self.args("goexport://record?movie_id=1&output=/tmp/x", json_mode=True)
        stream = io.StringIO()
        with (
            patch.object(cli, "setup_logging"),
            patch.object(
                cli, "Reporter", lambda json_mode, stream=None: Reporter(json_mode, out)
            ),
        ):
            out = stream
            code = cli.run(args)
        self.assertEqual(code, 1)
        event = json.loads(stream.getvalue().splitlines()[-1])
        self.assertEqual(event["event"], "error")
        self.assertIn("Unsupported parameter", event["message"])

    def test_main_pauses_only_for_interactive_url_handling(self):
        args = self.args("goexport://record?movie_id=1")
        with (
            patch.object(cli, "build_parser") as parser,
            patch.object(cli, "run", return_value=1),
            patch.object(cli, "interactive_terminal", return_value=True),
            patch("builtins.input") as prompt,
        ):
            parser.return_value.parse_args.return_value = args
            self.assertEqual(cli.main(), 1)
            prompt.assert_called_once()
            args.json = True
            prompt.reset_mock()
            cli.main()
            prompt.assert_not_called()


class ComponentErrorTests(unittest.TestCase):
    def test_component_errors_are_reported_without_traceback(self):
        args = cli.build_parser().parse_args(["--json", "-y", "install", "protocol"])
        stream = io.StringIO()
        failing = MagicMock()
        failing.status.side_effect = ComponentError("boom")
        with (
            patch.object(commands, "get_component", return_value=failing),
            patch.object(cli, "setup_logging"),
            patch.object(
                cli, "Reporter", lambda json_mode, stream=None: Reporter(json_mode, out)
            ),
        ):
            out = stream
            self.assertEqual(cli.run(args), 1)
        self.assertEqual(json.loads(stream.getvalue())["message"], "boom")


if __name__ == "__main__":
    unittest.main()
