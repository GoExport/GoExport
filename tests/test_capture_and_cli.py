import os
import sys
import unittest
from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import Mock, patch

from goexport import config
from goexport.services.capture import (
    VideoSelector,
    audio_padding_samples,
    audio_trim_samples,
    cfr_index,
)


class CaptureTimelineTests(unittest.TestCase):
    def test_cfr_rounding_at_boundary(self):
        origin = 1_000_000_000
        self.assertEqual(cfr_index(origin + 20_833_333, origin, 24), 0)
        self.assertEqual(cfr_index(origin + 20_833_334, origin, 24), 1)

    def test_duplicate_nearest_and_missing_repeat(self):
        origin = 0
        selector = VideoSelector(24)
        self.assertEqual(selector.add(origin, b"first"), [])
        self.assertEqual(selector.add(42_000_000, b"late"), [b"first"])
        # Slot one is settled as late; skipping to slot three repeats it for slot two.
        self.assertEqual(selector.add(125_000_000, b"third"), [b"late", b"late"])

    def test_initial_audio_offset_sample_math(self):
        self.assertEqual(audio_padding_samples(500_000_000, 48_000), 24_000)
        self.assertEqual(audio_trim_samples(-250_000_000, 48_000), 12_000)

    def test_formats_do_not_advertise_gif(self):
        self.assertEqual(config.SUPPORTED_FORMATS, {"mp4", "mov", "mkv"})


class CliTests(unittest.TestCase):
    def test_parse_args_is_called_once(self):
        import goexport.cli as cli

        parser = Mock()
        parser.parse_args.return_value = Namespace(verbose=False, func=lambda _: 0)
        with (
            patch.object(cli, "build_parser", return_value=parser),
            patch.object(cli, "setup_logging"),
        ):
            self.assertEqual(cli.main(), 0)
        self.assertEqual(parser.parse_args.call_count, 1)

    def test_recording_page_title_is_unique_for_capture_target_lookup(self):
        from goexport.services.recorder import RecordingService

        args = Namespace(
            output="out",
            format="mp4",
            resolution=(1280, 720),
            swf_url="swf",
            is_wide=True,
            api_url="api",
            store_path="store",
            client_theme_path="theme",
            movie_id="movie",
            user_id="user",
        )
        first, second = RecordingService(args), RecordingService(args)
        self.assertNotEqual(first._capture_window_title, second._capture_window_title)
        self.assertEqual(
            first._build_replacements()["WINDOW_TITLE"], first._capture_window_title
        )


class BrowserCaptureTargetTests(unittest.TestCase):
    def test_linux_uses_x11_root_display_without_enumerating_windows(self):
        from goexport.services.browser import BrowserService

        scap = Mock()
        with (
            patch.object(config, "SYSTEM", "Linux"),
            patch.dict(sys.modules, {"scap": scap}),
        ):
            self.assertIsNone(BrowserService.get_capture_target(Mock()))

        scap.targets.assert_not_called()

    def test_non_linux_retains_title_based_window_selection(self):
        from goexport.services.browser import BrowserService

        expected = SimpleNamespace(kind="window", title="Recorder - Chromium")
        scap = Mock()
        scap.targets.return_value = [expected]
        driver = SimpleNamespace(title="Recorder")
        with (
            patch.object(config, "SYSTEM", "Windows"),
            patch.dict(sys.modules, {"scap": scap}),
        ):
            self.assertIs(BrowserService.get_capture_target(driver), expected)

    def test_linux_display_forces_x11_backend(self):
        from goexport.services.browser import BrowserService

        service = BrowserService(
            Mock(), Mock(), Mock(), "1", check_screen_resolution=False
        )
        display = Mock()
        with (
            patch.object(config, "SYSTEM", "Linux"),
            patch("goexport.services.browser.Display", return_value=display),
            patch.dict(os.environ, {"SCAP_BACKEND": "pipewire"}),
        ):
            service.start_display()
            self.assertEqual(os.environ["SCAP_BACKEND"], "x11")

        display.start.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
