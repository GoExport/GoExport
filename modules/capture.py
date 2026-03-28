import helpers
from modules.logger import logger
from modules.obs_capture import Capture as ObsCapture
from modules.native_capture import Capture as NativeCapture
from modules.enhanced_capture import Capture as EnhancedCapture

class Capture:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.startup_delay = None
        self.ended_delay = None
        self.process = None
        self.filename = None
        self.obs = ObsCapture()
        self.native = NativeCapture()
        self.enhanced = EnhancedCapture()
        self.is_obs = False
        if not self.is_obs and helpers.get_param("obs_required"):
            logger.fatal("OBS connection is required but could not be established.")
            raise Exception("OBS connection is required but could not be established.")

        # Connect to OBS WebSocket server
        try:
            self.obs.connect()
            self.is_obs = True
        except Exception as e:
            logger.error(f"Failed to connect to OBS WebSocket server: {e}")

    def retrieve(self):
        if self.is_obs:
            self.filename = self.obs.filename
            self.start_time = self.obs.start_time
            self.end_time = self.obs.end_time
            self.startup_delay = self.obs.startup_delay
            self.ended_delay = self.obs.ended_delay
        elif not self.is_obs and helpers.os_is_windows():
            self.filename = self.enhanced.filename
            self.start_time = self.enhanced.start_time
            self.end_time = self.enhanced.end_time
            self.startup_delay = self.enhanced.startup_delay
            self.ended_delay = self.enhanced.ended_delay
        else:
            self.filename = self.native.filename
            self.start_time = self.native.start_time
            self.end_time = self.native.end_time
            self.startup_delay = self.native.startup_delay
            self.ended_delay = self.native.ended_delay

    def start(self, output: str, width: int, height: int, window: str):
        if self.is_obs:
            object = self.obs.start(width, height, window)
        elif not self.is_obs and helpers.os_is_windows():
            object = self.enhanced.start(output, window, width, height)
        else:
            object = self.native.start(output, width, height)
        self.retrieve()
        return object
    
    def stop(self):
        self.retrieve()
        if self.is_obs:
            return self.obs.stop()
        elif not self.is_obs and helpers.os_is_windows():
            return self.enhanced.stop()
        else:
            return self.native.stop()