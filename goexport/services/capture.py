"""PyScap construction and timestamp helpers used by the live recorder.

PyScap timestamps are converted to integer nanoseconds as soon as they enter
GoExport.  The recorder deliberately never compares them with Python clocks.
"""

from __future__ import annotations

import ctypes
import logging
import os
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from goexport import config

NANOSECONDS = 1_000_000_000
logger = logging.getLogger(__name__)

_windows_dpi_configured = False


def configure_windows_dpi_awareness() -> None:
    """Use physical pixels for Windows capture and window coordinates.

    Without process DPI awareness, Windows virtualizes a 1920x1080 display to
    1536x864 at 125% scaling.  PyScap then returns frames in those logical
    dimensions, which are too small for a requested 1920x1080 export.
    """
    global _windows_dpi_configured

    if config.SYSTEM != "Windows" or _windows_dpi_configured:
        return

    windll = getattr(ctypes, "windll", None)
    if windll is None:
        logger.debug("Windows DPI APIs are unavailable")
        return

    # Windows 10 1703+: per-monitor v2 is the most accurate mode when a window
    # moves between monitors with different scale factors.
    try:
        if windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            _windows_dpi_configured = True
            return
    except (AttributeError, OSError):
        pass

    # Windows 8.1 fallback.
    try:
        if windll.shcore.SetProcessDpiAwareness(2) == 0:
            _windows_dpi_configured = True
            return
    except (AttributeError, OSError):
        pass

    # Vista/Windows 7 fallback. This is system-DPI aware rather than per-monitor
    # aware, but still prevents the logical-pixel virtualization behind the bug.
    try:
        if windll.user32.SetProcessDPIAware():
            _windows_dpi_configured = True
            return
    except (AttributeError, OSError):
        pass

    logger.debug("Windows DPI awareness could not be configured")


def configure_backend(display: str | None = None) -> None:
    """Configure the process before PyScap initializes its native backend."""
    configure_windows_dpi_awareness()
    if config.SYSTEM == "Linux":
        os.environ.setdefault("SCAP_BACKEND", "x11")
        if display is not None:
            os.environ["DISPLAY"] = display


def timestamp_ns(timestamp: Any) -> int:
    """Convert PyScap's numeric timestamp to an exact-ish integer duration."""
    return int((Decimal(str(timestamp)) * NANOSECONDS).to_integral_value(ROUND_HALF_UP))


def create_capturer(
    target: Any,
    crop_area: tuple[int, int, int, int] | None = None,
    display: str | None = None,
):
    """Create the sole production PyScap capturer (imported lazily for export)."""
    configure_backend(display)
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
