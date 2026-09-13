import argparse
import logging
import threading
from pathlib import Path

from goexport import config
from goexport.helpers import resolve_output_path
from goexport.services.browser import BrowserService
from goexport.services.ffmpeg import (
    FFmpegMuxer,
    FFmpegRawAudioEncoder,
    FFmpegRawVideoEncoder,
)
from goexport.services.flash import await_player_ready, await_started, await_stopped

logger = logging.getLogger(__name__)


class RecordingService:
    """Coordinate Flash playback, screen capture, and FFmpeg output."""

    def __init__(self, args: argparse.Namespace):
        self.args = args

    def _create_output_path(self) -> Path:
        return resolve_output_path(Path(self.args.output), self.args.format)

    def _create_capturer(self, target):
        import scap

        options = scap.CaptureOptions(
            fps=config.FPS,
            target=target,
            show_cursor=True,
            show_highlight=True,
            output_type="bgra",
            output_resolution="captured",
            captures_audio=True,
        )
        return scap.Capturer(options)

    def _capture_streams(
        self,
        capturer,
        video_path: Path,
        audio_path: Path,
        stop_event: threading.Event,
    ) -> None:
        video_encoder = None
        audio_encoder = None
        first_video_timestamp = None
        next_video_index = 0
        previous_video_data = None
        audio_formats = {
            "int8": "s8",
            "int16": "s16le",
            "int32": "s32le",
            "int64": "s64le",
            "uint8": "u8",
            "uint16": "u16le",
            "uint32": "u32le",
            "uint64": "u64le",
            "float32": "f32le",
            "float64": "f64le",
        }

        try:
            while not stop_event.is_set():
                frame = capturer.next_frame()

                if hasattr(frame, "width"):
                    # Video frames can arrive faster than the configured output
                    # rate. Keep the first frame for each output index and repeat
                    # the previous frame when the capture clock skips an index.
                    if frame.format not in {"bgra", "bgr0"}:
                        raise RuntimeError(
                            f"scap returned unsupported frame format: {frame.format}"
                        )

                    if video_encoder is None:
                        self._capture_dimensions = (
                            frame.width + frame.width % 2,
                            frame.height + frame.height % 2,
                        )
                        video_encoder = FFmpegRawVideoEncoder(
                            ffmpeg_path=config.FFMPEG_PATH,
                            output_file=video_path,
                            width=frame.width,
                            height=frame.height,
                            output_width=self.args.resolution[0],
                            output_height=self.args.resolution[1],
                            fps=config.FPS,
                        )

                    frame_data = frame.data.tobytes()
                    if first_video_timestamp is None:
                        first_video_timestamp = frame.timestamp

                    frame_index = int(
                        (frame.timestamp - first_video_timestamp) * config.FPS
                    )
                    if frame_index < next_video_index:
                        previous_video_data = frame_data
                        continue

                    if previous_video_data is not None:
                        while next_video_index < frame_index:
                            video_encoder.write_frame(previous_video_data)
                            next_video_index += 1

                    video_encoder.write_frame(frame_data)
                    previous_video_data = frame_data
                    next_video_index += 1
                elif hasattr(frame, "channels"):
                    # Audio and video are delivered by scap through the same
                    # queue, so the stream type is determined by its attributes.
                    if frame.planar:
                        raise RuntimeError("Planar scap audio is not supported")

                    if audio_encoder is None:
                        sample_format = audio_formats.get(frame.format)
                        if sample_format is None:
                            raise RuntimeError(
                                "scap returned unsupported audio format: "
                                f"{frame.format}"
                            )

                        audio_encoder = FFmpegRawAudioEncoder(
                            ffmpeg_path=config.FFMPEG_PATH,
                            output_file=audio_path,
                            channels=frame.channels,
                            sample_rate=frame.rate,
                            sample_format=sample_format,
                        )

                    audio_encoder.write_frame(frame.data.tobytes())
        finally:
            capturer.stop()
            if video_encoder is not None:
                video_encoder.close()
            if audio_encoder is not None:
                audio_encoder.close()

    @staticmethod
    def _raise_capture_error(capture_error: list[BaseException]) -> None:
        if capture_error:
            raise capture_error[0]

    def _prepare_browser(self) -> tuple[BrowserService, object]:
        browser_service = self._create_browser_service()
        driver = browser_service.create_driver()
        driver.get(self.args.url)
        browser_service.enter_fullscreen(driver)
        browser_service.validate_screen_resolution(driver)
        browser_service.assert_full_resolution()
        browser_service.enable_flash(driver)
        browser_service.inject_dom(
            driver,
            config.TEMPLATE_HTML_PATH,
            self._build_replacements(),
        )
        await_player_ready(driver)
        return browser_service, driver

    @staticmethod
    def _watch_for_playback_end(
        driver,
        stop_capture: threading.Event,
        playback_error: list[BaseException],
    ) -> None:
        try:
            await_stopped(driver)
        except BaseException as exc:
            playback_error.append(exc)
        finally:
            stop_capture.set()

    def _record_playback(
        self,
        driver,
        video_path: Path,
        audio_path: Path,
    ) -> None:
        # Pause first so the capture starts before the movie clock advances.
        driver.execute_script("player.pause();")
        await_started(driver)

        capture_target = BrowserService.get_capture_target(driver)
        capturer = self._create_capturer(capture_target)
        stop_capture = threading.Event()
        playback_error: list[BaseException] = []
        playback_thread = threading.Thread(
            target=self._watch_for_playback_end,
            args=(driver, stop_capture, playback_error),
            name="playback-watcher",
            daemon=True,
        )

        try:
            capturer.start()
            playback_thread.start()
            driver.execute_script("player.play();")
            self._capture_streams(
                capturer,
                video_path,
                audio_path,
                stop_capture,
            )
            playback_thread.join(timeout=30)
            if playback_thread.is_alive():
                raise TimeoutError("Playback did not stop within 30 seconds")
            self._raise_capture_error(playback_error)
        finally:
            stop_capture.set()
            capturer.stop()
            playback_thread.join(timeout=30)

    def _finish_recording(
        self,
        output_path: Path,
        video_path: Path,
        audio_path: Path,
    ) -> None:
        muxer = FFmpegMuxer(config.FFMPEG_PATH)
        if audio_path.is_file():
            # Stretching prevents a short video stream from ending before the
            # final audio samples when the capture clocks differ slightly.
            muxer.stretch_video_to_duration(
                video_path,
                muxer.duration(audio_path),
                fps=config.FPS,
            )
            muxer.mux(video_path, audio_path, output_path)
        else:
            video_path.replace(output_path)

        if not self.args.no_outro:
            muxer.append_outro(
                main_video_file=output_path,
                outro_file=Path(self.args.use_outro),
                output_file=output_path,
                width=self.args.resolution[0],
                height=self.args.resolution[1],
                fps=config.FPS,
            )

    def _create_browser_service(self) -> BrowserService:
        return BrowserService(
            chrome_path=config.CHROME_PATH,
            chromedriver_path=config.CHROMEDRIVER_PATH,
            flash_path=config.FLASH_PLUGIN_PATH,
            flash_version=config.FLASH_PLUGIN_VERSION,
            width=self.args.resolution[0],
            height=self.args.resolution[1],
        )

    def _build_replacements(self) -> dict[str, object]:
        return {
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

    def run(self) -> int:
        import scap

        if not scap.is_supported():
            raise RuntimeError("This platform does not support screen capture")

        if not scap.has_permission() and not scap.request_permission():
            raise PermissionError("Screen-capture permission was denied")

        output_path = self._create_output_path()
        video_path = output_path.with_name(
            f"{output_path.stem}.video{output_path.suffix}"
        )
        audio_path = output_path.with_name(
            f"{output_path.stem}.audio.wav"
        )
        browser_service = None
        driver = None

        try:
            browser_service, driver = self._prepare_browser()
            self._record_playback(driver, video_path, audio_path)
            self._finish_recording(output_path, video_path, audio_path)

        finally:
            if driver is not None:
                driver.quit()

            if browser_service is not None:
                browser_service.stop_display()

        return 0
