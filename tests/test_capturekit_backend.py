import tempfile
import threading
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import capturekit as ck

from goexport.services.recording_backends import capturekit as backend_module
from goexport.services.recording_backends.base import CaptureArtifacts
from goexport.services.recording_backends.capturekit import CaptureKitBackend

TITLE = "GoExport Recorder unique"


def window(handle=0x10, title=f"{TITLE} - Chromium", pid=200, rect=None):
    return ck.Window(
        handle=handle,
        title=title,
        class_name="Chrome_WidgetWin_1",
        pid=pid,
        process_name="chrome",
        rect=rect or ck.Rect(0, 0, 1920, 1080),
        is_visible=True,
        is_minimized=False,
    )


def capabilities(**overrides):
    supported = ck.Capability(ck.Support.SUPPORTED, "ok")
    values = dict(
        platform="windows",
        os_version="test",
        display_server=None,
        monitor_capture=supported,
        window_capture=supported,
        window_capture_borderless=supported,
        window_capture_minimized=supported,
        cursor_capture=supported,
        microphone_audio=supported,
        system_audio=supported,
        process_audio=supported,
        audio_session_enumeration=supported,
        recording=supported,
    )
    values.update(overrides)
    return ck.Capabilities(**values)


def unavailable(reason):
    return ck.Capability(ck.Support.UNAVAILABLE, reason)


