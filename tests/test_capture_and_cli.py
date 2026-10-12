import io
import os
import unittest
from argparse import Namespace
from contextlib import redirect_stderr
from unittest.mock import Mock, patch

from goexport import config


class OutputFormatTests(unittest.TestCase):
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
            additional_flashvars={},
            replacement=[],
        )
        first, second = RecordingService(args), RecordingService(args)
        self.assertNotEqual(first._capture_window_title, second._capture_window_title)
        self.assertEqual(
            first._build_replacements()["WINDOW_TITLE"], first._capture_window_title
        )
        flashvars = first._build_replacements()["FLASHVARS"]
        self.assertIn("movieId=movie", flashvars)

    def test_record_backend_defaults_to_capturekit_and_accepts_obs(self):
        import goexport.cli as cli

        parser = cli.build_parser()
        defaults = parser.parse_args(["record", "-id", "movie"])
        selected = parser.parse_args(
            ["record", "-id", "movie", "--capture-backend", "obs"]
        )
        self.assertEqual(config.RECORDING_BACKEND, "capturekit")
        self.assertEqual(defaults.capture_backend, "capturekit")
        self.assertEqual(defaults.capturekit_audio, "process")
        self.assertEqual(defaults.capturekit_encoder, "auto")
        self.assertEqual(selected.capture_backend, "obs")

    def test_record_rejects_pyscap_with_migration_guidance(self):
        import goexport.cli as cli

        parser = cli.build_parser()
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit):
            parser.parse_args(["record", "-id", "m", "--capture-backend", "pyscap"])
        self.assertIn("--capture-backend capturekit", stderr.getvalue())

    def test_record_audio_mode_never_offers_microphone(self):
        import goexport.cli as cli

        parser = cli.build_parser()
        for mode in ("process", "system", "none"):
            args = parser.parse_args(["record", "-id", "m", "--capturekit-audio", mode])
            self.assertEqual(args.capturekit_audio, mode)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(
                ["record", "-id", "m", "--capturekit-audio", "microphone"]
            )

    def test_record_accepts_force_obs_profile(self):
        import goexport.cli as cli

        parser = cli.build_parser()

        defaults = parser.parse_args(["record", "-id", "movie"])
        forced = parser.parse_args(["record", "-id", "movie", "--obs-force-profile"])

        self.assertFalse(defaults.obs_force_profile)
        self.assertTrue(forced.obs_force_profile)


class BrowserCaptureTargetTests(unittest.TestCase):
    @staticmethod
    def _service():
        from goexport.services.browser import BrowserService

        return BrowserService(
            Mock(), Mock(), Mock(), "1", False, width=1280, height=720
        )

    def test_viewport_metrics_report_css_size_and_pixel_ratio(self):
        driver = Mock()
        driver.execute_script.return_value = {
            "width": 1280,
            "height": 720,
            "devicePixelRatio": 1,
        }
        self.assertEqual(
            self._service().get_viewport_metrics(driver),
            {"width": 1280, "height": 720, "devicePixelRatio": 1},
        )
        script = driver.execute_script.call_args.args[0]
        self.assertIn("window.innerWidth", script)
        self.assertIn("window.devicePixelRatio", script)

    def test_virtual_display_includes_browser_frame_margin(self):
        service = self._service()
        with patch("goexport.services.browser.LinuxDisplay") as display:
            with patch.object(config, "SYSTEM", "Linux"):
                display.return_value.start.return_value = ":99"
                service.start_display()
                service.stop_display()
        display.assert_called_once_with(size=(1536, 976), color_depth=24)
        display.return_value.stop.assert_called_once()

    def test_obs_linux_browser_uses_existing_display_visible_to_obs(self):
        from goexport.services.browser import BrowserService

        service = BrowserService(Mock(), Mock(), Mock(), "1", use_virtual_display=False)
        with (
            patch.object(config, "SYSTEM", "Linux"),
            patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True),
            patch("goexport.services.browser.LinuxDisplay") as display,
        ):
            service.start_display()
            self.assertEqual(service.capture_display, ":0")
        display.assert_not_called()

    def test_virtual_display_is_the_capture_display_when_inherited_differs(self):
        service = self._service()
        with (
            patch.object(config, "SYSTEM", "Linux"),
            patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True),
            patch("goexport.services.browser.LinuxDisplay") as display,
        ):
            display.return_value.start.return_value = ":99"
            display.return_value.capture_display = ":99"
            service.start_display()
            self.assertEqual(service.capture_display, ":99")

    def test_inherited_display_remains_capture_display_without_xvfb(self):
        from goexport.services.display import LinuxDisplay

        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True):
            display = LinuxDisplay((1280, 720))
            self.assertEqual(display.capture_display, ":0")

    def test_xvfb_window_is_grown_to_requested_viewport(self):
        service = self._service()
        service.display = Mock()
        driver = Mock()
        driver.execute_script.side_effect = [
            {"width": 1050, "height": 700},
            {"width": 1280, "height": 720},
        ]
        driver.get_window_rect.return_value = {"width": 1280, "height": 720}

        service.enter_fullscreen(driver)

        driver.set_window_rect.assert_any_call(x=0, y=0, width=1510, height=740)
        driver.fullscreen_window.assert_not_called()


class FlashPermissionTests(unittest.TestCase):
    def test_enable_flash_targets_chromium_plugins_permission(self):
        from goexport.services.browser import (
            FLASH_PERMISSION_SCRIPT,
            BrowserService,
        )

        driver = Mock()
        driver.current_url = "http://localhost:4343/player"
        driver.execute_script.return_value = {"status": "changed"}

        service = BrowserService.__new__(BrowserService)
        service.electron = False
        service.enable_flash(driver)

        self.assertIn("element.category === 'plugins'", FLASH_PERMISSION_SCRIPT)
        self.assertIn(
            "shadowRoot.querySelector('#permission')", FLASH_PERMISSION_SCRIPT
        )
        self.assertIn("select.disabled", FLASH_PERMISSION_SCRIPT)
        self.assertIn('option[value="allow"]', FLASH_PERMISSION_SCRIPT)
        driver.execute_script.assert_called_once_with(FLASH_PERMISSION_SCRIPT)
        self.assertEqual(
            driver.get.call_args_list[0].args[0],
            "chrome://settings/content/siteDetails?site=http%3A//localhost%3A4343/player",
        )
        self.assertEqual(driver.get.call_args_list[1].args[0], driver.current_url)

    def test_enable_flash_does_not_navigate_away_after_permission_failure(self):
        from goexport.services.browser import BrowserService

        driver = Mock()
        driver.current_url = "http://localhost:4343/player"
        driver.execute_script.return_value = {"status": "disabled"}

        with self.assertRaisesRegex(
            RuntimeError, "Flash permission control is disabled"
        ):
            service = BrowserService.__new__(BrowserService)
            service.electron = False
            service.enable_flash(driver)

        self.assertEqual(driver.get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
