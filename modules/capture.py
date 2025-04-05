import helpers
import subprocess
import atexit
import signal
from modules.logger import logger

class Capture:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.startup_delay = None
        self.ended_delay = None
        self.process = None
        atexit.register(self.cleanup)
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT):
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum, frame):
        self.cleanup()
        signal.signal(signum, signal.SIG_DFL)
        signal.raise_signal(signum)

    def cleanup(self):
        if self.process and self.process.poll() is None:
            try:
                logger.info("Terminating ffmpeg process due to application exit")
                self.process.terminate()
                self.process.wait(timeout=2)
            except (subprocess.TimeoutExpired, Exception) as e:
                logger.error(f"Error terminating ffmpeg process: {e}")
                try:
                    self.process.kill()
                except Exception:
                    pass

    def start(self, output: str, width: int, height: int):
        if helpers.os_is_windows():
            if not helpers.recall("FFMPEG_COMPATIBILITY"):
                command = [
                    helpers.get_path(None, helpers.get_config("PATH_FFMPEG")),
                    "-y",
                    "-f",
                    "dshow",
                    "-i",
                    "video=screen-capture-recorder:audio=virtual-audio-capturer",
                    "-vf",
                    f"crop={width}:{height}:0:0,format=yuv420p",
                    "-c:v",
                    "libx264",  # Use H.264 codec for video
                    "-preset",
                    "ultrafast",  # Use ultrafast preset for faster encoding (lower CPU usage)
                    "-crf",
                    "23",  # Constant Rate Factor for good quality (lower is better, 23 is default)
                    "-pix_fmt",
                    "yuv420p",  # Ensure compatibility with most players
                    "-c:a",
                    "aac",  # Use AAC codec for audio
                    "-b:a",
                    "128k",  # Set audio bitrate to ensure good quality
                    "-ar",
                    "44100",  # Set audio sample rate to avoid bass boosting or distortion
                    output,
                ]
            else:
                command = [
                    helpers.get_path(None, helpers.get_config("PATH_FFMPEG")),
                    "-y",
                    "-f",
                    "gdigrab",
                    "-framerate",
                    "24",
                    "-offset_x",
                    "0",
                    "-offset_y",
                    "0",
                    "-video_size",
                    f"{width}x{height}",
                    "-i",
                    "desktop",
                    "-vf",
                    "format=yuv420p",
                    output,
                ]
        else:
            logger.error("Unsupported OS")
            return False

        self.process = subprocess.Popen(
            command,
            cwd=helpers.get_cwd(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            bufsize=0,
            universal_newlines=True,
        )

        # Wait for FFmpeg to start
        for line in self.process.stdout:
            # Check if FFmpeg has started
            if "Output #0" in line:
                self.start_time = helpers.get_timestamp("FFmpeg started")
                break
            logger.debug(line)
            offset = helpers.get_timestamp("FFmpeg starting")
        
        if not self.start_time:
            logger.error("Failed to start FFmpeg")
            helpers.show_popup(helpers.get_config("APP_NAME"), f"Unable to start screen recording - YOU MAY NOT BE COMPATIBLE.", 16)
            return False

        self.startup_delay = self.start_time - offset

        return True

    def stop(self):
        self.process.stdin.write("q")
        offset = helpers.get_timestamp("FFmpeg stopping")
        self.process.communicate()
        self.process.wait()
        self.end_time = helpers.get_timestamp("FFmpeg ended")
        self.ended_delay = self.end_time - offset
        return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()