from dataclasses import dataclass


@dataclass(slots=True)
class ExportSettings:
    width: int = 1280
    height: int = 720
    fps: int = 24
    output_format: str = "mp4"
    is_wide: bool = True