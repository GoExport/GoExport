"""Shared browser/playback orchestration for recording capture backends."""

from __future__ import annotations

import argparse
import logging
import threading
import uuid
from pathlib import Path

from goexport import config
from goexport.helpers import resolve_output_path
from goexport.player_options import build_player_replacements, replacement_overrides
from goexport.reporting import get_reporter
from goexport.services.browser import BrowserService
from goexport.services.ffmpeg import FFmpegMuxer
from goexport.services.flash import (
    await_player_ready,
    await_started,
    await_stopped,
    get_total_frames,
)
from goexport.services.recording_backends import (
    CaptureArtifacts,
    create_recording_backend,
)
from goexport.services.recording_backends.pyscap import recording_progress

logger = logging.getLogger(__name__)


class RecordingService:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.reporter = get_reporter(args)
        self._capture_window_title = f"GoExport Recorder {uuid.uuid4().hex}"

    def _ffmpeg_path(self):
        return getattr(self.args, "ffmpeg_path", config.FFMPEG_PATH)

    def _create_output_path(self):
        return resolve_output_path(Path(self.args.output), self.args.format)

    def _prepare_browser(self):
        service = self._create_browser_service()
        try:
            driver = service.create_driver()
            driver.get(self.args.url)
        except BaseException:
            service.close()
            raise
        return service, driver

    def _finish_browser_setup(self, service, driver, backend_name="pyscap"):
        if backend_name == "pyscap":
            service.remember_capture_target(driver)
        else:
            # Bind OBS to the unique title even if macOS exposes the
            # pre-fullscreen native title after Chromium enters fullscreen.
            driver.execute_script(
                "document.title = arguments[0];", self._capture_window_title
            )
        service.enter_fullscreen(driver)
        service.validate_screen_resolution(driver)
        service.assert_full_resolution()
        service.enable_flash(driver)
        service.inject_dom(
            driver, config.TEMPLATE_HTML_PATH, self._build_replacements()
        )
        await_player_ready(
            driver,
            timeout_seconds=0 if getattr(self.args, "no_flash_timeout", False) else 30,
        )

    @staticmethod
    def _watch(driver, stopped, errors):
        try:
            await_stopped(driver)
        except Exception as exc:
            errors.append(exc)
        finally:
            stopped.set()

    def _record_playback(self, driver, backend, service=None):
        driver.execute_script("player.pause();")
        await_started(
            driver,
            timeout_minutes=0 if getattr(self.args, "no_flash_timeout", False) else 30,
        )
        started = threading.Event()
        stopped = threading.Event()
        errors = []
        watcher = threading.Thread(
            target=self._watch, args=(driver, stopped, errors), daemon=True
        )
        result = None
        try:
            backend.start()
            total_frames = get_total_frames(driver, config.FPS)
            if total_frames <= 0:
                raise RuntimeError("The movie has no frames to record")
            total_duration_ns = total_frames * 1_000_000_000 // config.FPS
            watcher.start()
            driver.execute_script("player.play();")
            started.set()
            result = backend.capture_until_stopped(started, stopped, total_duration_ns)
            watcher.join(30)
            if watcher.is_alive():
                raise TimeoutError("Playback did not stop within 30 seconds")
            if errors:
                raise errors[0]
            return result
        finally:
            stopped.set()
            if result is None:
                try:
                    backend.stop()
                except Exception:
                    logger.debug("capture stop failed during cleanup", exc_info=True)
            if watcher.ident is not None:
                watcher.join(30)

    def _finish_recording(self, output, result):
        muxer = FFmpegMuxer(self._ffmpeg_path())
        self.reporter.progress(85, "muxing")
        if result.audio_is_muxed:
            muxer.mux_combined(result.video, output)
        else:
            muxer.mux(result.video, result.audio, output)
        if not self.args.no_outro:
            self.reporter.progress(95, "outro")
            muxer.append_outro(
                output,
                Path(self.args.use_outro),
                output,
                *self.args.resolution,
                config.FPS,
            )
        self.reporter.progress(99, "finalizing")

    def _create_browser_service(self):
        return BrowserService(
            getattr(self.args, "chrome_path", config.CHROME_PATH),
            getattr(self.args, "chromedriver_path", config.CHROMEDRIVER_PATH),
            getattr(self.args, "flash_plugin_path", config.FLASH_PLUGIN_PATH),
            getattr(self.args, "flash_plugin_version", config.FLASH_PLUGIN_VERSION),
            getattr(self.args, "electron", config.ELECTRON),
            *self.args.resolution,
            use_virtual_display=(
                getattr(self.args, "capture_backend", "pyscap") != "obs"
            ),
        )

    def _build_replacements(self):
        values = {
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
        return build_player_replacements(
            values,
            getattr(self.args, "additional_flashvars", {}),
            {"user_id": self.args.user_id, "movie_id": self.args.movie_id},
            config.PLACEHOLDER_REPLACEMENTS,
            replacement_overrides(getattr(self.args, "replacement", [])),
        )

    def _create_backend(self, name):
        return create_recording_backend(
            name,
            args=self.args,
            reporter=self.reporter,
            ffmpeg_path=self._ffmpeg_path(),
            window_title=self._capture_window_title,
        )

    @staticmethod
    def _cleanup_result(result):
        for path in result.owned_paths:
            if path.is_file():
                path.unlink(missing_ok=True)
        for path in result.owned_paths:
            if path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    logger.warning("OBS intermediate directory is not empty: %s", path)

    def run(self):
        self.reporter.progress(0, "preparing")
        output = self._create_output_path()
        artifacts = CaptureArtifacts(
            output.with_name(f"{output.stem}.video.mkv"),
            output.with_name(f"{output.stem}.audio.wav"),
            output.parent,
        )
        backend_name = getattr(self.args, "capture_backend", "pyscap")
        backend = self._create_backend(backend_name)
        service = driver = result = None
        complete = False
        try:
            service, driver = self._prepare_browser()
            backend.check_available(service.capture_display)
            self._finish_browser_setup(service, driver, backend_name)
            backend.prepare(service, driver, artifacts)
            self.reporter.progress(5, "recording")
            result = self._record_playback(driver, backend, service)
            self._finish_recording(output, result)
            complete = True
        finally:
            try:
                backend.close()
            finally:
                if service is not None:
                    service.close()
            if complete and result is not None:
                self._cleanup_result(result)
            elif result is not None or any(
                path.exists()
                for path in (artifacts.video, artifacts.audio, artifacts.obs_directory)
            ):
                logger.error(
                    "Retaining capture diagnostics after failure beside %s", output
                )
        self.reporter.complete(output)
        return 0


__all__ = ["RecordingService", "recording_progress"]
