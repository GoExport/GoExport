import helpers
import subprocess
import threading
import atexit
import signal
from modules.logger import logger

class Capture:
    def __init__(self):
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
            command = [
                helpers.get_path(None, helpers.get_config("PATH_FFMPEG")),
                "-y",
                "-f",
                "dshow",
                "-i",
                "video=screen-capture-recorder:audio=virtual-audio-capturer",
                "-r",
                "24",
                "-vf",
                f"crop={width}:{height}:0:0,format=yuv444p",
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

        def monitor_ffmpeg():
            for line in self.process.stdout:
                print(line, end="")  # Print FFmpeg output to console
                if "Error" in line or "Invalid" in line or "failed" in line.lower():
                    logger.critical(f"FFmpeg encountered an issue: {line.strip()}")

            # If the process unexpectedly stops
            self.process.wait()
            if self.process.returncode not in (0, None):
                logger.critical(f"FFmpeg stopped unexpectedly with code {self.process.returncode}")

        # Start monitoring in a separate thread
        threading.Thread(target=monitor_ffmpeg, daemon=True).start()

        # Wait for FFmpeg to start
        for line in self.process.stdout:
            if "Output #0" in line:
                self.start_time = helpers.get_timestamp("FFmpeg started")
                break
            offset = helpers.get_timestamp("FFmpeg starting")

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
