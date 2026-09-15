import logging
from typing import Callable

from goexport import config

logger = logging.getLogger(__name__)


class Renderer:
    def __init__(
        self,
        driver,
        encoder,
        resolution_guard: Callable[[], None] | None = None,
    ):
        self.driver = driver
        self.encoder = encoder
        self.resolution_guard = resolution_guard
        self.duration_frames = 0

    def render(self):
        try:
            self.driver.find_element("id", "player")

            self.driver.execute_script("player.pause();")

            frame_count = self.driver.execute_script(
                """
                const fps = arguments[0];

                return player
                    .getSceneInfoArray()
                    .reduce(
                        (total, scene) => total + Math.round(scene.duration * fps),
                        0
                    );
            """,
                config.FPS,
            )

            self.duration_frames = frame_count

            for frame in range(1, frame_count + 1):
                self.driver.execute_script(f"player.seekFrame({frame})")

                if self.resolution_guard is not None:
                    self.resolution_guard()

                logger.info(
                    f"Rendering frame {frame}/{frame_count} ({(frame / frame_count) * 100:.2f}%)"
                )

                self.encoder.write_frame(self.driver.get_screenshot_as_png())

        finally:
            self.encoder.close()

        logger.info("Video rendering complete.")
