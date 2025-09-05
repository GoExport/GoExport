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
        self.random = helpers.get_timestamp()
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
                host=helpers.get_param("obs_websocket_address") or helpers.load("obs_websocket_address") or helpers.get_config("OBS_SERVER_HOST"),
                port=helpers.get_param("obs_websocket_port") or helpers.load("obs_websocket_port") or helpers.get_config("OBS_SERVER_PORT"),
                password=helpers.get_param("obs_websocket_password") or helpers.load("obs_websocket_password") or helpers.get_config("OBS_SERVER_PASSWORD"),
                timeout=3
            )
            self.cl = obs.EventClient(
                host=helpers.get_param("obs_websocket_address") or helpers.load("obs_websocket_address") or helpers.get_config("OBS_SERVER_HOST"),
                port=helpers.get_param("obs_websocket_port") or helpers.load("obs_websocket_port") or helpers.get_config("OBS_SERVER_PORT"),
                password=helpers.get_param("obs_websocket_password") or helpers.load("obs_websocket_password") or helpers.get_config("OBS_SERVER_PASSWORD"),
                timeout=3
            )
            helpers.save("obs_websocket_address", helpers.get_param("obs_websocket_address") or helpers.load("obs_websocket_address") or helpers.get_config("OBS_SERVER_HOST"))
            helpers.save("obs_websocket_port", helpers.get_param("obs_websocket_port") or helpers.load("obs_websocket_port") or helpers.get_config("OBS_SERVER_PORT"))
            helpers.save("obs_websocket_password", helpers.get_param("obs_websocket_password") or helpers.load("obs_websocket_password") or helpers.get_config("OBS_SERVER_PASSWORD"))
            logger.info("Connected to OBS WebSocket server.")
        except Exception as e:
            logger.error(f"Failed to connect to OBS WebSocket server: {e}")
            raise e

    def set(self, width: int, height: int):
        # Try to set video settings (optional)
        if not helpers.get_param("obs_no_overwrite"):
            try:
                self.ws.set_video_settings(
                    base_width=width,
                    base_height=height,
                    out_width=width,
                    out_height=height,
                    denominator=1,
                    numerator=helpers.get_param("OBS_FPS") or helpers.load("OBS_FPS") or helpers.get_config("OBS_FPS")
                )
                helpers.wait(1)
            except Exception as e:
                logger.warning(f"Could not set video settings: {e}")

    def prep(self, width: int, height: int, window: str):
        try:
            self.cl.callback.register(self.on_record_state_changed)
            helpers.wait(1)
            # Try to create profile (optional)
            try:
                self.ws.create_profile(name=f"{helpers.get_config('APP_NAME')} - Profile")
                helpers.wait(1)
            except Exception as e:
                logger.warning(f"Could not create OBS profile: {e}")
                # If profile exists, try to switch to it
                try:
                    self.ws.set_current_profile(name=f"{helpers.get_config('APP_NAME')} - Profile")
                    helpers.wait(1)
                    logger.info("Switched to existing OBS profile.")
                except Exception as e2:
                    logger.error(f"Could not switch to existing OBS profile: {e2}")

            # Set resolution
            self.set(width, height)

            # Change recording path
            try:
                self.ws.set_record_directory(recordDirectory=helpers.get_path(None, helpers.get_config("DEFAULT_OUTPUT_FILENAME")))
                helpers.wait(1)
            except Exception as e:
                logger.warning(f"Could not change recording path: {e}")

            # Try to create scene (optional)
            try:
                # Try to create the scene
                self.ws.create_scene(name=f"{helpers.get_config('APP_NAME')} - Scene")
                helpers.wait(1)
            except Exception as e:
                logger.warning(f"Could not create OBS scene: {e}")
                # If scene exists, delete and recreate it
                if not helpers.get_param("obs_no_overwrite"):
                    try:
                        self.ws.remove_scene(name=f"{helpers.get_config('APP_NAME')} - Scene")
                        helpers.wait(1)
                        self.ws.create_scene(name=f"{helpers.get_config('APP_NAME')} - Scene")
                        helpers.wait(1)
                        logger.info("Deleted and recreated existing OBS scene.")
                        helpers.wait(1)
                    except Exception as e2:
                        logger.error(f"Could not delete and recreate OBS scene: {e2}")

            # Try to set preview scene (optional)
            try:
                if self.ws.get_studio_mode_enabled().studio_mode_enabled:
                    helpers.wait(1)
                    self.ws.set_current_preview_scene(name=f"{helpers.get_config('APP_NAME')} - Scene")
                    helpers.wait(1)
                helpers.wait(1)
            except Exception as e:
                logger.warning(f"Could not set preview scene: {e}")

            # Try to set program scene (optional)
            try:
                self.ws.set_current_program_scene(name=f"{helpers.get_config('APP_NAME')} - Scene")
                helpers.wait(1)
            except Exception as e:
                logger.warning(f"Could not set program scene: {e}")

            # Try to create input/source (optional)
            if not helpers.get_param("obs_no_overwrite"):
                try:
                    # Output a list of inputs
                    if helpers.os_is_windows():
                        self.ws.create_input(
                            sceneName=f"{helpers.get_config('APP_NAME')} - Scene",
                            inputName=f"{helpers.get_config('APP_NAME')} - Capture",
                            inputKind="window_capture",
                            inputSettings={
                                "window": f"{window}:Chrome_WidgetWin_1:chrome.exe",
                                "cursor": False,
                                "capture_audio": True,
                                "client_area": True
                            },
                            sceneItemEnabled=True
                        )
                        helpers.wait(1)
                    elif helpers.os_is_linux():
                        self.ws.create_input(
                            sceneName=f"{helpers.get_config('APP_NAME')} - Scene",
                            inputName=f"{helpers.get_config('APP_NAME')} - Capture",
                            inputKind="xcomposite_input",
                            inputSettings={
                                "capture_window": f"{window}\r\nchrome",
                                "cursor": False
                            },
                            sceneItemEnabled=True
                        )
                        helpers.wait(1)
                except Exception as e:
                    logger.warning(f"Could not create input/source: {e}")
            helpers.wait(2, "Waiting for OBS to set up the scene and sources...")
            self.prepared = True
        except Exception as e:
            logger.error(f"Failed to prepare OBS: {e}")
            self.prepared = False

    def unprep(self):
        try:
            if not helpers.get_param("obs_no_overwrite"):
                self.ws.remove_scene(name=f"{helpers.get_config('APP_NAME')} - Scene")
                helpers.wait(1)
            logger.info("OBS: Unprepared successfully.")
            self.prepared = False
        except Exception as e:
            logger.error(f"Failed to unprepare OBS: {e}")

    def on_record_state_changed(self, data):
        self.filename = data.output_path
        self.recording = data.output_active
        self.state = data.output_state

    def start(self, width: int, height: int, window: str):
        try:
            self.prep(width, height, window)
            if not self.prepared:
                return False
            self.ws.start_record()
            offset = helpers.get_timestamp("OBS starting")
            helpers.wait_for(True, lambda: self.recording, reason="Waiting for OBS to start recording...")
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
            helpers.wait_for(False, lambda: self.recording, reason="Waiting for OBS to stop recording...")
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