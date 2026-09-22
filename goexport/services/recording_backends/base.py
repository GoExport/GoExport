"""Small data contract shared by recording capture engines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
