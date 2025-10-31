import helpers
import subprocess
import atexit
import signal
import os
import tempfile
from modules.logger import logger

class Capture:
    """
    Native screen capture using FFmpeg with dshow (Windows) or x11grab (Linux).
    
    This implementation uses a two-stage approach to prevent buffer overflow:
    1. Capture raw video with minimal encoding (fast, prevents dropped frames)
    2. Encode to final format in a separate process after capture completes
    
    This ensures the capture buffer never overflows while still producing
    high-quality output identical to the previous implementation.
    """
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.startup_delay = None
        self.ended_delay = None
        self.filename = None
        self.raw_filename = None
        self.process = None
        self.width = None
        self.height = None
        atexit.register(self.cleanup)
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT):
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle signals for graceful cleanup."""
        self.cleanup()
        signal.signal(signum, signal.SIG_DFL)
        signal.raise_signal(signum)

    def cleanup(self):
        """Clean up resources and terminate FFmpeg process if running."""
        if self.process and self.process.poll() is None:
            try:
                logger.info("Terminating ffmpeg capture process due to application exit")
                self.process.terminate()
                self.process.wait(timeout=2)
            except (subprocess.TimeoutExpired, Exception) as e:
                logger.error(f"Error terminating ffmpeg process: {e}")
                try:
                    self.process.kill()
                except Exception:
                    pass
        
        # Clean up temporary raw file if it exists
        if self.raw_filename and os.path.exists(self.raw_filename):
            try:
                os.remove(self.raw_filename)
                logger.debug(f"Cleaned up temporary raw file: {self.raw_filename}")
            except Exception as e:
                logger.warning(f"Could not remove temporary raw file {self.raw_filename}: {e}")

    def start(self, output: str, width: int, height: int):
        """
        Start capturing screen video using raw format for minimal encoding overhead.
        
        :param output: Final output path for the encoded video.
        :param width: Width of the capture area.
        :param height: Height of the capture area.
        :return: True if capture started successfully, False otherwise.
        """
        # Store parameters for later encoding
        self.filename = output
        self.width = width
        self.height = height
        
        # Create a temporary file for raw capture in the same directory as output
        output_dir = os.path.dirname(output)
        temp_basename = os.path.basename(output).replace('.mp4', '_raw.mkv')
        self.raw_filename = os.path.join(output_dir, temp_basename)
        
        logger.info(f"Starting raw video capture to: {self.raw_filename}")
        
        if helpers.os_is_windows():
            # Windows: Use dshow with minimal encoding
            # Use ultrafast preset and nut/mkv container for minimal overhead
            command = [
                helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_FFMPEG_WINDOWS")), "-y",
                "-f", "dshow",
                "-rtbufsize", "1500M",  # Increase buffer size to prevent overflow
                "-i", "video=screen-capture-recorder:audio=virtual-audio-capturer",
                "-vf", f"crop={width}:{height}:0:0",  # Crop to exact dimensions
                "-c:v", "libx264",  # Use H.264 for raw capture
                "-preset", "ultrafast",  # Fastest encoding to keep up with capture
                "-crf", "0",  # Lossless quality for raw capture
                "-tune", "zerolatency",  # Optimize for real-time encoding
                "-pix_fmt", "yuv420p",  # Standard pixel format
                "-c:a", "pcm_s16le",  # Uncompressed audio for raw capture
                "-ar", "44100",  # Standard audio sample rate
                self.raw_filename,
            ]
        elif helpers.os_is_linux():
            # Linux: Use x11grab with minimal encoding
            command = [
                helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_FFMPEG_LINUX")), "-y",
                "-f", "x11grab",
                "-s", f"{width}x{height}",
                "-i", ":0.0",
                "-f", "pulse",
                "-i", "alsa_output.pci-0000_00_1b.0.analog-stereo.monitor",
                "-ac", "2",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "0",
                "-tune", "zerolatency",
                "-pix_fmt", "yuv420p",
                "-c:a", "pcm_s16le",
                "-ar", "44100",
                self.raw_filename,
            ]
        else:
            logger.error("Unsupported OS for native capture")
            return False

        logger.debug(f"Capture command: {' '.join(command)}")

        # Start the capture process
        self.process = subprocess.Popen(
            command,
            cwd=helpers.get_cwd(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            bufsize=0,
            universal_newlines=True,
            creationflags=subprocess.CREATE_NO_WINDOW if helpers.os_is_windows() else 0,
        )

        # Wait for FFmpeg to start capturing
        offset = helpers.get_timestamp("FFmpeg capture starting")
        for line in self.process.stdout:
            logger.debug(line.strip())
            # Check if FFmpeg has started capturing
            if "Output #0" in line:
                self.start_time = helpers.get_timestamp("FFmpeg capture started")
                break
        
        if not self.start_time:
            logger.error("Failed to start FFmpeg capture")
            helpers.show_popup(
                helpers.get_config("APP_NAME"),
                "Unable to start screen recording - YOU MAY NOT BE COMPATIBLE.",
                16
            )
            return False

        self.startup_delay = self.start_time - offset
        logger.info(f"Capture started successfully (startup delay: {self.startup_delay}ms)")

        return True

    def stop(self):
        """
        Stop capturing and encode the raw video to the final format.
        
        :return: True if capture stopped and encoding succeeded, False otherwise.
        """
        if not self.process:
            logger.error("No capture process to stop")
            return False
        
        logger.info("Stopping video capture...")
        
        # Send 'q' to FFmpeg to gracefully stop
        try:
            offset = helpers.get_timestamp("FFmpeg capture stopping")
            self.process.stdin.write("q")
            self.process.stdin.flush()
            self.process.communicate(timeout=10)
            self.process.wait(timeout=10)
            self.end_time = helpers.get_timestamp("FFmpeg capture ended")
            self.ended_delay = self.end_time - offset
            logger.info(f"Capture stopped successfully (shutdown delay: {self.ended_delay}ms)")
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg did not stop gracefully, terminating...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.error("FFmpeg did not terminate, killing...")
                self.process.kill()
                self.process.wait()
        
        # Check if raw file was created
        if not os.path.exists(self.raw_filename):
            logger.error(f"Raw capture file not found: {self.raw_filename}")
            return False
        
        raw_size = os.path.getsize(self.raw_filename)
        logger.info(f"Raw capture size: {raw_size / (1024*1024):.2f} MB")
        
        # Encode the raw video to final format
        logger.info("Encoding raw capture to final format...")
        encode_success = helpers.encode_video(
            input_path=self.raw_filename,
            output_path=self.filename,
            width=self.width,
            height=self.height,
            crf=23,  # Good quality (same as before)
            preset="medium"  # Balanced preset for good quality/speed
        )
        
        if not encode_success:
            logger.error("Failed to encode raw capture to final format")
            # Keep the raw file for debugging
            logger.warning(f"Raw capture preserved at: {self.raw_filename}")
            return False
        
        # Clean up the raw file after successful encoding
        try:
            os.remove(self.raw_filename)
            logger.info(f"Cleaned up temporary raw file: {self.raw_filename}")
        except Exception as e:
            logger.warning(f"Could not remove temporary raw file: {e}")
        
        final_size = os.path.getsize(self.filename)
        logger.info(f"Final encoded size: {final_size / (1024*1024):.2f} MB")
        logger.info(f"Encoding complete: {self.filename}")
        
        return True

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()