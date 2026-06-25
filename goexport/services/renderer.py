import logging

from goexport import config

logger = logging.getLogger(__name__)

class Renderer:
    def __init__(
        self,
        driver,
        encoder,
    ):
        self.driver = driver
        self.encoder = encoder

    def render(self):
        player = self.driver.find_element(
            "id",
            "player"
        )

        self.driver.execute_script(
            "player.pause();"
        )

        frame_count = self.driver.execute_script("""
            const fps = arguments[0];

            return player
                .getSceneInfoArray()
                .reduce(
                    (total, scene) => total + Math.round(scene.duration * fps),
                    0
                );
        """, config.FPS)

        result = self.driver.execute_script("""
            const fps = arguments[0];
            const scenes = player.getSceneInfoArray();

            const totalSeconds =
                scenes.reduce((t, s) => t + s.duration, 0);

            return {
                scenes: scenes.map((scene, index) => ({
                    scene: index,
                    duration: scene.duration,
                    framesExact: scene.duration * fps,
                    framesRounded: Math.round(scene.duration * fps),
                })),
                totalSeconds,
                totalFramesExact: totalSeconds * fps,
                roundedTotal: Math.round(totalSeconds * fps),
                summedRounded: scenes.reduce(
                    (t, s) => t + Math.round(s.duration * fps),
                    0
                ),
            };
        """, config.FPS)

        self.driver.execute_script("player.seekFrame(1)")

        for frame in range(1, frame_count + 1):
            self.driver.execute_script(
                f"player.seekFrame({frame})"
            )

            logger.info(
                f"Rendering frame {frame}/{frame_count} ({(frame/frame_count)*100:.2f}%)"
            )

            self.encoder.write_frame(
                player.screenshot_as_png
            )
            
        self.encoder.close()

        logger.info(
            "Video rendering complete."
        )