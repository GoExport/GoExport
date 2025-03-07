import helpers
import subprocess
import time
import atexit
import signal
from modules.logger import logger

class Capture:
    def __init__(self):
        self.process = None
        # Register cleanup handler for normal exits
        atexit.register(self.cleanup)
        # Register signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT):
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum, frame):
        self.cleanup()
        # Re-raise the signal to allow the default behavior to occur
        signal.signal(signum, signal.SIG_DFL)
        signal.raise_signal(signum)

    def cleanup(self):
        if self.process and self.process.poll() is None:
            try:
                logger.info("Terminating ffmpeg process due to application exit")
                self.process.terminate()
                self.process.wait(timeout=2)  # Wait up to 2 seconds
            except (subprocess.TimeoutExpired, Exception) as e:
                logger.error(f"Error terminating ffmpeg process: {e}")
                try:
                    self.process.kill()  # Force kill if terminate doesn't work
                except Exception:
                    pass

    def start(self, output: str, width: int, height: int):
        # Start the ffmpeg process
        self.process = subprocess.Popen([
            helpers.get_path(None, helpers.get_config("PATH_FFMPEG")),
            "-y",
            "-f", "dshow",
            "-i", "video=screen-capture-recorder:audio=virtual-audio-capturer",
            "-c:v", "libx264",  # High-quality GPL encoder
            "-preset", "veryfast",  # Good balance of compression and speed
            "-crf", "23",  # Default visually lossless compression
            "-tune", "zerolatency",
            "-pix_fmt", "yuv420p",
            "-c:a", "libmp3lame",  # GPL-compatible audio encoder
            "-b:a", "256k",  # Higher bitrate for better audio quality
            "-ac", "2",  # Ensure stereo output
            "-ar", "44100",  # Standard audio sample rate
            "-filter:a", "volume=1.0",
            "-vf", f"crop={width}:{height}:0:0,format=yuv420p",
            output
        ], cwd=helpers.get_cwd(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, bufsize=0)

        # Read stderr in real-time without blocking
        for line in iter(self.process.stderr.readline, b''):
            decoded_line = line.decode("GBK").strip()

            # Check if the recording has started (detect output initialization)
            if "Output #0, mp4" in decoded_line:
                self.start_time_ms = helpers.get_timestamp("FFmpeg started")
                break

        return True

    def stop(self):
        self.process.stdin.write('q'.encode("GBK"))
        self.process.communicate()
        self.end_time_ms = helpers.get_timestamp("FFmpeg ended")
        self.process.wait()
        return True
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()