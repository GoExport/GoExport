import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from goexport import config
from goexport.services.asset_resolver import AssetResolver
from goexport.services.ffmpeg import (
    FFmpegAudioEncoder,
    FFmpegMuxer,
    FFmpegRawVideoEncoder,
)


@unittest.skipUnless(config.FFMPEG_PATH.is_file(), "Bundled FFmpeg is not installed")
class FFmpegIntegrationTests(unittest.TestCase):
    def create_video(self, path):
        encoder = FFmpegRawVideoEncoder(config.FFMPEG_PATH, path, 16, 16, 16, 16)
        try:
            for _ in range(24):
                encoder.write_frame(bytes([0, 0, 255, 255]) * 16 * 16)
        finally:
            encoder.close()

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
