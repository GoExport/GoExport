from goexport.config import FPS


class Renderer:
    def __init__(self, driver, encoder):
        self.driver = driver
        self.encoder = encoder

    def render(self, frame_count):
        player = self.driver.find_element(
            "id",
            "player_object"
        )

        for frame in range(frame_count):
            self.encoder.write_frame(
                player.screenshot_as_png
            )

            self.driver.execute_script(
                f"player_object.seekFrame({frame + 1})"
            )