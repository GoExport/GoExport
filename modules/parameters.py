import argparse

class Parameters:
    def __init__(self):
        parser = argparse.ArgumentParser(description="Automate the process of exporting videos for GoExport")
        parser.add_argument("-ni", "--no-input", help="Skip all user input", action="store_true", dest="no_input")
        parser.add_argument("-v", "--verbose", help="Enable verbose output", action="store_true", dest="verbose")
        parser.add_argument("-s", "--service", help="Set the service to use", dest="service")
        parser.add_argument("-r", "--resolution", help="Set the resolution to use", dest="resolution")
        parser.add_argument("-asr", "--aspect_ratio", help="Set the aspect ratio", dest="aspect_ratio")
        parser.add_argument("-oi", "--owner-id", help="Set the owner ID", dest="owner_id")
        parser.add_argument("-mi", "--movie-id", help="Set the movie ID", dest="movie_id")
        parser.add_argument("-ae", "--auto-edit", help="Enable auto editing", action="store_true", dest="auto_edit")
        parser.add_argument("--obs-websocket-address", help="Set the OBS WebSocket address", dest="obs_websocket_address")
        parser.add_argument("--obs-websocket-port", help="Set the OBS WebSocket port", dest="obs_websocket_port")
        parser.add_argument("--obs-websocket-password", help="Set the OBS WebSocket password", dest="obs_websocket_password")
        parser.add_argument("--obs-fps", help="Set the OBS FPS", dest="obs_fps")
        parser.add_argument("--obs-no-overwrite", help="Controls whether GoExport will overwrite your scenes (ADVANCED, use if you want to configure your GoExport scene in OBS). Set to true to allow overwriting, false to prevent it.", action="store_true", dest="obs_no_overwrite")
        parser.add_argument("-ngui", "--no-gui", help="Run without GUI (for advanced users)", action="store_true", dest="no_gui")

        args = parser.parse_args()
        for key, value in vars(args).items():
            print(f"Parameter {key} set to {value}")
            setattr(self, key, value)