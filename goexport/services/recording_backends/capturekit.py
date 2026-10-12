"""CaptureKit recording backend.

CaptureKit captures the Selenium-controlled Chromium window exclusively
(Windows Graphics Capture on Windows, XComposite on Linux X11/Xvfb) together
with the browser's own audio, and encodes both into one synchronized MKV.
The video is encoded exactly once here; GoExport's ``FFmpegMuxer`` then copies
it into the requested container and encodes the PCM audio to AAC.

Timeline: ``start()`` performs the slow setup (encoder validation, native
session start) and immediately pauses the recorder. ``before_playback()``
resumes it right before ``player.play()``, so CaptureKit's pause-aware
timeline excludes the setup pre-roll without any trimming or re-encoding.
"""

from __future__ import annotations

import logging
import time

from goexport import config
from goexport.services.recording_backends.base import (
    CaptureArtifacts,
    CaptureResult,
    report_recording_progress,
)

logger = logging.getLogger(__name__)

AUDIO_MODES = ("process", "system", "none")
WINDOW_LOOKUP_TIMEOUT_SECONDS = 10.0
WINDOW_LOOKUP_POLL_SECONDS = 0.1
PROBE_TIMEOUT_SECONDS = 5.0
STOP_TIMEOUT_SECONDS = 120.0
PROGRESS_POLL_SECONDS = 0.1
# Constant-quality value (CRF for libx264, CQ/QP for hardware encoders).
VIDEO_QUALITY = 18
# Lossless intermediate audio: FFmpegMuxer performs the only AAC encode.
INTERMEDIATE_AUDIO_CODEC = "pcm_s16le"


def _capturekit():
    import capturekit

    return capturekit


