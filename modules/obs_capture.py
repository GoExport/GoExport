import helpers
from obswebsocket import obsws, requests
from modules.logger import logger

class Capture:
    def __init__(self):
        self.ws = obsws(host=helpers.get_config("OBS_SERVER_HOST"), port=helpers.get_config("OBS_SERVER_PORT"), password=helpers.get_config("OBS_SERVER_PASSWORD"))
        self.ws.connect()