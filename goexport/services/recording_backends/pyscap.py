"""The existing timestamped PyScap recorder behind the backend boundary."""

from __future__ import annotations

import logging

from goexport import config
from goexport.services.capture import (
    VideoSelector,
    audio_padding_samples,
    audio_trim_samples,
    configure_backend,
    create_capturer,
    timestamp_ns,
)
from goexport.services.ffmpeg import FFmpegRawAudioEncoder, FFmpegRawVideoEncoder
from goexport.services.recording_backends.base import CaptureArtifacts, CaptureResult

logger = logging.getLogger(__name__)

_AUDIO_FORMATS = {
    "int8": ("s8", 1),
    "int16": ("s16le", 2),
    "int32": ("s32le", 4),
    "int64": ("s64le", 8),
    "uint8": ("u8", 1),
    "uint16": ("u16le", 2),
    "uint32": ("u32le", 4),
    "uint64": ("u64le", 8),
    "float32": ("f32le", 4),
    "float64": ("f64le", 8),
}


def recording_progress(timestamp: int, origin: int, total_duration: int) -> int:
    if total_duration <= 0:
        return 0
    return int(max(0, min(100, (timestamp - origin) * 100 / total_duration)))


class PyScapBackend:
    def __init__(self, args, reporter, ffmpeg_path, window_title, **_kwargs):
        self.args = args
        self.reporter = reporter
        self.ffmpeg_path = ffmpeg_path
        self.window_title = window_title
        self.capturer = None
        self.artifacts = None
        self._audio_aligned = False

    def check_available(self, display=None):
        configure_backend(display)
        import scap

        if not scap.is_supported():
            raise RuntimeError("This platform does not support screen capture")
        if not scap.has_permission() and not scap.request_permission():
            raise PermissionError("Screen-capture permission was denied")

    def prepare(self, service, driver, artifacts: CaptureArtifacts):
        self.artifacts = artifacts
        target = service.get_capture_target(driver)
        crop_area = service.get_capture_crop_area(driver)
        self.capturer = create_capturer(target, crop_area, service.capture_display)

    def start(self):
        if self.capturer is None:
            raise RuntimeError("PyScap backend was not prepared")
        self.capturer.start()

    def capture_until_stopped(self, started, stopped, total_duration_ns):
        import scap

        if self.capturer is None or self.artifacts is None:
            raise RuntimeError("PyScap backend was not prepared")
        video = audio = None
        selector = VideoSelector(config.FPS)
        video_origin = audio_origin = None
        pending = []
        boundary = None
        try:
            while True:
                frame = self.capturer.next_frame()
                if not started.is_set():
                    continue
                now = timestamp_ns(frame.timestamp)
                if stopped.is_set() and boundary is None:
                    boundary = now
                if boundary is not None and now > boundary:
                    break
                if isinstance(frame, scap.VideoFrameInfo):
                    if frame.format not in {"bgra", "bgr0"}:
                        raise RuntimeError(
                            f"unsupported scap video format: {frame.format}"
                        )
                    if video is None:
                        video = FFmpegRawVideoEncoder(
                            self.ffmpeg_path,
                            self.artifacts.video,
                            frame.width,
                            frame.height,
                            *self.args.resolution,
                            config.FPS,
                        )
                    if video_origin is None:
                        video_origin = now
                    for data in selector.add(now, frame.data.tobytes()):
                        video.write_frame(data)
                    for item, stamp in pending:
                        self._write_audio(item, stamp, video_origin, audio, boundary)
                    pending.clear()
                elif isinstance(frame, scap.AudioFrameInfo):
                    if frame.planar:
                        raise RuntimeError("Planar scap audio is not supported")
                    spec = _AUDIO_FORMATS.get(frame.format)
                    if spec is None:
                        raise RuntimeError(
                            f"unsupported scap audio format: {frame.format}"
                        )
                    if audio is None:
                        audio = FFmpegRawAudioEncoder(
                            self.ffmpeg_path,
                            self.artifacts.audio,
                            frame.channels,
                            frame.rate,
                            spec[0],
                        )
                        self._sample_bytes = spec[1]
                    if audio_origin is None:
                        audio_origin = now
                    if video_origin is None:
                        pending.append((frame, now))
                    else:
                        self._write_audio(frame, now, video_origin, audio, boundary)
                else:
                    raise RuntimeError(f"unexpected scap frame type: {type(frame)!r}")
                if video_origin is not None and total_duration_ns:
                    timeline_percent = recording_progress(
                        now, video_origin, total_duration_ns
                    )
                    self.reporter.progress(5 + timeline_percent * 0.79, "recording")
                if boundary is not None:
                    break
        finally:
            self.stop()
            try:
                if video is not None:
                    try:
                        if boundary is not None:
                            for data in selector.finish(boundary):
                                video.write_frame(data)
                    finally:
                        video.close()
            finally:
                if audio is not None:
                    audio.close()
        if audio_origin is not None and video_origin is not None:
            logger.debug(
                "Initial audio/video offset: %.3f ms",
                (audio_origin - video_origin) / 1_000_000,
            )
        return CaptureResult(
            self.artifacts.video,
            self.artifacts.audio if self.artifacts.audio.is_file() else None,
            owned_paths=(self.artifacts.video, self.artifacts.audio),
        )

    def _write_audio(self, frame, stamp, video_origin, encoder, boundary=None):
        data = frame.data.tobytes()
        offset = stamp - video_origin
        size = frame.channels * self._sample_bytes
        if not self._audio_aligned:
            if offset > 0:
                encoder.write_frame(
                    b"\0" * (audio_padding_samples(offset, frame.rate) * size)
                )
            elif offset < 0:
                data = data[
                    min(len(data), audio_trim_samples(offset, frame.rate) * size) :
                ]
            self._audio_aligned = True
        if boundary is not None:
            allowed = max(
                0,
                min(
                    frame.sample_count,
                    (boundary - stamp) * frame.rate // 1_000_000_000,
                ),
            )
            data = data[: allowed * size]
        if data:
            encoder.write_frame(data)

    def stop(self):
        if self.capturer is not None:
            try:
                self.capturer.stop()
            except Exception:
                logger.debug("capturer.stop failed during cleanup", exc_info=True)

    def close(self):
        self.stop()
