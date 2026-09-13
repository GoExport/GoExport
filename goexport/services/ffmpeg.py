from __future__ import annotations

import logging
from pathlib import Path
import subprocess
import tempfile

from goexport.models.audio_clip import AudioClip
from goexport.services.asset_resolver import AssetResolver

logger = logging.getLogger(__name__)


class FFmpegError(RuntimeError):
    """An FFmpeg process failed; its command and diagnostic tail are included."""


class _PipeEncoder:
    """FFmpeg stdin encoder using a file-backed stderr sink, avoiding pipe deadlocks."""
    def __init__(self, command: list[str]):
        self.command = command
        self._stderr = tempfile.TemporaryFile(mode="w+b")
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=self._stderr, bufsize=0)

    def _failure(self) -> FFmpegError:
        self._stderr.seek(0)
        tail = self._stderr.read().decode(errors="replace")[-4000:]
        return FFmpegError(f"FFmpeg failed (exit {self.process.returncode}): {' '.join(self.command)}\nstderr tail:\n{tail}")

    def write_frame(self, data: bytes) -> None:
        if self.process.stdin is None:
            raise FFmpegError("FFmpeg stdin is unavailable: " + " ".join(self.command))
        try:
            self.process.stdin.write(data)
        except BrokenPipeError as exc:
            self.process.wait()
            raise self._failure() from exc

    def close(self) -> None:
        if self.process.stdin is not None and not self.process.stdin.closed:
            try:
                self.process.stdin.close()
            except BrokenPipeError:
                pass
        self.process.wait()
        if self.process.returncode:
            raise self._failure()
        self._stderr.close()


class FFmpegVideoEncoder(_PipeEncoder):
    def __init__(self, ffmpeg_path: str | Path, output_file: str | Path, width: int, height: int, fps: int = 24):
        super().__init__([str(ffmpeg_path), "-y", "-f", "image2pipe", "-framerate", str(fps), "-vcodec", "png", "-i", "-", "-vf", f"crop={width}:{height}:0:0,pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium", str(output_file)])


class FFmpegRawVideoEncoder(_PipeEncoder):
    def __init__(self, ffmpeg_path: Path, output_file: Path, width: int, height: int, output_width: int, output_height: int, fps: int = 24):
        if output_width > width or output_height > height:
            raise ValueError(f"Capture {width}x{height} is smaller than requested output {output_width}x{output_height}")
        super().__init__([str(ffmpeg_path), "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{width}x{height}", "-framerate", str(fps), "-i", "-", "-vf", f"crop={output_width}:{output_height}:0:0,pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium", str(output_file)])


class FFmpegRawAudioEncoder(_PipeEncoder):
    def __init__(self, ffmpeg_path: Path, output_file: Path, channels: int, sample_rate: int, sample_format: str):
        super().__init__([str(ffmpeg_path), "-y", "-f", sample_format, "-ar", str(sample_rate), "-ac", str(channels), "-i", "-", "-c:a", "pcm_s16le", str(output_file)])


class FFmpegAudioEncoder:
    def __init__(self, ffmpeg_path: Path, resolver: AssetResolver, fps: int = 24, audio_offset_frames: int = 0):
        self.ffmpeg_path, self.resolver, self.fps = ffmpeg_path, resolver, fps
        self.audio_offset_frames = audio_offset_frames

    def encode(self, clips: list[AudioClip], output_file: Path, frame_count: int) -> None:
        duration = frame_count / self.fps
        command = [str(self.ffmpeg_path), "-y"]
        if not clips:
            subprocess.run(command + ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{duration:.6f}", "-c:a", "pcm_s16le", str(output_file)], check=True)
            return
        filters, inputs = [], []
        explicit_offset_ms = round(self.audio_offset_frames * 1000 / self.fps)
        for i, clip in enumerate(clips):
            command += ["-i", str(self.resolver.resolve(clip.asset_id))]
            delay = round((clip.start_frame - 1) * 1000 / self.fps) + explicit_offset_ms
            source = (f"atrim=start={clip.trim_start_frame / self.fps:.6f}:end={min(clip.trim_end_frame, clip.trim_start_frame + clip.duration_frames) / self.fps:.6f}" if clip.has_trim else f"atrim=end={clip.duration_frames / self.fps:.6f}")
            filters.append(f"[{i}:a]{source},adelay={delay}|{delay}[a{i}]"); inputs.append(f"[a{i}]")
        filters.append("".join(inputs) + f"amix=inputs={len(clips)}:normalize=0,atrim=end={duration:.6f}")
        subprocess.run(command + ["-filter_complex", ";".join(filters), "-c:a", "pcm_s16le", str(output_file)], check=True)


class FFmpegMuxer:
    def __init__(self, ffmpeg_path: Path): self.ffmpeg_path = ffmpeg_path
    def _run(self, command: list[str]) -> None:
        logger.info("FFmpeg command: %s", " ".join(command)); subprocess.run(command, check=True)
    def mux(self, video_file: Path, audio_file: Path, output_file: Path) -> None:
        self._run([str(self.ffmpeg_path), "-y", "-i", str(video_file), "-i", str(audio_file), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(output_file)])
        video_file.unlink(missing_ok=True); audio_file.unlink(missing_ok=True)
    def append_outro(self, main_video_file: Path, outro_file: Path, output_file: Path, width: int, height: int, fps: int = 24) -> None:
        if not main_video_file.is_file() or not outro_file.is_file(): raise FileNotFoundError("Main video or outro does not exist")
        temp = output_file.with_name(f"{output_file.stem}.with_outro{output_file.suffix}")
        self._run([str(self.ffmpeg_path), "-y", "-i", str(main_video_file), "-i", str(outro_file), "-filter_complex", f"[0:v]fps={fps},setpts=N/({fps}*TB)[a];[1:v]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps},setpts=N/({fps}*TB)[b];[a][0:a][b][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(temp)])
        temp.replace(output_file)
