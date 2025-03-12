import helpers
import subprocess
import time
import atexit
import signal
from modules.logger import logger


class Capture:
    def __init__(self):
        self.process = None
        self.start_time = None
        self.startup_delay = None  # Store delay estimation
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
            command = [
                helpers.get_path(None, helpers.get_config("PATH_FFMPEG")),
                "-y",
                "-f",
                "dshow",
                "-i",
                "video=screen-capture-recorder:audio=virtual-audio-capturer",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-tune",
                "zerolatency",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "256k",
                "-ac",
                "2",
                "-ar",
                "44100",
                "-filter:a",
                "volume=1.0",
                "-vf",
                f"crop={width}:{height}:0:0,format=yuv420p",
                output,
            ]
        elif helpers.os_is_linux():
            command = [
                helpers.get_path(None, helpers.get_config("PATH_FFMPEG")),
                "-y",
                "-f",
                "x11grab",
                "-s",
                f"{width}x{height}",
                "-i",
                ":0.0",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-tune",
                "zerolatency",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "256k",
                "-ac",
                "2",
                "-ar",
                "44100",
                "-filter:a",
                "volume=1.0",
                output,
            ]
        else:
            logger.error("Unsupported OS")
            return False

        self.start_time = helpers.get_timestamp("FFmpeg starting")

        self.process = subprocess.Popen(
            command,
            cwd=helpers.get_cwd(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            bufsize=0,
        )

        # Read stderr to detect when recording starts
        for line in iter(self.process.stderr.readline, b""):
            decoded_line = line.decode("GBK").strip()

            # Detect when FFmpeg starts writing to output
            if "Output #0" in decoded_line or "Press [q] to stop" in decoded_line:
                self.startup_delay = helpers.get_timestamp("FFmpeg started") - self.start_time
                break

        return True

    def stop(self):
        self.end_time = helpers.get_timestamp("FFmpeg ending")
        self.process.stdin.write("q".encode("GBK"))
        self.process.communicate()
        self.process.wait()
        self.end_delay = helpers.get_timestamp("FFmpeg ended") - self.end_time
        return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
