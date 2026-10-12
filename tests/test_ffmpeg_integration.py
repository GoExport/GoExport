import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from goexport import config
from goexport.services.asset_resolver import AssetResolver
from goexport.services.ffmpeg import (
    FFmpegAudioEncoder,
    FFmpegError,
    FFmpegMuxer,
)


@unittest.skipUnless(config.FFMPEG_PATH.is_file(), "Bundled FFmpeg is not installed")
class FFmpegIntegrationTests(unittest.TestCase):
    def create_video(self, path, frames=24, audio=False):
        # Matches a CaptureKit intermediate: H.264 video with B-frames and,
        # optionally, PCM audio exactly as long as the video.
        command = [
            str(config.FFMPEG_PATH), "-v", "error", "-y",
            "-f", "lavfi", "-i", "color=c=red:s=16x16:r=24",
        ]  # fmt: skip
        if audio:
            command += ["-f", "lavfi", "-i", "sine=r=48000"]
            command += ["-t", f"{frames / 24:.6f}", "-c:a", "pcm_s16le"]
        command += [
            "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(path),
        ]  # fmt: skip
        subprocess.run(command, check=True, capture_output=True)

    def assert_decodable(self, path, frames):
        result = subprocess.run(
            [
                str(config.FFMPEG_PATH),
                "-v",
                "error",
                "-i",
                str(path),
                "-map",
                "0:v:0",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "bgra",
                "-",
            ],
            capture_output=True,
            check=True,
        )
        self.assertEqual(len(result.stdout), frames * 16 * 16 * 4)
        subprocess.run(
            [
                str(config.FFMPEG_PATH),
                "-v",
                "error",
                "-i",
                str(path),
                "-map",
                "0:a:0",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            check=True,
        )

    def test_recording_without_audio_supports_every_container(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for video_format in sorted(config.SUPPORTED_FORMATS):
                with self.subTest(video_format=video_format):
                    video = root / "video.mkv"
                    output = root / f"output.{video_format}"
                    self.create_video(video)
                    FFmpegMuxer(config.FFMPEG_PATH).mux(video, None, output)
                    self.assert_decodable(output, 24)
                    self.assertFalse(video.exists())
                    if video_format in {"mp4", "mov"}:
                        self.assertEqual(output.read_bytes()[4:8], b"ftyp")
                    else:
                        self.assertEqual(output.read_bytes()[:4], b"\x1aE\xdf\xa3")

    def test_export_silent_timeline_and_mux(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video, audio, output = (
                root / "video.mkv",
                root / "audio.wav",
                root / "out.mp4",
            )
            self.create_video(video)
            encoder = FFmpegAudioEncoder(config.FFMPEG_PATH, AssetResolver(root, root))
            encoder.encode([], audio, 24)
            with wave.open(str(audio)) as stream:
                self.assertEqual(stream.getnframes(), 44100)
            FFmpegMuxer(config.FFMPEG_PATH).mux(video, audio, output)
            self.assert_decodable(output, 24)
            self.assertFalse(audio.exists())

    def test_combined_obs_recording_is_finalized(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "video.mkv"
            audio = root / "audio.wav"
            combined = root / "obs.mkv"
            output = root / "output.mp4"
            self.create_video(video)
            FFmpegAudioEncoder(config.FFMPEG_PATH, AssetResolver(root, root)).encode(
                [], audio, 24
            )
            FFmpegMuxer(config.FFMPEG_PATH).mux(video, audio, combined)
            FFmpegMuxer(config.FFMPEG_PATH).mux_combined(combined, output)
            self.assert_decodable(output, 24)
            self.assertFalse(combined.exists())

    def test_combined_recording_keeps_every_video_frame(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for video_format in sorted(config.SUPPORTED_FORMATS):
                with self.subTest(video_format=video_format):
                    combined = root / "capture.video.mkv"
                    output = root / f"output.{video_format}"
                    self.create_video(combined, frames=74, audio=True)
                    muxer = FFmpegMuxer(config.FFMPEG_PATH)
                    self.assertEqual(muxer.audio_stream_count(combined), 1)
                    muxer.mux_combined(combined, output, has_audio=True)
                    self.assert_decodable(output, 74)
                    self.assertFalse(combined.exists())

    def test_combined_recording_without_audio_gets_silent_track(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            combined, output = root / "capture.video.mkv", root / "output.mp4"
            self.create_video(combined, frames=30)
            muxer = FFmpegMuxer(config.FFMPEG_PATH)
            self.assertEqual(muxer.audio_stream_count(combined), 0)
            muxer.mux_combined(combined, output, has_audio=False)
            self.assert_decodable(output, 30)

    def test_combined_recording_missing_expected_audio_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            combined = root / "capture.video.mkv"
            self.create_video(combined)
            with self.assertRaisesRegex(FFmpegError, "no audio stream"):
                FFmpegMuxer(config.FFMPEG_PATH).mux_combined(
                    combined, root / "output.mp4", has_audio=True
                )
            self.assertTrue(combined.exists())

    def test_unreadable_recording_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            broken = Path(temp) / "broken.mkv"
            broken.write_bytes(b"not a video")
            with self.assertRaisesRegex(FFmpegError, "could not read"):
                FFmpegMuxer(config.FFMPEG_PATH).audio_stream_count(broken)

    def test_outro_can_replace_main_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            muxer = FFmpegMuxer(config.FFMPEG_PATH)
            main, outro = root / "main.mp4", root / "outro.mp4"
            for output in (main, outro):
                video = root / "video.mkv"
                self.create_video(video)
                muxer.mux(video, None, output)
            muxer.append_outro(main, outro, main, 16, 16)
            self.assert_decodable(main, 48)
            self.assertFalse((root / "main.with_outro.mp4").exists())
