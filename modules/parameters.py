import argparse
import sys
import urllib.parse

class Parameters:
    def __init__(self):
        parser = argparse.ArgumentParser(
            description="Automate the process of exporting videos for GoExport"
        )
        # CLI args (same as yours)
        parser.add_argument("-ni", "--no-input", help="Skip all user input", action="store_true", dest="no_input")
        parser.add_argument("-j", "--json", help="Enable structured JSON output to STDOUT (diagnostics go to STDERR)", action="store_true", dest="json")
        parser.add_argument("-c", "--console", help="Force console mode (no GUI). NOT RECOMMENDED: May leave orphaned processes.", action="store_true", dest="console")
        parser.add_argument("-v", "--verbose", help="Enable verbose output", action="store_true", dest="verbose")
        parser.add_argument("-s", "--service", help="Set the service to use", dest="service")
        parser.add_argument("-r", "--resolution", help="Set the resolution to use", dest="resolution")
        parser.add_argument("-asr", "--aspect_ratio", help="Set the aspect ratio", dest="aspect_ratio")
        parser.add_argument("-oi", "--owner-id", help="Set the owner ID", dest="owner_id")
        parser.add_argument("-mi", "--movie-id", help="Set the movie ID", dest="movie_id")
        parser.add_argument("-ae", "--auto-edit", help="Enable auto editing", action="store_true", dest="auto_edit")
        parser.add_argument("-of", "--open-file", help="Determines if should open destination folder in no-input mode", action="store_true", dest="open_folder")
        parser.add_argument("-uo", "--use-outro", help="Enable adding outro in no-input mode", action="store_true", dest="use_outro")
        parser.add_argument("--obs-websocket-address", help="Set the OBS WebSocket address", dest="obs_websocket_address")
        parser.add_argument("--obs-websocket-port", help="Set the OBS WebSocket port", dest="obs_websocket_port")
        parser.add_argument("--obs-websocket-password", help="Set the OBS WebSocket password", dest="obs_websocket_password")
        parser.add_argument("--obs-fps", help="Set the OBS FPS", dest="obs_fps")
        parser.add_argument("--obs-no-overwrite", help="Prevent scene overwriting", action="store_true", dest="obs_no_overwrite")
        parser.add_argument("--obs-required", help="Require OBS connection", action="store_true", dest="obs_required")
        parser.add_argument("--output-path", help="Custom output path for the final rendered video", dest="output_path")
        parser.add_argument("--load-timeout", help="Timeout in minutes to wait for video to load (default: 30, 0 to disable)", type=int, default=30, dest="load_timeout")
        parser.add_argument("--video-timeout", help="Timeout in minutes to wait for video to finish after loading (default: 0/disabled)", type=int, default=0, dest="video_timeout")
        parser.add_argument("--x11grab-display", help="X11 display for ffmpeg's x11grab input (Linux only, default: :0.0)", dest="x11grab_display")
        parser.add_argument("--pulse-audio", help="PulseAudio source for ffmpeg input (Linux only)", dest="pulse_audio")
        parser.add_argument("--skip-resolution-check", help="Skip the exceeds resolution check", action="store_true", dest="skip_resolution_check")
        parser.add_argument("--monitor-index", help="Monitor index for get_resolution (default: 0)", type=int, default=0, dest="monitor_index")
        parser.add_argument("--ffmpeg-linux-args", help="Custom arguments to append to FFmpeg Linux recording commands", dest="ffmpeg_linux_args")
        parser.add_argument("--ffmpeg-windows-args", help="Custom arguments to append to FFmpeg Windows recording commands", dest="ffmpeg_windows_args")
        parser.add_argument("--ffmpeg-encode-args", help="Custom arguments to append to FFmpeg encoding commands", dest="ffmpeg_encode_args")
        parser.add_argument("--ffmpeg-linux-override", help="Override the entire FFmpeg Linux recording command (advanced users only)", dest="ffmpeg_linux_override")
        parser.add_argument("--ffmpeg-windows-override", help="Override the entire FFmpeg Windows recording command (advanced users only)", dest="ffmpeg_windows_override")
        parser.add_argument("--ffmpeg-encode-override", help="Override the entire FFmpeg encoding command (advanced users only)", dest="ffmpeg_encode_override")
        parser.add_argument("--protocol", help="Protocol URL e.g. goexport://?video_id=1&user_id=1&aspect_ratio=16:9&resolution=1920x1080&no_input=true", dest="protocol")

        args = parser.parse_args()

        # If protocol provided, parse and merge into args
        if args.protocol:
            proto_args = self._parse_protocol(args.protocol)
            # Apply protocol values over parsed args
            for k, v in proto_args.items():
                # only set when we have a non-None value
                if v is not None:
                    setattr(args, k, v)

        # Expose as attributes on the instance and print (to stderr in json/no-input mode)
        for key, value in vars(args).items():
            # In json mode or no-input mode, print to stderr to keep stdout clean for JSON output
            if args.json or args.no_input:
                print(f"Parameter {key} set to {value}", file=sys.stderr)
            else:
                print(f"Parameter {key} set to {value}")
            setattr(self, key, value)

    def _parse_protocol(self, uri: str):
        """
        Parse goexport:// protocol URL and return a dict that maps to argparse dest names.
        Keys returned match the parser dest names (movie_id, owner_id, aspect_ratio, resolution, no_input, service).
        """
        parsed = urllib.parse.urlparse(uri)
        qs = urllib.parse.parse_qs(parsed.query)

        def _first(name):
            return qs.get(name, [None])[0]

        # map protocol query names to argparse dest names
        proto_map = {
            "service": "service",
            "video_id": "movie_id",
            "user_id": "owner_id",
            "aspect_ratio": "aspect_ratio",
            "resolution": "resolution",
            "no_input": "no_input",
            "json": "json",
            "open_folder": "open_folder",
            "use_outro": "use_outro",
            "obs_websocket_address": "obs_websocket_address",
            "obs_websocket_port": "obs_websocket_port",
            "obs_websocket_password": "obs_websocket_password",
            "obs_fps": "obs_fps",
            "obs_no_overwrite": "obs_no_overwrite",
            "obs_required": "obs_required",
            "output_path": "output_path",
            "load_timeout": "load_timeout",
            "video_timeout": "video_timeout",
            "x11grab_display": "x11grab_display",
            "pulse_audio": "pulse_audio",
            "ffmpeg_linux_args": "ffmpeg_linux_args",
            "ffmpeg_windows_args": "ffmpeg_windows_args",
            "ffmpeg_encode_args": "ffmpeg_encode_args",
            "ffmpeg_linux_override": "ffmpeg_linux_override",
            "ffmpeg_windows_override": "ffmpeg_windows_override",
            "ffmpeg_encode_override": "ffmpeg_encode_override",
        }

        result = {
            "service": None,
            "movie_id": None,
            "owner_id": None,
            "aspect_ratio": "16:9",
            "resolution": "360p",
            "no_input": True,
            "json": False,
            "open_folder": False,
            "use_outro": True,
            "obs_websocket_address": "localhost",
            "obs_websocket_port": "4455",
            "obs_websocket_password": "",
            "obs_fps": "60",
            "obs_no_overwrite": False,
            "obs_required": False,
            "output_path": None,
            "load_timeout": 30,
            "video_timeout": 0,
            "x11grab_display": ":0.0",
            "pulse_audio": None,
            "skip_resolution_check": False,
            "monitor_index": 0,
            "ffmpeg_linux_args": None,
            "ffmpeg_windows_args": None,
            "ffmpeg_encode_args": None,
            "ffmpeg_linux_override": None,
            "ffmpeg_windows_override": None,
            "ffmpeg_encode_override": None,
        }

        # action/service can be provided in netloc or path; prefer netloc (e.g., goexport://upload?...).
        if parsed.netloc:
            result["service"] = parsed.netloc
        elif parsed.path and parsed.path != "/":
            result["service"] = parsed.path.lstrip("/")

        # Fill mapped fields
        for qname, dest in proto_map.items():
            val = _first(qname)
            if val is not None:
                # Convert all boolean parameters
                if dest in ("no_input", "json", "open_folder", "use_outro", "obs_no_overwrite", "obs_required", "skip_resolution_check"):
                    result[dest] = self._str_to_bool(val)
                # Convert integer parameters
                elif dest in ("load_timeout", "video_timeout", "monitor_index"):
                    try:
                        result[dest] = int(val)
                    except ValueError:
                        pass  # Keep default if invalid
                else:
                    result[dest] = val

        return result

    def _str_to_bool(self, s: str) -> bool:
        """Convert strings like 'true', '1', 'yes' to True, otherwise False."""
        if s is None:
            return False
        return s.strip().lower() in ("1", "true", "yes", "y", "t")


# Singleton instance - created once and reused
_instance = None
_lock = __import__('threading').Lock()

def get_parameters():
    """Get the singleton Parameters instance (thread-safe)."""
    global _instance
    if _instance is None:
        with _lock:
            # Double-check locking pattern
            if _instance is None:
                _instance = Parameters()
    return _instance

if __name__ == "__main__":
    params = get_parameters()
