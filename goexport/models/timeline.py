from dataclasses import dataclass, field

from goexport.models import AudioClip


@dataclass(slots=True)
class Timeline:
    clips: list[AudioClip] = field(default_factory=list)

    @property
    def duration_frames(self) -> int:
        if not self.clips:
            return 0

        return max(clip.end_frame for clip in self.clips)

    @property
    def duration_seconds(self) -> float:
        return self.duration_frames / 24