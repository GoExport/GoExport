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

        self.obs = ObsCapture()
        self.native = NativeCapture()
        self.is_obs = False

        # Connect to OBS WebSocket server
        try:
            self.obs.connect()
            self.is_obs = True
        except Exception as e:
            logger.error(f"Failed to connect to OBS WebSocket server: {e}")

    def start(self, output: str, width: int, height: int):
        if self.is_obs:
            object = self.obs.start(output, width, height)
        else:
            object = self.native.start(output, width, height)
        
        # Load the values reported by the recorder
        return object
    
    def stop(self):
        if self.is_obs:
            return self.obs.stop()
        else:
            return self.native.stop()