import io
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from goexport.commands import export
from goexport.services.browser import BrowserService
from goexport.services.ffmpeg import FFmpegError, FFmpegMuxer, _PipeEncoder
from goexport.services.recorder import RecordingService
from goexport.services.renderer import Renderer
from goexport.services.timeline_builder import TimelineBuilder


class ResourceCleanupTests(unittest.TestCase):
    def test_recording_probes_scap_after_browser_activates_display(self):
        args = Namespace(output=Path("out"), format="mkv")
        recording = RecordingService(args)
        browser = Mock()
        browser.capture_display = ":99"
        scap = Mock()
        scap.is_supported.side_effect = lambda: os.environ.get("DISPLAY") == ":99"
        with (
            patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True),
            patch.object(recording, "_prepare_browser", return_value=(browser, Mock())),
            patch.object(
                recording, "_create_output_path", return_value=Path("out.mkv")
            ),
            patch.object(recording, "_record_playback"),
            patch.object(recording, "_finish_recording"),
            patch.object(recording, "_finish_browser_setup"),
            patch.dict(sys.modules, {"scap": scap}),
        ):
            # This models BrowserService.start_display selecting Xvfb :99 before
            # it returns control to RecordingService.run().
            browser_activation = recording._prepare_browser
            browser_activation.side_effect = lambda: (
                os.environ.__setitem__("DISPLAY", ":99") or (browser, Mock())
            )
            self.assertEqual(recording.run(), 0)
        scap.is_supported.assert_called_once()

    def test_linux_browser_stops_before_selenium_for_missing_dependencies(self):
        service = BrowserService(Path("chrome"), Mock(), Mock(), "1")
        with (
            patch("goexport.services.browser.config.SYSTEM", "Linux"),
            patch(
                "goexport.services.browser.find_linux_chromium_missing_dependencies",
                return_value=("libpci.so.3", "libasound.so.2"),
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "(?s)Chromium cannot start.*libpci.so.3.*libasound.so.2",
            ):
                service.validate_linux_dependencies()

    def test_non_linux_browser_skips_dependency_validation(self):
        service = BrowserService(Path("chrome"), Mock(), Mock(), "1")
        with (
            patch("goexport.services.browser.config.SYSTEM", "Windows"),
            patch(
                "goexport.services.browser.find_linux_chromium_missing_dependencies"
            ) as check,
        ):
            service.validate_linux_dependencies()
        check.assert_not_called()

    def test_browser_releases_display_when_quit_fails(self):
        service = BrowserService(Mock(), Mock(), Mock(), "1")
        service.driver = Mock()
        service.driver.quit.side_effect = RuntimeError("quit failed")
        service.display = Mock()
        display = service.display
        with self.assertRaisesRegex(RuntimeError, "quit failed"):
            service.close()
        display.stop.assert_called_once()

    def test_recording_setup_failure_closes_browser(self):
        recording = RecordingService(Namespace(url="url"))
        service = Mock()
        service.create_driver.return_value.get.side_effect = RuntimeError("navigation")
        with patch.object(recording, "_create_browser_service", return_value=service):
            with self.assertRaisesRegex(RuntimeError, "navigation"):
                recording._prepare_browser()
        service.close.assert_called_once()

    def test_capture_start_failure_is_not_hidden_by_join(self):
        recording = RecordingService(Namespace())
        capturer = Mock()
        capturer.start.side_effect = RuntimeError("capture start")
        with (
            patch.object(recording, "_create_capturer", return_value=capturer),
            patch("goexport.services.recorder.await_started"),
            patch.object(BrowserService, "get_capture_target"),
        ):
            with self.assertRaisesRegex(RuntimeError, "capture start"):
                recording._record_playback(Mock(), Path("video"), Path("audio"))
        capturer.stop.assert_called_once()

    def test_render_failure_closes_encoder(self):
        driver = Mock()
        driver.execute_script.return_value = 2
        driver.get_screenshot_as_png.side_effect = RuntimeError("screenshot")
        encoder = Mock()
        with self.assertRaisesRegex(RuntimeError, "screenshot"):
            Renderer(driver, encoder).render()
        encoder.close.assert_called_once()

    def test_export_uses_paths_and_closes_browser(self):
        args = Namespace(
            ugc_path="ugc",
            assets="assets",
            movie_xml=Path("movie.xml"),
            resolution=(1280, 720),
            url="url",
            swf_url="swf",
            is_wide=True,
            api_url="api",
            store_path="store",
            client_theme_path="theme",
            movie_id="movie",
            format="mp4",
            electron=True,
            no_flash_timeout=True,
            chrome_path=Path("chrome"),
            chromedriver_path=Path("chromedriver"),
            flash_plugin_path=Path("flash"),
            flash_plugin_version="1",
            ffmpeg_path=Path("ffmpeg"),
        )
        with (
            patch.object(export, "BrowserService", autospec=True) as browser,
            patch.object(export, "TimelineBuilder"),
            patch.object(export, "FFmpegVideoEncoder"),
            patch.object(export, "Renderer"),
            patch.object(export, "AudioProcessor") as audio,
            patch.object(export, "FFmpegMuxer") as muxer,
            patch.object(export, "await_started"),
        ):
            audio.return_value.process.return_value = Path("audio.wav")
            self.assertEqual(export.export_video(args), 0)
            muxer.return_value.mux.assert_called_once_with(
                video_file=Path("output.mkv"),
                audio_file=Path("audio.wav"),
                output_file=Path("final_output.mp4"),
            )
            browser.return_value.close.assert_called_once()
            self.assertEqual(browser.call_args.kwargs["electron"], True)
            export.await_started.assert_called_once_with(
                browser.return_value.create_driver.return_value,
                timeout_minutes=0,
            )


class EncodingTests(unittest.TestCase):
    def test_partial_pipe_writes_preserve_all_bytes(self):
        received = bytearray()

        def write(data):
            received.extend(data[:2])
            return min(2, len(data))

        process = Mock()
        process.stdin.write.side_effect = write
        process.returncode = 0
        process.stdin.closed = False
        with patch("goexport.services.ffmpeg.subprocess.Popen", return_value=process):
            encoder = _PipeEncoder(["ffmpeg"])
            encoder.write_frame(b"abcdefg")
            encoder.close()
            encoder.close()
        self.assertEqual(received, b"abcdefg")

    def test_failed_encoder_closes_stderr_and_reports_diagnostics(self):
        process = SimpleNamespace(stdin=io.BytesIO(), returncode=1, wait=Mock())
        with patch("goexport.services.ffmpeg.subprocess.Popen", return_value=process):
            encoder = _PipeEncoder(["ffmpeg"])
        encoder._stderr.write(b"bad encoder")
        with self.assertRaisesRegex(FFmpegError, "bad encoder"):
            encoder.close()
        self.assertTrue(encoder._stderr.closed)

    def test_failed_mux_preserves_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            video, audio = Path(temp) / "video.mkv", Path(temp) / "audio.wav"
            video.touch()
            audio.touch()
            muxer = FFmpegMuxer(Path("ffmpeg"))
            with patch.object(muxer, "_run", side_effect=FFmpegError("mux")):
                with self.assertRaises(FFmpegError):
                    muxer.mux(video, audio, Path(temp) / "out.mp4")
            self.assertTrue(video.exists())
            self.assertTrue(audio.exists())

    def test_sound_requires_asset_id(self):
        with tempfile.TemporaryDirectory() as temp:
            xml = Path(temp) / "movie.xml"
            xml.write_text(
                "<film><sound><start>1</start><stop>24</stop></sound></film>"
            )
            with self.assertRaisesRegex(ValueError, "sfile"):
                TimelineBuilder(xml).build()

    def test_audio_alignment_and_stop_buffer_trim(self):
        recording = RecordingService(Namespace())
        recording._audio_aligned = False
        recording._sample_bytes = 2
        frame = SimpleNamespace(data=Mock(), channels=1, rate=4, sample_count=4)
        frame.data.tobytes.return_value = b"abcdefgh"
        encoder = Mock()
        recording._write_audio(frame, 500_000_000, 0, encoder, 1_000_000_000)
        self.assertEqual(
            [call.args[0] for call in encoder.write_frame.call_args_list],
            [b"\0" * 4, b"abcd"],
        )
