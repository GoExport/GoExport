from pathlib import Path
import logging

from goexport.models.audio_clip import AudioClip
from goexport.services.ffmpeg import FFmpegAudioEncoder

logger = logging.getLogger(__name__)


class AudioProcessor:
    def __init__(
        self,
        encoder: FFmpegAudioEncoder,
    ):
        self.encoder = encoder

    def process(
        self,
        timeline: list[AudioClip],
    ) -> Path:
        logger.info(
            "Processing %d audio clips",
            len(timeline),
        )

        output_file = Path("audio.wav")


        for clip in timeline:
            logger.info(
                (
                    "Clip: asset=%s "
                    "timeline=%d-%d "
                    "trim=%d-%d"
                ),
                clip.asset_id,
                clip.start_frame,
                clip.end_frame,
                clip.trim_start_frame,
                clip.trim_end_frame,
            )

        self.encoder.encode(
            timeline,
            output_file,
        )

        return output_file