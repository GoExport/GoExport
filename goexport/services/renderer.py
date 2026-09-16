import logging
from typing import Callable

from goexport import config
from goexport.services.flash import get_total_frames

logger = logging.getLogger(__name__)


class Renderer:
    def __init__(
        self,
        driver,
        encoder,
        resolution_guard: Callable[[], None] | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ):
        self.driver = driver
        self.encoder = encoder
        self.resolution_guard = resolution_guard
        self.progress_callback = progress_callback
        self.duration_frames = 0

    def render(self):
        try:
            self.driver.find_element("id", "player")

            self.driver.execute_script("player.pause();")

            frame_count = get_total_frames(self.driver, config.FPS)

            self.duration_frames = frame_count

            for frame in range(1, frame_count + 1):
                self.driver.execute_script(f"player.seekFrame({frame})")

                if self.resolution_guard is not None:
                    self.resolution_guard()

                if self.progress_callback is not None:
                    self.progress_callback(frame / frame_count * 100)
                else:
                    logger.info(
                        "Rendering frame %d/%d (%.2f%%)",
                        frame,
                        frame_count,
                        frame / frame_count * 100,
                    )

                self.encoder.write_frame(self.driver.get_screenshot_as_png())

        finally:
            self.encoder.close()

        logger.info("Video rendering complete.")
