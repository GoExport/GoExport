"""PyScap construction and timestamp helpers used by the live recorder.

PyScap timestamps are converted to integer nanoseconds as soon as they enter
GoExport.  The recorder deliberately never compares them with Python clocks.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from goexport import config

NANOSECONDS = 1_000_000_000


def configure_backend() -> None:
    """Select X11 before PyScap initializes its native Linux backend."""
    if config.SYSTEM == "Linux":
        os.environ.setdefault("SCAP_BACKEND", "x11")


def timestamp_ns(timestamp: Any) -> int:
    """Convert PyScap's numeric timestamp to an exact-ish integer duration."""
    return int((Decimal(str(timestamp)) * NANOSECONDS).to_integral_value(ROUND_HALF_UP))


def create_capturer(target: Any, crop_area: tuple[int, int, int, int] | None = None):
    """Create the sole production PyScap capturer (imported lazily for export)."""
    configure_backend()
    import scap

    return scap.Capturer(
        scap.CaptureOptions(
            fps=config.FPS,
            target=target,
            crop_area=crop_area,
            show_cursor=False,
            show_highlight=False,
            output_type="bgra",
            output_resolution="captured",
            captures_audio=True,
        )
    )


def cfr_index(timestamp: int, origin: int, fps: int) -> int:
    """Nearest CFR slot for a capture timestamp; ties round up.

    When multiple captures map to one slot, the one nearest its ideal timestamp
    wins. Slots with no capture repeat the prior selected frame.
    """
    return max(0, ((timestamp - origin) * fps * 2 + NANOSECONDS) // (2 * NANOSECONDS))


def audio_padding_samples(offset_ns: int, rate: int) -> int:
    """Silence required when audio begins after video, rounded to samples."""
    return max(0, (offset_ns * rate + NANOSECONDS // 2) // NANOSECONDS)


def audio_trim_samples(offset_ns: int, rate: int) -> int:
    """Samples to discard when audio begins before video, rounded to samples."""
    return audio_padding_samples(-offset_ns, rate)


def audio_frame_duration_ns(sample_count: int, rate: int) -> int:
    """Duration of an audio buffer; callers must not infer it from frame rate."""
    return sample_count * NANOSECONDS // rate


@dataclass
class VideoSelector:
    """CFR selection state; callers flush it at the playback stop boundary."""

    fps: int
    origin_ns: int | None = None
    next_index: int = 0
    previous: bytes | None = None
    candidate: bytes | None = None
    candidate_index: int | None = None
    candidate_distance: int | None = None

    def add(self, timestamp: int, data: bytes) -> list[bytes]:
        if self.origin_ns is None:
            self.origin_ns = timestamp
        index = cfr_index(timestamp, self.origin_ns, self.fps)
        ideal = self.origin_ns + index * NANOSECONDS // self.fps
        distance = abs(timestamp - ideal)
        emitted: list[bytes] = []
        if self.candidate_index is None:
            self.candidate_index, self.candidate, self.candidate_distance = (
                index,
                data,
                distance,
            )
            return emitted
        if index == self.candidate_index:
            if (
                self.candidate_distance is not None
                and distance < self.candidate_distance
            ):  # nearest capture wins; stable on ties
                self.candidate, self.candidate_distance = data, distance
            return emitted
        if index < self.candidate_index:
            return emitted  # late duplicate cannot replace an already settled slot
        emitted.extend(self._emit_through(index - 1))
        self.candidate_index, self.candidate, self.candidate_distance = (
            index,
            data,
            distance,
        )
        return emitted

    def _emit_through(self, last: int) -> list[bytes]:
        result: list[bytes] = []
        while self.next_index <= last:
            if self.next_index == self.candidate_index:
                self.previous = self.candidate
            if self.previous is not None:
                result.append(self.previous)
            self.next_index += 1
        return result

    def finish(self, stop_ns: int) -> list[bytes]:
        if self.origin_ns is None:
            return []
        last = cfr_index(stop_ns, self.origin_ns, self.fps)
        return self._emit_through(last)
