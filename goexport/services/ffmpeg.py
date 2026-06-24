import subprocess


class FFmpegEncoder:
    def __init__(
        self,
        ffmpeg_path: str,
        output_file: str,
        fps: int = 24,
    ):
        self.process = subprocess.Popen(
            [
                ffmpeg_path,
                "-y",
                "-f", "image2pipe",
                "-framerate", str(fps),
                "-vcodec", "png",
                "-i", "-",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "18",
                "-preset", "medium",
                output_file,
            ],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )

    def write_frame(self, png_bytes):
        self.process.stdin.write(png_bytes)

    def close(self):
        self.process.stdin.close()
        self.process.wait()