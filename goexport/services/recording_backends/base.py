"""Data contract and lifecycle shared by recording capture engines.

``RecordingService`` drives every backend through the same lifecycle::

    check_available(display) -> prepare(service, driver, artifacts) -> start()
    -> before_playback() -> [player.play()] -> capture_until_stopped(...)
    -> close()                      (stop() is only used for failure cleanup)

``start`` may perform slow setup (encoder probing, native session start);
``before_playback`` runs immediately before ``player.play()`` and must be
cheap, so the recorded timeline begins as close to playback as possible.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# The recording stage owns this part of the progress range; 85-99 is reserved
# for muxing, outro processing and finalization.
RECORDING_PROGRESS_START = 5
RECORDING_PROGRESS_END = 84


@dataclass(frozen=True)
class CaptureArtifacts:
    video: Path
    audio: Path
    obs_directory: Path


@dataclass(frozen=True)
class CaptureResult:
    video: Path
    audio: Path | None
    audio_is_muxed: bool = False
    owned_paths: tuple[Path, ...] = ()
    # For muxed recordings: True when the backend recorded an audio track,
    # False when it deliberately recorded none, None when unknown (probe it).
    has_audio: bool | None = None


class RecordingBackend(Protocol):
    def check_available(self, display: str | None = None) -> None: ...

    def prepare(self, service, driver, artifacts: CaptureArtifacts) -> None: ...

    def start(self) -> None: ...

    def before_playback(self) -> None: ...

    def capture_until_stopped(
        self,
        started: threading.Event,
        stopped: threading.Event,
        total_duration_ns: int,
    ) -> CaptureResult: ...

    def stop(self) -> CaptureResult | None: ...

    def close(self) -> None: ...


def recording_progress(elapsed_ns: int, total_duration_ns: int) -> int:
    """Whole percentage of the movie recorded so far, clamped to 0-100."""
    if total_duration_ns <= 0:
        return 0
    return int(max(0, min(100, elapsed_ns * 100 / total_duration_ns)))


def report_recording_progress(reporter, elapsed_ns: int, total_duration_ns: int):
    percent = recording_progress(elapsed_ns, total_duration_ns)
    span = RECORDING_PROGRESS_END - RECORDING_PROGRESS_START
    reporter.progress(RECORDING_PROGRESS_START + percent * span / 100, "recording")
