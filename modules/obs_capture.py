import helpers
from obswebsocket import obsws, requests
from modules.logger import logger

class Capture:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.startup_delay = None
        self.ended_delay = None
        self.process = None
        self.ws = obsws(host=helpers.get_config("OBS_SERVER_HOST"), port=helpers.get_config("OBS_SERVER_PORT"), password=helpers.get_config("OBS_SERVER_PASSWORD"))
    
    def connect(self):
        try:
            self.ws.connect()
            logger.info("Connected to OBS WebSocket server.")
        except Exception as e:
            logger.error(f"Failed to connect to OBS WebSocket server: {e}")

    def prep(self, output: str, width: int, height: int):
        # Set profile
        self.ws.call(requests.CreateProfile(profileName=f"{helpers.config("APP_NAME")} - Profile"))
        # Create scene
        self.ws.call(requests.CreateScene(sceneName=f"{helpers.config("APP_NAME")} - Scene"))
        # Set current scene
        self.ws.call(requests.SetCurrentPreviewScene(sceneName=f"{helpers.config("APP_NAME")} - Scene"))
        self.ws.call(requests.SetCurrentProgramScene(sceneName=f"{helpers.config("APP_NAME")} - Scene"))
        # Set video settings
        self.ws.call(requests.SetVideoSettings(baseWidth=width, baseHeight=height, outputWidth=width, outputHeight=height))
        # Mute Mute all inputs that aren't already muted using SetInputMute
        self.ws.call(requests.SetInputMute(inputName="Desktop Audio", inputMuted=True))
        self.ws.call(requests.SetInputMute(inputName="Mic/Aux", inputMuted=True))
        # Create source
        self.ws.call(requests.CreateInput(
            sceneName=f"{helpers.config("APP_NAME")} - Scene",
            inputName=f"{helpers.config("APP_NAME")} - Capture",
            inputKind="window_capture",
            inputSettings={
                "window": "GoExport Viewer:Chrome_WidgetWin_1:chrome.exe",
                "cursor": False,
                "capture_audio": True,
                "client_area": True
            }
        ))
        # Wait a moment for everything to be set up
        helpers.wait(4, "Waiting for OBS to set up the scene and sources...")

    def unprep(self):
        # Remove profile
        self.ws.call(requests.RemoveProfile(profileName="GoExport"))
        # Remove scene
        self.ws.call(requests.RemoveScene(sceneName="GoExport"))
        # Unmute desktop audio and mic audio using SetInputMute
        self.ws.call(requests.SetInputMute(inputName="Desktop Audio", inputMuted=False))
        self.ws.call(requests.SetInputMute(inputName="Mic/Aux", inputMuted=False))

    def start(self, output: str, width: int, height: int):
        try:
            self.prep(output, width, height)
            self.ws.call(requests.StartRecord())
            helpers.wait(0.5)
            logger.info("OBS: Started recording")
            return True
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False

    def stop(self):
        try:
            self.ws.call(requests.StopRecord())
            helpers.wait(0.5)
            self.unprep()
            logger.info("OBS: Stopped recording")
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            return False
        return True