from dataclasses import dataclass


@dataclass(slots=True)
class AudioClip:
    asset_id: str

    start_frame: int
    end_frame: int

    trim_start_frame: int = 0
    trim_end_frame: int = 0

    @property
    def has_trim(self) -> bool:
        return (
            self.trim_start_frame > 0
            and self.trim_end_frame > 0
        )
    
    @property
    def duration_frames(self) -> int:
        return self.end_frame - self.start_frame