class CaptureKitBackend:
    def __init__(self, args, reporter, ffmpeg_path, window_title, **_kwargs):
        self.args = args
        self.reporter = reporter
        self.ffmpeg_path = ffmpeg_path
        self.window_title = window_title
        self.audio_mode = getattr(args, "capturekit_audio", config.CAPTUREKIT_AUDIO)
        self.encoder = getattr(args, "capturekit_encoder", config.CAPTUREKIT_ENCODER)
        self.display = None
        self.capabilities = None
        self.artifacts = None
        self.window = None
        self.video_source = None
        self.audio_sources = ()
        self.recorder = None
        self.result = None

    # -- availability ----------------------------------------------------
    def check_available(self, display=None):
        if config.SYSTEM not in {"Windows", "Linux"}:
            raise RuntimeError(
                f"The CaptureKit backend does not support {config.SYSTEM}; it "
                "supports Windows 10/11 and Linux X11/Xvfb. Use "
                "--capture-backend obs on this system."
            )
        if self.audio_mode not in AUDIO_MODES:
            raise ValueError(
                f"Unsupported CaptureKit audio mode {self.audio_mode!r}; "
                f"choose one of {', '.join(AUDIO_MODES)}."
            )
        width, height = self.args.resolution
        if width % 2 or height % 2:
            raise RuntimeError(
                f"The CaptureKit backend requires an even output resolution for "
                f"H.264 4:2:0 encoding; got {width}x{height}."
            )
        if config.SYSTEM == "Linux":
            if not display:
                raise RuntimeError(
                    "The CaptureKit backend requires an X11 display on Linux. "
                    "Install Xvfb so GoExport can create a private display."
                )
            self.display = display

        caps = _capturekit().get_capabilities(self.display)
        self.capabilities = caps
        logger.debug("CaptureKit capabilities:\n%s", caps.summary())
        if not caps.recording:
            raise RuntimeError(
                f"CaptureKit recording is unavailable: {caps.recording.reason}"
            )
        if not caps.window_capture and not caps.monitor_capture:
            raise RuntimeError(
                "CaptureKit cannot capture video on "
                f"{self.display or 'this desktop'}: {caps.window_capture.reason}"
            )
        if self.audio_mode == "process" and not caps.process_audio:
            raise RuntimeError(
                "CaptureKit cannot capture Chromium's application audio here: "
                f"{caps.process_audio.reason}. Use --capturekit-audio system to "
                "record everything played on the default output device, or "
                "--capturekit-audio none to record without audio."
            )
        if self.audio_mode == "system" and not caps.system_audio:
            raise RuntimeError(
                "CaptureKit cannot capture system audio here: "
                f"{caps.system_audio.reason}. Use --capturekit-audio none to "
                "record without audio."
            )

    # -- preparation -----------------------------------------------------
    def prepare(self, service, driver, artifacts: CaptureArtifacts):
        ck = _capturekit()
        self.artifacts = artifacts
        session_pids = self._session_pids(driver)
        self.window = self._find_window(session_pids)
        self.video_source = self._video_source(service, driver, self.window)
        self.audio_sources = self._audio_sources(self.window, driver)
        width, height = self.args.resolution
        self.recorder = ck.Recorder(
            self.video_source,
            self.audio_sources,
            artifacts.video,
            ck.RecordingConfig(
                fps=config.FPS,
                output_size=(width, height),
                container=ck.Container.MKV,
                encoder=ck.EncoderConfig(
                    encoder=self.encoder,
                    quality=VIDEO_QUALITY,
                    audio_codec=INTERMEDIATE_AUDIO_CODEC,
                    ffmpeg_path=str(self.ffmpeg_path),
                ),
                # The intermediate path belongs to this export; an older
                # failed attempt may have retained a diagnostic copy there.
                overwrite=True,
                on_target_lost=ck.TargetLostPolicy.STOP,
            ),
        )

    @staticmethod
    def _session_pids(driver):
        """PIDs of this Selenium session (chromedriver and its descendants)."""
        process = getattr(getattr(driver, "service", None), "process", None)
        pid = getattr(process, "pid", None)
        if not isinstance(pid, int):
            return None
        import psutil

        try:
            root = psutil.Process(pid)
            return {pid, *(child.pid for child in root.children(recursive=True))}
        except psutil.Error:
            logger.debug("Could not inspect chromedriver process %s", pid)
            return None

    def _find_window(self, session_pids):
        """Find the uniquely titled Chromium window and bind it by handle.

        Only the lookup uses the title; capture uses the native handle, so
        later title, fullscreen or size changes cannot redirect the capture.
        """
        ck = _capturekit()
        deadline = time.monotonic() + WINDOW_LOOKUP_TIMEOUT_SECONDS
        while True:
            matches = [
                window
                for window in ck.list_windows(self.display)
                if self.window_title in window.title
            ]
            if session_pids is not None:
                # A window whose owner is unknown is kept: its unique title
                # still identifies it. Known foreign owners are rejected.
                foreign = [
                    w
                    for w in matches
                    if w.pid is not None and w.pid not in session_pids
                ]
                if foreign:
                    logger.warning(
                        "Ignoring %d window(s) titled %r that do not belong to "
                        "this Selenium session.",
                        len(foreign),
                        self.window_title,
                    )
                matches = [w for w in matches if w not in foreign]
            if len(matches) == 1:
                window = matches[0]
                logger.info(
                    "Capturing Chromium window %#x (pid %s) on %s.",
                    window.handle,
                    window.pid,
                    self.display or "the Windows desktop",
                )
                return window
            if len(matches) > 1:
                raise RuntimeError(
                    "Could not uniquely identify the Selenium window for capture; "
                    f"{len(matches)} windows are titled {self.window_title!r}."
                )
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "Could not find the Selenium Chromium window titled "
                    f"{self.window_title!r} on {self.display or 'the desktop'}."
                )
            time.sleep(WINDOW_LOOKUP_POLL_SECONDS)

    def _video_source(self, service, driver, window):
        ck = _capturekit()
        viewport = service.get_viewport_metrics(driver)
        try:
            client_size = self._probe_client_size(window.handle)
        except ck.CapabilityUnavailableError as error:
            if config.SYSTEM == "Linux" and service.display is not None:
                return self._owned_xvfb_monitor_source(window, viewport, error)
            raise RuntimeError(
                f"CaptureKit cannot capture the Chromium window exclusively: {error}"
            ) from error
        region = self._viewport_region(client_size, viewport)
        logger.info(
            "Chromium client area %dx%d; recording viewport region %s.",
            *client_size,
            region,
        )
        return ck.WindowSource(
            window.handle,
            region=region,
            client_area_only=True,
            include_cursor=False,
            border=False,
            display=self.display,
        )

    def _probe_client_size(self, handle):
        """Physical client-area size, measured from a real captured frame."""
        ck = _capturekit()
        source = ck.WindowSource(handle, client_area_only=True, display=self.display)
        with ck.ScreenCapture(source) as capture:
            frame = capture.grab(PROBE_TIMEOUT_SECONDS)
        return frame.width, frame.height

    def _viewport_region(self, client_size, viewport):
        """Window-relative crop of the requested output inside the page viewport.

        Physical viewport pixels are CSS pixels times devicePixelRatio. Browser
        UI is above the page and any frame is symmetric, so the viewport sits
        at the bottom centre of the client area. In fullscreen/kiosk mode (the
        recording default) the viewport is the entire client area.
        """
        ck = _capturekit()
        width, height = self.args.resolution
        client_width, client_height = client_size
        ratio = float(viewport.get("devicePixelRatio") or 1)
        view_width = round(int(viewport["width"]) * ratio)
        view_height = round(int(viewport["height"]) * ratio)
        side = max(0, (client_width - view_width) // 2)
        top = max(0, client_height - view_height - side)
        if (
            width > view_width
            or height > view_height
            or side + width > client_width
            or top + height > client_height
        ):
            raise RuntimeError(
                f"The requested {width}x{height} recording does not fit in "
                f"Chromium's {view_width}x{view_height} viewport (client area "
                f"{client_width}x{client_height})."
            )
        if (view_width, view_height) != (client_width, client_height):
            logger.warning(
                "Chromium's viewport (%dx%d) does not fill its client area "
                "(%dx%d); assuming browser UI above the page.",
                view_width,
                view_height,
                client_width,
                client_height,
            )
        return ck.Rect(side, top, width, height)

    def _owned_xvfb_monitor_source(self, window, viewport, error):
        """Controlled fallback when XComposite is unavailable on Xvfb.

        Only GoExport's private Xvfb display is eligible: it contains nothing
        but this Chromium window, so the cropped display region is the movie.
        """
        ck = _capturekit()
        monitor = (
            next(
                (m for m in ck.list_monitors(self.display) if m.is_primary),
                None,
            )
            or ck.list_monitors(self.display)[0]
        )
        local = self._viewport_region((window.rect.width, window.rect.height), viewport)
        region = local.translate(
            window.rect.x - monitor.rect.x, window.rect.y - monitor.rect.y
        )
        logger.warning(
            "Exclusive window capture is unavailable on GoExport's private Xvfb "
            "display %s (%s); recording region %s of that display instead.",
            self.display,
            error,
            region,
        )
        return ck.MonitorSource(
            monitor, region=region, include_cursor=False, display=self.display
        )

    def _audio_sources(self, window, driver):
        ck = _capturekit()
        if self.audio_mode == "none":
            logger.info("CaptureKit audio capture is disabled; recording silent video.")
            return ()
        if self.audio_mode == "system":
            logger.warning(
                "Recording all audio played on the default output device "
                "(--capturekit-audio system); other applications will be audible."
            )
            return (ck.SystemAudioSource(name="system"),)
        pid = window.pid
        if pid is None:
            pid = getattr(getattr(driver.service, "process", None), "pid", None)
        if pid is None:
            raise RuntimeError(
                "Cannot identify Chromium's process for application audio capture."
            )
        return (ck.ProcessAudioSource(pid, include_children=True, name="chromium"),)

    # -- recording -------------------------------------------------------
    def start(self):
        if self.recorder is None:
            raise RuntimeError("CaptureKit backend was not prepared")
        self.recorder.start()
        try:
            self.recorder.pause()
        except _capturekit().RecorderStateError as error:
            # The recorder stopped itself between start and pause. stop()
            # raises a fatal cause; a lost target is reported in the result.
            result = self.recorder.stop(STOP_TIMEOUT_SECONDS)
            raise RuntimeError(
                f"CaptureKit stopped while starting: {result.error or error}"
            ) from (result.error or error)

    def before_playback(self):
        self.recorder.resume()

    def capture_until_stopped(self, started, stopped, total_duration_ns):
        recorder = self.recorder
        if recorder is None or self.artifacts is None:
            raise RuntimeError("CaptureKit backend was not prepared")
        logger.debug(
            "player.play() returned at media time %.1f ms",
            recorder.stats.media_duration_s * 1000,
        )
        while not stopped.wait(PROGRESS_POLL_SECONDS):
            if recorder.wait(0):
                break
            report_recording_progress(
                self.reporter,
                int(recorder.stats.media_duration_s * 1_000_000_000),
                total_duration_ns,
            )
        ended_early = not stopped.is_set()
        result = recorder.stop(STOP_TIMEOUT_SECONDS)
        if result.error is not None:
            raise RuntimeError(
                f"CaptureKit capture failed: {result.error}"
            ) from result.error
        if ended_early:
            raise RuntimeError("CaptureKit stopped recording before playback finished.")
        self._log_stats(result.stats, total_duration_ns)
        if not self.artifacts.video.is_file():
            raise RuntimeError(
                f"CaptureKit did not produce a recording at {self.artifacts.video}"
            )
        report_recording_progress(self.reporter, total_duration_ns, total_duration_ns)
        self.result = CaptureResult(
            self.artifacts.video,
            None,
            audio_is_muxed=True,
            owned_paths=(self.artifacts.video,),
            has_audio=bool(self.audio_sources),
        )
        return self.result

    @staticmethod
    def _log_stats(stats, total_duration_ns):
        expected = total_duration_ns / 1_000_000_000
        logger.info(
            "CaptureKit recorded %.3fs for a %.3fs movie (%+.0f ms).",
            stats.media_duration_s,
            expected,
            (stats.media_duration_s - expected) * 1000,
        )
        video = stats.video
        if video is not None:
            logger.info(
                "CaptureKit video: %s via %s, %d frames (%d new, %d repeated, "
                "%d dropped, %d late).",
                "x".join(map(str, video.output_size)),
                video.encoder,
                video.slots,
                video.frames_new,
                video.frames_duplicated,
                video.frames_dropped,
                video.frames_late,
            )
            if video.frames_dropped or video.frames_late:
                logger.warning(
                    "CaptureKit could not keep up with %d of %d frames; consider "
                    "a hardware encoder or a lower resolution.",
                    video.frames_dropped + video.frames_late,
                    video.slots,
                )
        for track in stats.audio:
            logger.info(
                "CaptureKit audio %r from %s: %.3fs, %.3fs silence inserted, "
                "%.3fs trimmed, %d discontinuities.",
                track.name,
                track.device,
                track.duration_s,
                track.silence_inserted_s,
                track.trimmed_s,
                track.discontinuities,
            )

    def stop(self):
        recorder = self.recorder
        if recorder is None:
            return self.result
        state = _capturekit().RecorderState
        if recorder.state not in (state.IDLE, state.STOPPED, state.FAILED):
            recorder.stop(STOP_TIMEOUT_SECONDS)
        return self.result

    def close(self):
        try:
            self.stop()
        except Exception:
            logger.warning(
                "Could not stop CaptureKit recording during cleanup", exc_info=True
            )
