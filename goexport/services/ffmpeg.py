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
        width: int,
        height: int,
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
                "-vf", f"crop={width}:{height}:0:0,pad=ceil(iw/2)*2:ceil(ih/2)*2",
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


class FFmpegRawVideoEncoder:
    def __init__(
        self,
        ffmpeg_path: Path,
        output_file: Path,
        width: int,
        height: int,
        output_width: int,
        output_height: int,
        fps: int = 24,
    ):
        self.process = subprocess.Popen(
            [
                str(ffmpeg_path),
                "-y",
                "-f", "rawvideo",
                "-pix_fmt", "bgra",
                "-s", f"{width}x{height}",
                "-framerate", str(fps),
                "-i", "-",
                "-vf", (
                    f"crop={output_width}:{output_height}:0:0,"
                    "pad=ceil(iw/2)*2:ceil(ih/2)*2"
                ),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "18",
                "-preset", "medium",
                str(output_file),
            ],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )

    def write_frame(self, frame_data: bytes) -> None:
        self.process.stdin.write(frame_data)

    def close(self) -> None:
        self.process.stdin.close()
        self.process.wait()


class FFmpegRawAudioEncoder:
    def __init__(
        self,
        ffmpeg_path: Path,
        output_file: Path,
        channels: int,
        sample_rate: int,
        sample_format: str,
    ):
        self.process = subprocess.Popen(
            [
                str(ffmpeg_path),
                "-y",
                "-f", sample_format,
                "-ar", str(sample_rate),
                "-ac", str(channels),
                "-i", "-",
                "-c:a", "pcm_s16le",
                str(output_file),
            ],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )

    def write_frame(self, frame_data: bytes) -> None:
        self.process.stdin.write(frame_data)

    def close(self) -> None:
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
        frame_count: int,
    ) -> None:
        movie_duration = frame_count / self.fps

        if not clips:
            # Keep muxing stable by emitting a silent track when no clips exist.
            command = [
                str(self.ffmpeg_path),
                "-y",
                "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
                "-t", f"{max(movie_duration, 0):.6f}",
                "-c:a", "pcm_s16le",
                str(output_file),
            ]

            logger.info(
                "No audio clips found; generating silent track (%s seconds)",
                f"{max(movie_duration, 0):.6f}",
            )
            logger.info("FFmpeg command: %s", " ".join(command))

            subprocess.run(
                command,
                check=True,
            )
            return

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
                clip_duration = (
                    clip.duration_frames / self.fps
                )

                filter_chain = (
                    f"[{index}:a]"
                    f"atrim=end={clip_duration:.6f},"
                    f"adelay={delay}|{delay}"
                    f"[a{index}]"
                )

            filters.append(filter_chain)
            mix_inputs.append(f"[a{index}]")

        filters.append(
            "".join(mix_inputs)
            + (
                f"amix=inputs={len(clips)}:normalize=0,"
                f"adelay={offset_ms}|{offset_ms},"
                f"atrim=end={movie_duration:.6f}"
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

    def _has_audio_stream(self, media_file: Path) -> bool:
        ffprobe_path = self.ffmpeg_path.with_name(
            f"ffprobe{self.ffmpeg_path.suffix}"
        )
        result = subprocess.run(
            [
                str(ffprobe_path),
                "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=index",
                "-of", "csv=p=0",
                str(media_file),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return bool(result.stdout.strip())

    def duration(self, media_file: Path) -> float:
        ffprobe_path = self.ffmpeg_path.with_name(
            f"ffprobe{self.ffmpeg_path.suffix}"
        )
        result = subprocess.run(
            [
                str(ffprobe_path),
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                str(media_file),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())

    def stretch_video_to_duration(
        self,
        video_file: Path,
        duration: float,
        fps: int = 24,
    ) -> None:
        current_duration = self.duration(video_file)
        if current_duration <= 0 or duration <= 0:
            return

        temp_output_file = video_file.with_name(
            f"{video_file.stem}.timed{video_file.suffix}"
        )
        command = [
            str(self.ffmpeg_path),
            "-y",
            "-i", str(video_file),
            "-vf", f"setpts=PTS*{duration / current_duration:.9f}",
            "-r", str(fps),
            "-fps_mode", "cfr",
            "-an",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "medium",
            str(temp_output_file),
        ]
        logger.info("FFmpeg command: %s", " ".join(command))
        subprocess.run(command, check=True)
        temp_output_file.replace(video_file)

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

        # Clean up temporary files
        video_file.unlink(missing_ok=True)
        audio_file.unlink(missing_ok=True)

    def append_outro(
        self,
        main_video_file: Path,
        outro_file: Path,
        output_file: Path,
        width: int,
        height: int,
        fps: int = 24,
    ) -> None:
        if output_file.suffix.lower() == ".gif":
            raise ValueError(
                "Appending an outro with audio is not supported for GIF output. "
                "Use --no-outro or choose a different output format."
            )

        if not main_video_file.is_file():
            raise FileNotFoundError(
                f"Main video file does not exist: {main_video_file}"
            )

        if not outro_file.is_file():
            raise FileNotFoundError(
                f"Outro video file does not exist: {outro_file}"
            )

        temp_output_file = output_file.with_name(
            f"{output_file.stem}.with_outro{output_file.suffix}"
        )

        main_has_audio = self._has_audio_stream(main_video_file)
        outro_has_audio = self._has_audio_stream(outro_file)
        input_files = [
            ("-i", str(main_video_file)),
            ("-i", str(outro_file)),
        ]
        main_audio = "[0:a]"
        outro_audio = "[1:a]"

        if not main_has_audio:
            input_files.extend([
                ("-f", "lavfi"),
                ("-t", f"{self.duration(main_video_file):.6f}"),
                ("-i", "anullsrc=r=44100:cl=stereo"),
            ])
            main_audio = "[2:a]"

        if not outro_has_audio:
            input_files.extend([
                ("-f", "lavfi"),
                ("-t", f"{self.duration(outro_file):.6f}"),
                ("-i", "anullsrc=r=44100:cl=stereo"),
            ])
            outro_audio = "[3:a]" if not main_has_audio else "[2:a]"

        # Normalize both inputs before concat.  In particular, concat otherwise
        # retains the input timestamps, which can result in a fractional average
        # frame rate after the outro is attached.
        filter_complex = (
            f"[0:v]fps={fps},settb=AVTB,setpts=N/({fps}*TB)[main_v];"
            f"[1:v]"
            f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease,"
            f"pad=w={width}:h={height}:x=(ow-iw)/2:y=(oh-ih)/2:color=black,"
            f"fps={fps},settb=AVTB,setpts=N/({fps}*TB)"
            f"[outro_v];"
            f"[main_v]{main_audio}[outro_v]{outro_audio}"
            f"concat=n=2:v=1:a=1[v][a]"
        )

        command = [
            str(self.ffmpeg_path),
            *[value for pair in input_files for value in pair],
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-fps_mode", "cfr",
            "-c:a", "aac",
            "-b:a", "192k",
            str(temp_output_file),
        ]

        logger.info("FFmpeg command: %s", " ".join(command))

        subprocess.run(
            command,
            check=True,
        )

        temp_output_file.replace(output_file)
