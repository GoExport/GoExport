import io
import json
import logging
import unittest
from argparse import Namespace
from unittest.mock import Mock, patch

from goexport import cli
from goexport.commands import doctor
from goexport.reporting import Reporter
from goexport.services.recorder import recording_progress
from goexport.services.renderer import Renderer


class ReporterTests(unittest.TestCase):
    def test_json_progress_is_valid_deduplicated_and_clamped(self):
        output = io.StringIO()
        reporter = Reporter(json_mode=True, stream=output)

        reporter.progress(-2, "recording")
        reporter.progress(0, "recording")
        reporter.progress(42.5, "recording")
        reporter.progress(42.5, "recording")
        reporter.progress(43.0, "recording")
        reporter.progress(101, "recording")

        events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(
            events,
            [
                {"event": "progress", "progress": 0.0, "stage": "recording"},
                {"event": "progress", "progress": 42.5, "stage": "recording"},
                {"event": "progress", "progress": 99.0, "stage": "recording"},
            ],
        )

    def test_normal_progress_uses_info_logging_without_json(self):
        reporter = Reporter()
        with self.assertLogs("goexport.progress", logging.INFO) as logs:
            reporter.progress(42.5, "recording")
        self.assertIn("Recording: 42.50%", logs.output[0])

    def test_complete_is_the_only_success_event_with_100(self):
        output = io.StringIO()
        reporter = Reporter(json_mode=True, stream=output)
        reporter.progress(99, "finalizing")
        reporter.complete("movie.mp4")

        events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(events[-1]["event"], "complete")
        self.assertEqual(events[-1]["progress"], 100)
        self.assertTrue(all(event["progress"] < 100 for event in events[:-1]))

    def test_recording_timeline_progress_is_clamped(self):
        self.assertEqual(recording_progress(50, 100, 1000), 0)
        self.assertEqual(recording_progress(600, 100, 1000), 50)
        self.assertEqual(recording_progress(1200, 100, 1000), 100)

    def test_renderer_uses_progress_callback_contract(self):
        driver = Mock()
        driver.execute_script.side_effect = [None, 2, None, None]
        encoder = Mock()
        progress = Mock()

        Renderer(driver, encoder, progress_callback=progress).render()

        self.assertEqual([call.args[0] for call in progress.call_args_list], [50, 100])
        encoder.close.assert_called_once_with()


class JsonCliTests(unittest.TestCase):
    def _run(self, func):
        output = io.StringIO()
        args = Namespace(verbose=False, json=True, func=func)
        parser = Mock()
        parser.parse_args.return_value = args
        with (
            patch.object(cli, "build_parser", return_value=parser),
            patch.object(cli, "setup_logging"),
            patch("sys.stdout", output),
        ):
            code = cli.main()
        return code, [json.loads(line) for line in output.getvalue().splitlines()]

    def test_cli_accepts_global_json_option(self):
        args = cli.build_parser().parse_args(["--json", "doctor"])
        self.assertTrue(args.json)

    def test_json_mode_keeps_plain_output_out_of_stdout(self):
        def command(args):
            print("incidental output")
            args.reporter.progress(12, "rendering")
            return 0

        code, events = self._run(command)
        self.assertEqual(code, 0)
        self.assertEqual(
            events, [{"event": "progress", "progress": 12.0, "stage": "rendering"}]
        )

    def test_failure_is_json_and_retains_nonzero_status(self):
        def command(_):
            raise RuntimeError("broken")

        code, events = self._run(command)
        self.assertEqual(code, 1)
        self.assertEqual(events, [{"event": "error", "message": "broken", "code": 1}])

    def test_keyboard_interrupt_is_json_with_130_status(self):
        def command(_):
            raise KeyboardInterrupt

        code, events = self._run(command)
        self.assertEqual(code, 130)
        self.assertEqual(events[0]["event"], "error")
        self.assertEqual(events[0]["code"], 130)

    def test_doctor_produces_structured_result(self):
        output = io.StringIO()
        args = Namespace(reporter=Reporter(json_mode=True, stream=output))
        checks = [doctor.Check("Python", "ok", "Python 3.13")]
        with patch.object(doctor, "run_checks", return_value=checks):
            self.assertEqual(doctor.entry(args), 0)

        event = json.loads(output.getvalue())
        self.assertEqual(event["event"], "result")
        self.assertEqual(event["command"], "doctor")
        self.assertTrue(event["ok"])
        self.assertEqual(event["checks"][0]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
