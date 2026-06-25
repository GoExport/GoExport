from pathlib import Path
import subprocess
import logging

from goexport.models.audio_clip import AudioClip
from goexport.services.asset_resolver import AssetResolver

logger = logging.getLogger(__name__)

class FFmpegVideoEncoder:
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



class FFmpegAudioEncoder:
    def __init__(
        self,
        ffmpeg_path: Path,
        resolver: AssetResolver,
        fps: int = 24,
        audio_offset_frames: int = 2,
    ):
        self.ffmpeg_path = ffmpeg_path
        self.resolver = resolver
        self.fps = fps
        self.audio_offset_frames = audio_offset_frames

    def encode(
        self,
        clips: list[AudioClip],
        output_file: Path,
    ) -> None:
        command = [
            str(self.ffmpeg_path),
            "-y",
        ]

        filters = []
        mix_inputs = []

        offset_ms = round(
            self.audio_offset_frames * 1000 / self.fps
        )

        for index, clip in enumerate(clips):
            command.extend([
                "-i",
                str(
                    self.resolver.resolve(
                        clip.asset_id,
                    )
                ),
            ])

            delay = round(
                (clip.start_frame - 1) * 1000 / self.fps
            )

            if clip.has_trim:
                trim_start = (
                    clip.trim_start_frame / self.fps
                )

                trim_end = min(
                    clip.trim_end_frame,
                    clip.trim_start_frame
                    + clip.duration_frames,
                ) / self.fps

                filter_chain = (
                    f"[{index}:a]"
                    f"atrim=start={trim_start:.6f}:"
                    f"end={trim_end:.6f},"
                    f"adelay={delay}|{delay}"
                    f"[a{index}]"
                )
            else:
                duration = (
                    clip.duration_frames / self.fps
                )

                filter_chain = (
                    f"[{index}:a]"
                    f"atrim=end={duration:.6f},"
                    f"adelay={delay}|{delay}"
                    f"[a{index}]"
                )

            filters.append(filter_chain)
            mix_inputs.append(f"[a{index}]")

        filters.append(
            "".join(mix_inputs)
            + (
                f"amix=inputs={len(clips)}:normalize=0,"
                f"adelay={offset_ms}|{offset_ms}"
            )
        )

        command.extend([
            "-filter_complex",
            ";".join(filters),
            "-c:a",
            "pcm_s16le",
            str(output_file),
        ])

        logger.info("FFmpeg command: %s", " ".join(command))

        subprocess.run(
            command,
            check=True,
        )

class FFmpegMuxer:
    def __init__(self, ffmpeg_path: Path):
        self.ffmpeg_path = ffmpeg_path

    def mux(
        self,
        video_file: Path,
        audio_file: Path,
        output_file: Path,
    ) -> None:
        subprocess.run(
            [
                str(self.ffmpeg_path),
                "-y",
                "-i", str(video_file),
                "-i", str(audio_file),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_file),
            ],
            check=True,
        )