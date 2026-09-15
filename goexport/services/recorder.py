import argparse
import logging
import threading
import uuid
from pathlib import Path

from goexport import config
from goexport.helpers import resolve_output_path
from goexport.services.browser import BrowserService
from goexport.services.capture import (
    VideoSelector,
    audio_padding_samples,
    audio_trim_samples,
    create_capturer,
    timestamp_ns,
)
from goexport.services.ffmpeg import (
    FFmpegMuxer,
    FFmpegRawAudioEncoder,
    FFmpegRawVideoEncoder,
)
from goexport.services.flash import await_player_ready, await_started, await_stopped

logger = logging.getLogger(__name__)
_AUDIO_FORMATS = {
    "int8": ("s8", 1),
    "int16": ("s16le", 2),
    "int32": ("s32le", 4),
    "int64": ("s64le", 8),
    "uint8": ("u8", 1),
    "uint16": ("u16le", 2),
    "uint32": ("u32le", 4),
    "uint64": ("u64le", 8),
    "float32": ("f32le", 4),
    "float64": ("f64le", 8),
}


class RecordingService:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        # PyScap identifies browser windows by title. A per-run title prevents
        # stale Chromium windows from matching this recording's capture target.
        self._capture_window_title = f"GoExport Recorder {uuid.uuid4().hex}"

    def _create_output_path(self):
        return resolve_output_path(Path(self.args.output), self.args.format)

    def _create_capturer(self, target, crop_area=None):
        return create_capturer(target, crop_area)

    def _capture_streams(self, capturer, video_path, audio_path, started, stopped):
        import scap

        video = audio = None
        selector = VideoSelector(config.FPS)
        video_origin = audio_origin = None
        pending = []
        boundary = None
        self._audio_aligned = False
        try:
            while True:
                frame = capturer.next_frame()
                # PyScap exposes no API to make a browser play() marker in its clock.
                # Discard frames dequeued before play returns; see README limitation.
                if not started.is_set():
                    continue
                now = timestamp_ns(frame.timestamp)
                if stopped.is_set() and boundary is None:
                    boundary = now
                if boundary is not None and now > boundary:
                    break
                if isinstance(frame, scap.VideoFrameInfo):
                    if frame.format not in {"bgra", "bgr0"}:
                        raise RuntimeError(
                            f"unsupported scap video format: {frame.format}"
                        )
                    if video is None:
                        video = FFmpegRawVideoEncoder(
                            config.FFMPEG_PATH,
                            video_path,
                            frame.width,
                            frame.height,
                            *self.args.resolution,
                            config.FPS,
                        )
                    if video_origin is None:
                        video_origin = now
                    for data in selector.add(now, frame.data.tobytes()):
                        video.write_frame(data)
                    for item, stamp in pending:
                        self._write_audio(item, stamp, video_origin, audio, boundary)
                    pending.clear()
                elif isinstance(frame, scap.AudioFrameInfo):
                    if frame.planar:
                        raise RuntimeError("Planar scap audio is not supported")
                    spec = _AUDIO_FORMATS.get(frame.format)
                    if spec is None:
                        raise RuntimeError(
                            f"unsupported scap audio format: {frame.format}"
                        )
                    if audio is None:
                        audio = FFmpegRawAudioEncoder(
                            config.FFMPEG_PATH,
                            audio_path,
                            frame.channels,
                            frame.rate,
                            spec[0],
                        )
                        self._sample_bytes = spec[1]
                    if audio_origin is None:
                        audio_origin = now
                    if video_origin is None:
                        pending.append((frame, now))
                    else:
                        self._write_audio(frame, now, video_origin, audio, boundary)
                else:
                    raise RuntimeError(f"unexpected scap frame type: {type(frame)!r}")
                if boundary is not None:
                    break
        finally:
            try:
                capturer.stop()
            except Exception:
                logger.debug("capturer.stop failed during cleanup", exc_info=True)
            try:
                if video is not None:
                    try:
                        if boundary is not None:
                            for data in selector.finish(boundary):
                                video.write_frame(data)
                    finally:
                        video.close()
            finally:
                if audio is not None:
                    audio.close()
        if audio_origin is not None and video_origin is not None:
            logger.debug(
                "Initial audio/video offset: %.3f ms",
                (audio_origin - video_origin) / 1_000_000,
            )

    def _write_audio(self, frame, stamp, video_origin, encoder, boundary=None):
        data = frame.data.tobytes()
        offset = stamp - video_origin
        size = frame.channels * self._sample_bytes
        if not self._audio_aligned:
            if offset > 0:
                encoder.write_frame(
                    b"\0" * (audio_padding_samples(offset, frame.rate) * size)
                )
            elif offset < 0:
                data = data[
                    min(len(data), audio_trim_samples(offset, frame.rate) * size) :
                ]
            self._audio_aligned = True
        if boundary is not None:
            # A buffer may straddle the stop marker. Preserve only samples whose
            # timestamp range reaches that marker (duration = sample_count / rate).
            allowed = max(
                0,
                min(
                    frame.sample_count, (boundary - stamp) * frame.rate // 1_000_000_000
                ),
            )
            data = data[: allowed * size]
        if data:
            encoder.write_frame(data)

    def _prepare_browser(self):
        service = self._create_browser_service()
        try:
            driver = service.create_driver()
            driver.get(self.args.url)
            service.enter_fullscreen(driver)
            service.validate_screen_resolution(driver)
            service.assert_full_resolution()
            service.enable_flash(driver)
            service.inject_dom(
                driver, config.TEMPLATE_HTML_PATH, self._build_replacements()
            )
            await_player_ready(driver)
        except BaseException:
            # Setup can fail before run() receives the service and driver.
            service.close()
            raise
        return service, driver

    @staticmethod
    def _watch(driver, stopped, errors):
        try:
            await_stopped(driver)
        except Exception as exc:
            # Forward worker errors to the main thread.
            errors.append(exc)
        finally:
            stopped.set()

    def _record_playback(self, driver, video_path, audio_path, service=None):
        driver.execute_script("player.pause();")
        await_started(driver)
        if service is None:
            target = BrowserService.get_capture_target(driver)
            crop_area = None
        else:
            target = service.get_capture_target(driver)
            crop_area = service.get_capture_crop_area(driver)
        capturer = self._create_capturer(target, crop_area)
        started = threading.Event()
        stopped = threading.Event()
        errors = []
        watcher = threading.Thread(
            target=self._watch, args=(driver, stopped, errors), daemon=True
        )
        try:
            capturer.start()
            watcher.start()
            driver.execute_script("player.play();")
            started.set()
            self._capture_streams(capturer, video_path, audio_path, started, stopped)
            watcher.join(30)
            if watcher.is_alive():
                raise TimeoutError("Playback did not stop within 30 seconds")
            if errors:
                raise errors[0]
        finally:
            stopped.set()
            try:
                capturer.stop()
            except Exception:
                # A second stop may fail; keep the original recording error.
                logger.debug("capturer.stop failed during cleanup", exc_info=True)
            if watcher.ident is not None:
                watcher.join(30)

    def _finish_recording(self, output, video, audio):
        muxer = FFmpegMuxer(config.FFMPEG_PATH)
        muxer.mux(video, audio if audio.is_file() else None, output)
        if not self.args.no_outro:
            muxer.append_outro(
                output,
                Path(self.args.use_outro),
                output,
                *self.args.resolution,
                config.FPS,
            )

    def _create_browser_service(self):
        return BrowserService(
            config.CHROME_PATH,
            config.CHROMEDRIVER_PATH,
            config.FLASH_PLUGIN_PATH,
            config.FLASH_PLUGIN_VERSION,
            *self.args.resolution,
        )

    def _build_replacements(self):
        return {
            "WINDOW_TITLE": self._capture_window_title,
            "PLAYER_WIDTH": self.args.resolution[0],
            "PLAYER_HEIGHT": self.args.resolution[1],
            "PLAYER_SWF_URL": self.args.swf_url,
            "IS_WIDE": int(self.args.is_wide),
            "API_SERVER": self.args.api_url,
            "STORE_PATH": self.args.store_path,
            "CLIENT_THEME_PATH": self.args.client_theme_path,
            "MOVIE_ID": self.args.movie_id,
            "USER_ID": self.args.user_id,
        }

    def run(self):
        import scap

        if not scap.is_supported():
            raise RuntimeError("This platform does not support screen capture")
        if not scap.has_permission() and not scap.request_permission():
            raise PermissionError("Screen-capture permission was denied")
        output = self._create_output_path()
        video = output.with_name(f"{output.stem}.video.mkv")
        audio = output.with_name(f"{output.stem}.audio.wav")
        service = driver = None
        complete = False
        try:
            service, driver = self._prepare_browser()
            self._record_playback(driver, video, audio, service)
            self._finish_recording(output, video, audio)
            complete = True
        finally:
            if service is not None:
                service.close()
            if complete:
                video.unlink(missing_ok=True)
                audio.unlink(missing_ok=True)
            elif video.exists() or audio.exists():
                logger.error(
                    "Retaining capture diagnostics after failure: %s, %s", video, audio
                )
        return 0
