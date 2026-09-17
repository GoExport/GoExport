from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait


def get_total_frames(driver, fps: int) -> int:
    """Return the movie duration using the Flash player's scene timeline."""
    return int(
        driver.execute_script(
            """
            const fps = arguments[0];
            return player
                .getSceneInfoArray()
                .reduce(
                    (total, scene) => total + Math.round(scene.duration * fps),
                    0
                );
            """,
            fps,
        )
    )


def await_started(driver, timeout_minutes=30):
    timeout_seconds = timeout_minutes * 60 if timeout_minutes > 0 else float("inf")

    try:
        WebDriverWait(driver, timeout_seconds).until(
            lambda d: d.execute_script("return window.startRecord !== undefined")
        )
    except TimeoutException:
        raise TimeoutError("Video failed to load")

def await_player_ready(driver, timeout_seconds=30):
    try:
        WebDriverWait(driver, timeout_seconds).until(
            lambda d: d.execute_script(
                """
                return (
                    typeof window.player !== 'undefined'
                    && window.player !== null
                    && typeof window.player.pause === 'function'
                    && typeof window.player.play === 'function'
                );
                """
            )
        )
    except TimeoutException:
        screenshot_path = "player_ready_timeout.png"

        try:
            driver.save_screenshot(screenshot_path)
            print(f"Player readiness screenshot saved to: {screenshot_path}")
        except Exception as screenshot_error:
            print(f"Failed to capture screenshot: {screenshot_error}")

        raise TimeoutError(
            "Timed out waiting for the Flash player to become ready."
        )


def await_stopped(driver, timeout_minutes=60):
    timeout_seconds = timeout_minutes * 60 if timeout_minutes > 0 else float("inf")

    try:
        WebDriverWait(driver, timeout_seconds).until(
            lambda d: d.execute_script("return window.stopRecord === 1;")
        )
    except TimeoutException:
        raise TimeoutError(
            "Timed out waiting for the Flash player to signal recording stop."
        )
