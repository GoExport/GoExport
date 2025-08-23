import helpers
import obsws_python as obs
from modules.logger import logger
import atexit
import signal
import sys

class Capture:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.startup_delay = None
        self.ended_delay = None
        self.process = None
        self.filename = None
        self.recording = False
        self.ws = None
        self.cl = None
        self.prepared = False

        # Register cleanup handlers
        atexit.register(self._cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def connect(self):
        try:
            self.ws = obs.ReqClient(
                host=helpers.get_config("OBS_SERVER_HOST"),
                port=helpers.get_config("OBS_SERVER_PORT"),
                password=helpers.get_config("OBS_SERVER_PASSWORD"),
                timeout=3
            )
            self.cl = obs.EventClient(
                host=helpers.get_config("OBS_SERVER_HOST"),
                port=helpers.get_config("OBS_SERVER_PORT"),
                password=helpers.get_config("OBS_SERVER_PASSWORD"),
                timeout=3
            )
            logger.info("Connected to OBS WebSocket server.")
        except Exception as e:
            logger.error(f"Failed to connect to OBS WebSocket server: {e}")
            raise e

    def prep(self, output: str, width: int, height: int):
        try:
            self.cl.callback.register(self.on_record_state_changed)
            self.ws.create_profile(name=f"{helpers.get_config('APP_NAME')} - Profile")
            self.ws.create_scene(name=f"{helpers.get_config('APP_NAME')} - Scene")
            if self.ws.get_studio_mode_enabled().studio_mode_enabled:
                self.ws.set_current_preview_scene(name=f"{helpers.get_config('APP_NAME')} - Scene")
            self.ws.set_current_program_scene(name=f"{helpers.get_config('APP_NAME')} - Scene")
            self.ws.set_video_settings(
                base_width=width,
                base_height=height,
                out_width=width,
                out_height=height,
                denominator=1,
                numerator=helpers.get_config("OBS_FPS")
            )
            self.ws.set_input_mute(name="Desktop Audio", muted=True)
            self.ws.set_input_mute(name="Mic/Aux", muted=True)
            self.ws.create_input(
                sceneName=f"{helpers.get_config('APP_NAME')} - Scene",
                inputName=f"{helpers.get_config('APP_NAME')} - Capture",
                inputKind="window_capture",
                inputSettings={
                    "window": "GoExport Viewer:Chrome_WidgetWin_1:chrome.exe",
                    "cursor": False,
                    "capture_audio": True,
                    "client_area": True
                },
                sceneItemEnabled=True
            )
            # self.ws.set_profile_parameter(category="AdvOutput", name="RecFormat2", value="mp4")
            helpers.wait(4, "Waiting for OBS to set up the scene and sources...")
            self.prepared = True
        except Exception as e:
            logger.error(f"Failed to prepare OBS: {e}")
            self.prepared = False

    def unprep(self):
        try:
            self.ws.set_input_mute(name="Desktop Audio", muted=False)
            self.ws.set_input_mute(name="Mic/Aux", muted=False)
            self.ws.remove_scene(name=f"{helpers.get_config('APP_NAME')} - Scene")
            self.ws.remove_profile(name=f"{helpers.get_config('APP_NAME')} - Profile")
            logger.info("OBS: Unprepared successfully.")
        except Exception as e:
            logger.error(f"Failed to unprepare OBS: {e}")

    def on_record_state_changed(self, data):
        self.filename = data.output_path
        self.recording = data.output_active
        self.state = data.output_state

    def start(self, output: str, width: int, height: int):
        try:
            self.prep(output, width, height)
            if not self.prepared:
                return False
            self.ws.start_record()
            offset = helpers.get_timestamp("OBS starting")
            helpers.wait_for(True, self.recording, lambda: self.recording)
            self.start_time = helpers.get_timestamp("OBS started")

            # Calculate startup delay
            self.startup_delay = self.start_time - offset

            return True
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self._cleanup()
            return False

    def stop(self):
        try:
            offset = helpers.get_timestamp("OBS stopping")
            self.ws.stop_record()
            helpers.wait_for(False, self.recording, lambda: self.recording)
            self.end_time = helpers.get_timestamp("OBS stopped")

            # Calculate ending delay
            self.ended_delay = self.end_time - offset

            logger.info("OBS: Stopped recording")
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            self._cleanup()
            return False
        return True

    def _cleanup(self):
        if self.ws and self.prepared:
            try:
                self.unprep()
            except Exception as e:
                logger.error(f"Cleanup failed: {e}")

    def _signal_handler(self, signum, frame):
        logger.warning(f"Received signal {signum}, cleaning up OBS...")
        self._cleanup()
        sys.exit(1)