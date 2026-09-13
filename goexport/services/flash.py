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
        raise TimeoutError(
            "Timed out waiting for the Flash player to become ready."
        )


def await_stopped(driver, timeout_minutes=60):
    timeout_seconds = (
        timeout_minutes * 60
        if timeout_minutes > 0
        else float("inf")
    )

    try:
        WebDriverWait(driver, timeout_seconds).until(
            lambda d: d.execute_script(
                "return window.stopRecord === 1;"
            )
        )
    except TimeoutException:
        raise TimeoutError(
            "Timed out waiting for the Flash player to signal recording stop."
        )