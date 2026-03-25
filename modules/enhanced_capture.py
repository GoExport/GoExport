import helpers
from recap import Recorder, RecordingConfig
from modules.logger import logger


class Capture:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.startup_delay = None
        self.ended_delay = None
        self.filename = None
        self._recorder: Recorder | None = None

    def start(self, output: str, window: str, width: int = None, height: int = None):
        self.filename = output

        ffmpeg_path = None
        if helpers.os_is_windows():
            ffmpeg_path = helpers.get_path(
                helpers.get_app_folder(),
                helpers.get_config("PATH_FFMPEG_WINDOWS")
            )

        config = RecordingConfig(
            output=self.filename,
            window_title=window,
            overwrite=True,
            ffmpeg=ffmpeg_path,
            crop_position="top-left",
            crop_height=height,
            crop_width=width,
        )
        self._recorder = Recorder(config)

        logger.info(f"Starting recap capture of window '{window}' -> {self.filename}")
        offset = helpers.get_timestamp("recap capture starting")
        try:
            self._recorder.start()
        except Exception as e:
            logger.error(f"Failed to start recap capture: {e}")
            return False

        self.start_time = helpers.get_timestamp("recap capture started")
        self.startup_delay = self.start_time - offset
        logger.info(f"Capture started successfully (startup delay: {self.startup_delay}ms)")
        return True

    def stop(self):
        if not self._recorder:
            logger.warning("No active recorder to stop.")
            return False

        logger.info("Stopping recap capture...")
        offset = helpers.get_timestamp("recap capture stopping")
        try:
            self._recorder.stop()
            self._recorder.wait(timeout=30)
        except Exception as e:
            logger.error(f"Failed to stop recap capture: {e}")
            return False

        self.end_time = helpers.get_timestamp("recap capture stopped")
        self.ended_delay = self.end_time - offset
        logger.info(f"Capture stopped successfully (ended delay: {self.ended_delay}ms)")
        return True