class CaptureKitBackendTests(unittest.TestCase):
    def setUp(self):
        self.system = patch.object(backend_module.config, "SYSTEM", "Windows")
        self.system.start()
        self.addCleanup(self.system.stop)
        self.args = Namespace(
            resolution=(1280, 720),
            capturekit_audio="process",
            capturekit_encoder="auto",
        )
        self.reporter = Mock()

    def backend(self):
        return CaptureKitBackend(
            self.args, self.reporter, Path("bin/ffmpeg.exe"), TITLE
        )

    # -- availability --------------------------------------------------------
    def test_macos_is_rejected_with_obs_guidance(self):
        with patch.object(backend_module.config, "SYSTEM", "Darwin"):
            with self.assertRaisesRegex(RuntimeError, "--capture-backend obs"):
                self.backend().check_available(None)

    def test_odd_resolution_is_rejected_instead_of_resized(self):
        self.args.resolution = (1281, 720)
        with self.assertRaisesRegex(RuntimeError, "even output resolution"):
            self.backend().check_available(None)

    def test_linux_requires_and_uses_the_explicit_capture_display(self):
        backend = self.backend()
        with patch.object(backend_module.config, "SYSTEM", "Linux"):
            with self.assertRaisesRegex(RuntimeError, "X11 display"):
                backend.check_available(None)
            with patch.object(
                ck, "get_capabilities", return_value=capabilities()
            ) as caps:
                backend.check_available(":99")
        caps.assert_called_once_with(":99")
        self.assertEqual(backend.display, ":99")

    def test_windows_never_passes_an_inherited_x11_display(self):
        backend = self.backend()
        with patch.object(ck, "get_capabilities", return_value=capabilities()) as caps:
            backend.check_available(":0")
        caps.assert_called_once_with(None)

    def test_missing_process_audio_is_explicit_not_substituted(self):
        caps = capabilities(process_audio=unavailable("no PulseAudio server"))
        with patch.object(ck, "get_capabilities", return_value=caps):
            with self.assertRaisesRegex(
                RuntimeError, "(?s)no PulseAudio server.*audio system.*audio none"
            ):
                self.backend().check_available(None)

    def test_recording_capability_is_required(self):
        caps = capabilities(recording=unavailable("no FFmpeg"))
        with patch.object(ck, "get_capabilities", return_value=caps):
            with self.assertRaisesRegex(RuntimeError, "no FFmpeg"):
                self.backend().check_available(None)

    # -- window selection ----------------------------------------------------
    def test_unique_title_selects_window_and_binds_handle(self):
        target = window(handle=0x42)
        other = window(handle=0x43, title="GoExport Recorder another-session")
        with patch.object(ck, "list_windows", return_value=[other, target]):
            self.assertIs(self.backend()._find_window({100, 200}), target)

    def test_windows_of_other_sessions_are_ignored(self):
        ours = window(handle=0x42, pid=200)
        foreign = window(handle=0x43, pid=999)
        with patch.object(ck, "list_windows", return_value=[foreign, ours]):
            self.assertIs(self.backend()._find_window({100, 200}), ours)

    def test_window_lookup_waits_for_the_title_to_be_published(self):
        target = window()
        listing = Mock(side_effect=[[window(title="about:blank")], [target]])
        with (
            patch.object(ck, "list_windows", listing),
            patch.object(backend_module.time, "sleep") as sleep,
        ):
            self.assertIs(self.backend()._find_window(None), target)
        sleep.assert_called_once_with(backend_module.WINDOW_LOOKUP_POLL_SECONDS)

    def test_ambiguous_window_title_is_an_error(self):
        with patch.object(ck, "list_windows", return_value=[window(1), window(2)]):
            with self.assertRaisesRegex(RuntimeError, "2 windows"):
                self.backend()._find_window(None)

    def test_missing_window_times_out_with_title(self):
        clock = iter([0.0, 0.0, 100.0])
        with (
            patch.object(ck, "list_windows", return_value=[]),
            patch.object(backend_module.time, "monotonic", lambda: next(clock)),
            patch.object(backend_module.time, "sleep"),
        ):
            with self.assertRaisesRegex(RuntimeError, TITLE):
                self.backend()._find_window(None)

    def test_linux_enumerates_windows_on_the_owned_display(self):
        backend = self.backend()
        backend.display = ":99"
        with patch.object(ck, "list_windows", return_value=[window()]) as listing:
            backend._find_window(None)
        listing.assert_called_once_with(":99")

    # -- crop and resolution -------------------------------------------------
    def video_source(self, client, viewport, *, display=None, linux_display=None):
        backend = self.backend()
        backend.display = linux_display
        service = Mock(display=display)
        service.get_viewport_metrics.return_value = viewport
        with patch.object(backend, "_probe_client_size", return_value=client):
            return backend._video_source(service, Mock(), window(handle=0x42))

    def test_fullscreen_crop_is_top_left_of_the_client_area(self):
        source = self.video_source(
            (1920, 1080), {"width": 1920, "height": 1080, "devicePixelRatio": 1}
        )
        self.assertIsInstance(source, ck.WindowSource)
        self.assertEqual(source.handle, 0x42)
        self.assertTrue(source.client_area_only)
        self.assertFalse(source.include_cursor)
        self.assertEqual(source.region, ck.Rect(0, 0, 1280, 720))

    def test_browser_ui_above_viewport_is_excluded(self):
        source = self.video_source(
            (1280, 800), {"width": 1280, "height": 760, "devicePixelRatio": 1}
        )
        self.assertEqual(source.region, ck.Rect(0, 40, 1280, 720))

    def test_viewport_uses_physical_pixels(self):
        self.args.resolution = (2560, 1440)
        source = self.video_source(
            (2880, 1620), {"width": 1440, "height": 810, "devicePixelRatio": 2}
        )
        self.assertEqual(source.region, ck.Rect(0, 0, 2560, 1440))

    def test_viewport_smaller_than_requested_output_is_not_stretched(self):
        with self.assertRaisesRegex(RuntimeError, "does not fit"):
            self.video_source(
                (1024, 576), {"width": 1024, "height": 576, "devicePixelRatio": 1}
            )

    def test_linux_window_source_uses_owned_display(self):
        source = self.video_source(
            (1280, 720),
            {"width": 1280, "height": 720, "devicePixelRatio": 1},
            linux_display=":99",
        )
        self.assertEqual(source.display, ":99")

    def test_probe_measures_client_area_from_a_captured_frame(self):
        backend = self.backend()
        backend.display = ":99"
        capture = MagicMock()
        capture.__enter__.return_value.grab.return_value = SimpleNamespace(
            width=1536, height=976
        )
        with patch.object(ck, "ScreenCapture", return_value=capture) as factory:
            self.assertEqual(backend._probe_client_size(0x42), (1536, 976))
        source = factory.call_args.args[0]
        self.assertEqual((source.handle, source.client_area_only), (0x42, True))
        self.assertEqual(source.display, ":99")

    def test_xvfb_without_composite_falls_back_to_owned_display_region(self):
        backend = self.backend()
        backend.display = ":99"
        service = Mock(display=Mock())
        service.get_viewport_metrics.return_value = {
            "width": 1280,
            "height": 720,
            "devicePixelRatio": 1,
        }
        monitor = ck.Monitor("screen", 0, "screen", ck.Rect(0, 0, 1536, 976), True)
        target = window(rect=ck.Rect(10, 20, 1280, 760))
        with (
            patch.object(backend_module.config, "SYSTEM", "Linux"),
            patch.object(
                backend,
                "_probe_client_size",
                side_effect=ck.CapabilityUnavailableError("no Composite"),
            ),
            patch.object(ck, "list_monitors", return_value=[monitor]) as monitors,
        ):
            source = backend._video_source(service, Mock(), target)
        monitors.assert_called_with(":99")
        self.assertIsInstance(source, ck.MonitorSource)
        self.assertEqual(source.display, ":99")
        self.assertEqual(source.region, ck.Rect(10, 60, 1280, 720))

    def test_unowned_display_never_falls_back_to_screen_capture(self):
        backend = self.backend()
        backend.display = ":0"
        service = Mock(display=None)
        service.get_viewport_metrics.return_value = {"width": 1280, "height": 720}
        with (
            patch.object(backend_module.config, "SYSTEM", "Linux"),
            patch.object(
                backend,
                "_probe_client_size",
                side_effect=ck.CapabilityUnavailableError("no Composite"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "exclusively"):
                backend._video_source(service, Mock(), window())

    # -- audio ---------------------------------------------------------------
    def test_process_audio_follows_chromium_process_tree_without_microphone(self):
        sources = self.backend()._audio_sources(window(pid=200), Mock())
        self.assertEqual(len(sources), 1)
        self.assertIsInstance(sources[0], ck.ProcessAudioSource)
        self.assertEqual((sources[0].pid, sources[0].include_children), (200, True))

    def test_audio_modes_are_explicit(self):
        self.args.capturekit_audio = "system"
        system = self.backend()._audio_sources(window(), Mock())
        self.args.capturekit_audio = "none"
        silent = self.backend()._audio_sources(window(), Mock())
        self.assertIsInstance(system[0], ck.SystemAudioSource)
        self.assertEqual(silent, ())
        for source in (*system, *silent):
            self.assertNotIsInstance(source, ck.MicrophoneSource)

    def test_unknown_window_pid_uses_chromedriver_session(self):
        driver = SimpleNamespace(
            service=SimpleNamespace(process=SimpleNamespace(pid=7))
        )
        sources = self.backend()._audio_sources(window(pid=None), driver)
        self.assertEqual(sources[0].pid, 7)

    # -- configuration and lifecycle ---------------------------------------
    def prepared(self, directory):
        backend = self.backend()
        artifacts = CaptureArtifacts(
            Path(directory) / "out.video.mkv",
            Path(directory) / "a.wav",
            Path(directory),
        )
        with (
            patch.object(backend, "_session_pids", return_value=None),
            patch.object(backend, "_find_window", return_value=window()),
            patch.object(backend, "_video_source", return_value="video"),
            patch.object(ck, "Recorder") as recorder,
        ):
            backend.prepare(Mock(), Mock(), artifacts)
        return backend, recorder, artifacts

    def test_recording_config_matches_goexport_output(self):
        with tempfile.TemporaryDirectory() as directory:
            backend, recorder, artifacts = self.prepared(directory)
        video, audio, output, cfg = recorder.call_args.args
        self.assertEqual((video, output), ("video", artifacts.video))
        self.assertIsInstance(audio[0], ck.ProcessAudioSource)
        self.assertEqual(cfg.fps, backend_module.config.FPS)
        self.assertEqual(cfg.output_size, (1280, 720))
        self.assertIs(cfg.container, ck.Container.MKV)
        self.assertIs(cfg.on_target_lost, ck.TargetLostPolicy.STOP)
        self.assertEqual(cfg.encoder.encoder, "auto")
        self.assertEqual(cfg.encoder.ffmpeg_path, str(Path("bin/ffmpeg.exe")))
        # Lossless intermediate: FFmpegMuxer performs the only AAC encode.
        self.assertEqual(cfg.encoder.audio_codec, "pcm_s16le")

    def test_start_pauses_until_playback_begins(self):
        with tempfile.TemporaryDirectory() as directory:
            backend, recorder, _ = self.prepared(directory)
        rec = recorder.return_value
        backend.start()
        self.assertEqual([c[0] for c in rec.method_calls], ["start", "pause"])
        backend.before_playback()
        rec.resume.assert_called_once_with()

    def test_failure_between_start_and_pause_reports_recorder_error(self):
        with tempfile.TemporaryDirectory() as directory:
            backend, recorder, _ = self.prepared(directory)
        rec = recorder.return_value
        rec.pause.side_effect = ck.RecorderStateError(
            "cannot pause from state stopping"
        )
        rec.stop.return_value = SimpleNamespace(error=ck.WindowClosedError("closed"))
        with self.assertRaisesRegex(RuntimeError, "closed"):
            backend.start()

    def recording(self, directory, *, stopped_after=1, result_error=None):
        backend, recorder, artifacts = self.prepared(directory)
        artifacts.video.write_bytes(b"mkv")
        rec = recorder.return_value
        rec.wait.return_value = False
        rec.stats = SimpleNamespace(media_duration_s=1.5)
        stats = SimpleNamespace(media_duration_s=3.04, video=None, audio=())
        rec.stop.return_value = SimpleNamespace(error=result_error, stats=stats)
        stopped = Mock(spec=threading.Event)
        waits = iter([False] * stopped_after + [True])
        stopped.wait.side_effect = lambda _timeout: next(waits)
        stopped.is_set.return_value = True
        return backend, rec, stopped

    def test_capture_until_stopped_returns_muxed_result_and_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            backend, rec, stopped = self.recording(directory)
            result = backend.capture_until_stopped(
                threading.Event(), stopped, 3 * 10**9
            )
            self.assertTrue(result.audio_is_muxed)
            self.assertTrue(result.has_audio)
            self.assertIsNone(result.audio)
            self.assertEqual(result.owned_paths, (result.video,))
        rec.stop.assert_called_once_with(backend_module.STOP_TIMEOUT_SECONDS)
        values = [c.args[0] for c in self.reporter.progress.call_args_list]
        self.assertEqual(values[0], 5 + 50 * 79 / 100)
        self.assertTrue(all(5 <= value <= 84 for value in values))

    def test_lost_window_is_a_capture_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            backend, _, stopped = self.recording(
                directory, result_error=ck.WindowClosedError("window closed")
            )
            with self.assertRaisesRegex(RuntimeError, "window closed"):
                backend.capture_until_stopped(threading.Event(), stopped, 10**9)

    def test_recorder_ending_before_playback_stops_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            backend, rec, stopped = self.recording(directory, stopped_after=3)
            rec.wait.return_value = True
            stopped.is_set.return_value = False
            with self.assertRaisesRegex(RuntimeError, "before playback finished"):
                backend.capture_until_stopped(threading.Event(), stopped, 10**9)

    def test_encoder_failure_propagates(self):
        with tempfile.TemporaryDirectory() as directory:
            backend, rec, stopped = self.recording(directory)
            rec.stop.side_effect = ck.EncoderError("FFmpeg exited with an error")
            with self.assertRaises(ck.EncoderError):
                backend.capture_until_stopped(threading.Event(), stopped, 10**9)

    def test_close_stops_an_active_recorder_and_logs_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            backend, recorder, _ = self.prepared(directory)
        rec = recorder.return_value
        rec.state = ck.RecorderState.RECORDING
        rec.stop.side_effect = ck.EncoderError("broken pipe")
        with self.assertLogs(backend_module.logger, "WARNING"):
            backend.close()
        rec.stop.assert_called_once()

    def test_close_after_finished_recording_does_not_stop_again(self):
        with tempfile.TemporaryDirectory() as directory:
            backend, recorder, _ = self.prepared(directory)
        recorder.return_value.state = ck.RecorderState.STOPPED
        backend.close()
        recorder.return_value.stop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
