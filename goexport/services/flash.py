import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException


def await_started(driver, timeout_minutes=30):
    timeout_seconds = (
        timeout_minutes * 60
        if timeout_minutes > 0
        else float("inf")
    )

    try:
        WebDriverWait(driver, timeout_seconds).until(
            lambda d: d.execute_script(
                "return window.startRecord !== undefined"
            )
        )
    except TimeoutException:
        raise TimeoutError(
            "Video failed to load"
        )