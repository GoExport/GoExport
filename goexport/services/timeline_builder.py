from xml.etree import ElementTree as ET
from pathlib import Path
import logging
from goexport.models.audio_clip import AudioClip

logger = logging.getLogger(__name__)

class TimelineBuilder:
    def __init__(self, movie_xml: Path):
        self.movie_xml = movie_xml

        if not self.movie_xml.is_file():
            raise FileNotFoundError(
                f"Movie XML file does not exist: {self.movie_xml}"
            )

    def load(self) -> ET.Element:
        logger.info(
            "Loading movie XML: %s",
            self.movie_xml,
        )

        tree = ET.parse(self.movie_xml)

        return tree.getroot()

    def build(self) -> list[AudioClip]:
        """
        Build an audio timeline from the movie XML.
        """

        root = self.load()

        timeline = []

        for sound in root.findall("sound"):
            timeline.append(
                AudioClip(
                    asset_id=sound.findtext("sfile"),
                    start_frame=int(sound.findtext("start", "0")),
                    end_frame=int(sound.findtext("stop", "0")),
                    trim_start_frame=int(sound.findtext("trimStart", "0")),
                    trim_end_frame=int(sound.findtext("trimEnd", "0")),
                )
            )

            print(ET.tostring(sound, encoding="unicode"))

        logger.info(
            "Discovered %d audio clips",
            len(timeline),
        )
        
        for clip in timeline:
            print(clip)

        return timeline