"""Opt-in native recording test for the CaptureKit backend.

This runs the real recording workflow (``RecordingService.run``) against the
bundled Chromium, CaptureKit and FFmpeg. Flash and a Wrapper server are not
required: a stand-in ``player`` page implements the template's play/pause,
scene duration and start/stop signals, flashes white and plays a 1 kHz beep at
a known time. The decoded output is checked for resolution, frame rate,
duration and audio/video alignment.

Run with ``GOEXPORT_NATIVE_CAPTURE_TESTS=1``. It opens a fullscreen browser
window (Windows) or a private Xvfb display (Linux).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from array import array
from pathlib import Path
from unittest.mock import patch

from goexport import config
from goexport.reporting import Reporter
from goexport.services.recorder import RecordingService

ENABLED = os.environ.get("GOEXPORT_NATIVE_CAPTURE_TESTS") == "1"
DURATION_MS = 3000
FLASH_MS = 1000
FLASH_LENGTH_MS = 250
# 24 fps frames are 41.7 ms; allow two frames of capture/presentation latency.
SYNC_TOLERANCE_S = 0.1
# Pre-roll (resume -> play round trip) plus stop detection (<= 50 ms poll).
DURATION_TOLERANCE_S = 0.2

PAGE = """<!doctype html>
<html><head><meta charset="UTF-8"><title>{{WINDOW_TITLE}}</title>
<style>*{margin:0;padding:0}html,body{width:100%;height:100%;background:#000;
overflow:hidden}</style>
<script>
var DURATION = {{DURATION_MS}}, FLASH_AT = {{FLASH_MS}}, FLASH_LEN = {{FLASH_LEN}};
var audio = null;
function unlockAudio() {
    audio = new (window.AudioContext || window.webkitAudioContext)();
    audio.resume();
}
var player = {
    pause: function () {},
    getSceneInfoArray: function () { return [{duration: DURATION / 1000}]; },
    play: function () {
        var t0 = performance.now();
        if (audio) {
            var osc = audio.createOscillator(), gain = audio.createGain();
            osc.frequency.value = 1000;
            gain.gain.value = 0.5;
            osc.connect(gain);
            gain.connect(audio.destination);
            var at = audio.currentTime + FLASH_AT / 1000;
            osc.start(at);
            osc.stop(at + FLASH_LEN / 1000);
        }
        function tick(now) {
            var t = now - t0;
            document.body.style.background =
                t >= FLASH_AT && t < FLASH_AT + FLASH_LEN ? '#fff' : '#000';
            if (t >= DURATION) { window.stopRecord = 1; return; }
            requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    }
};
window.startRecord = 1;
</script></head><body onclick="unlockAudio()"></body></html>
"""


def _ffmpeg(*args):
    return subprocess.run(
        [str(config.FFMPEG_PATH), "-hide_banner", "-nostdin", *args],
        capture_output=True,
        check=False,
    )


def _probe(path):
    return _ffmpeg("-i", str(path)).stderr.decode(errors="replace")


def _gray_frames(path, width=32, height=18):
    raw = _ffmpeg(
        "-v", "error", "-i", str(path), "-map", "0:v:0",
        "-vf", f"scale={width}:{height}", "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ).stdout  # fmt: skip
    size = width * height
    return [sum(raw[i : i + size]) / size for i in range(0, len(raw) - size + 1, size)]


def _mono_samples(path, rate=48_000):
    raw = _ffmpeg(
        "-v", "error", "-i", str(path), "-map", "0:a:0",
        "-ac", "1", "-ar", str(rate), "-f", "s16le", "-",
    ).stdout  # fmt: skip
    samples = array("h")
    samples.frombytes(raw[: len(raw) // 2 * 2])
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


@unittest.skipUnless(ENABLED, "set GOEXPORT_NATIVE_CAPTURE_TESTS=1 to run")
@unittest.skipUnless(
    config.SYSTEM in {"Windows", "Linux"}, "CaptureKit supports Windows and Linux"
)
class CaptureKitNativeRecordingTests(unittest.TestCase):
    def setUp(self):
        for path in (config.CHROME_PATH, config.CHROMEDRIVER_PATH, config.FFMPEG_PATH):
            if not Path(path).is_file():
                self.skipTest(f"runtime dependency missing: {path}")
        import capturekit

        # On Linux the recording creates its own Xvfb display; only audio
        # capabilities are meaningful before that display exists.
        caps = capturekit.get_capabilities(
            os.environ.get("DISPLAY") if config.SYSTEM == "Linux" else None
        )
        if config.SYSTEM == "Windows" and not caps.window_capture:
            self.skipTest(f"window capture unavailable: {caps.window_capture.reason}")
        self.process_audio = bool(caps.process_audio)

    def record(self, directory, video_format, *, audio, outro=False):
        output = Path(directory) / f"capture test.{video_format}"
        args = Namespace(
            output=output,
            format=video_format,
            url="about:blank",
            resolution=(640, 360),
            capture_backend="capturekit",
            capturekit_audio=audio,
            capturekit_encoder="auto",
            no_outro=not outro,
            use_outro=config.OUTRO_PATH,
            no_flash_timeout=False,
            electron=False,
            ffmpeg_path=config.FFMPEG_PATH,
            json=False,
        )
        service = RecordingService(args)
        service.reporter = Reporter()
        backends = []
        create_backend = service._create_backend

        def keep_backend(name):
            backend = create_backend(name)
            backends.append(backend)
            return backend

        page = (
            PAGE.replace("{{WINDOW_TITLE}}", service._capture_window_title)
            .replace("{{DURATION_MS}}", str(DURATION_MS))
            .replace("{{FLASH_MS}}", str(FLASH_MS))
            .replace("{{FLASH_LEN}}", str(FLASH_LENGTH_MS))
        )
        page_path = Path(directory) / "player.html"
        page_path.write_text(page, encoding="utf-8")

        def stand_in_setup(browser, driver):
            browser.enter_fullscreen(driver)
            browser.validate_screen_resolution(driver)
            browser.assert_full_resolution()
            browser.inject_dom(driver, page_path)
            # A WebDriver click is a user gesture, which Chromium's autoplay
            # policy requires before an AudioContext may produce sound.
            from selenium.webdriver.common.by import By

            driver.find_element(By.TAG_NAME, "body").click()

        with (
            patch.object(service, "_create_backend", side_effect=keep_backend),
            patch.object(service, "_finish_browser_setup", side_effect=stand_in_setup),
        ):
            self.assertEqual(service.run(), 0)
        self.assertTrue(output.is_file())
        self.assertFalse(output.with_name(f"{output.stem}.video.mkv").exists())
        return output, backends[0]

    def assert_stream_format(self, output, width, height):
        info = _probe(output)
        self.assertRegex(info, rf"Video: h264.*\b{width}x{height}\b")
        self.assertRegex(info, r"\b24 fps\b")
        self.assertRegex(info, r"Audio: aac")

    def test_mp4_window_capture_is_cropped_timed_and_synchronized(self):
        audio = "process" if self.process_audio else "none"
        with tempfile.TemporaryDirectory() as directory:
            output, backend = self.record(directory, "mp4", audio=audio)
            self.assertEqual(output.read_bytes()[4:8], b"ftyp")
            self.assert_stream_format(output, 640, 360)
            self.assertEqual(backend.video_source.region.size, (640, 360))
            self.assertTrue(backend.video_source.client_area_only)
            if config.SYSTEM == "Linux":
                self.assertEqual(backend.window.display, backend.display)

            frames = _gray_frames(output)
            duration = len(frames) / config.FPS
            print(f"\n[native] decoded {len(frames)} frames = {duration:.3f}s")
            self.assertAlmostEqual(
                duration, DURATION_MS / 1000, delta=DURATION_TOLERANCE_S
            )
            bright = [index for index, value in enumerate(frames) if value > 128]
            self.assertTrue(bright, "the white flash was not captured")
            video_onset = bright[0] / config.FPS
            print(f"[native] video flash at {video_onset:.3f}s")
            self.assertAlmostEqual(video_onset, FLASH_MS / 1000, delta=0.15)
            self.assertTrue(all(value < 32 for value in frames[: bright[0]]))

            if audio != "process":
                print("[native] process audio unavailable; audio checks skipped")
                return
            samples = _mono_samples(output)
            threshold = int(0.1 * 32767)
            loud = [i for i, value in enumerate(samples) if abs(value) > threshold]
            self.assertTrue(loud, "the beep was not captured")
            audio_onset = loud[0] / 48_000
            print(
                f"[native] audio beep at {audio_onset:.3f}s "
                f"(A-V {1000 * (audio_onset - video_onset):+.0f} ms)"
            )
            self.assertAlmostEqual(audio_onset, video_onset, delta=SYNC_TOLERANCE_S)
            beep = (loud[-1] - loud[0]) / 48_000
            self.assertAlmostEqual(beep, FLASH_LENGTH_MS / 1000, delta=0.05)

    def test_mov_with_outro_and_mkv_without_audio(self):
        audio = "process" if self.process_audio else "none"
        with tempfile.TemporaryDirectory() as directory:
            output, _ = self.record(directory, "mov", audio=audio, outro=True)
            self.assertEqual(output.read_bytes()[4:8], b"ftyp")
            self.assert_stream_format(output, 640, 360)
            hours, minutes, seconds = re.search(
                r"Duration: (\d+):(\d+):([\d.]+)", _probe(config.OUTRO_PATH)
            ).groups()
            outro_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            outro = round(outro_seconds * config.FPS)
            frames = len(_gray_frames(output))
            self.assertAlmostEqual(
                frames, DURATION_MS * config.FPS // 1000 + outro, delta=6
            )

            silent, backend = self.record(directory, "mkv", audio="none")
            self.assertEqual(silent.read_bytes()[:4], b"\x1aE\xdf\xa3")
            self.assertEqual(backend.audio_sources, ())
            self.assert_stream_format(silent, 640, 360)
            self.assertFalse(any(_mono_samples(silent)))


if __name__ == "__main__":
    unittest.main()
