import helpers
from modules.logger import logger
from modules.obs_capture import Capture as ObsCapture
from modules.native_capture import Capture as NativeCapture

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
        self.is_obs = False

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
        else:
            self.filename = self.native.filename
            self.start_time = self.native.start_time
            self.end_time = self.native.end_time
            self.startup_delay = self.native.startup_delay
            self.ended_delay = self.native.ended_delay

    def start(self, output: str, width: int, height: int):
        if self.is_obs:
            object = self.obs.start(width, height)
        else:
            object = self.native.start(output, width, height)
        self.retrieve()
        return object
    
    def stop(self):
        self.retrieve()
        if self.is_obs:
            return self.obs.stop()
        else:
            return self.native.stop()