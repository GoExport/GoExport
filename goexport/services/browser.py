from pathlib import Path
import urllib.parse
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from goexport import config


class BrowserService:
    def __init__(
        self,
        chrome_path: Path,
        chromedriver_path: Path,
        flash_path: Path,
        flash_version: str,
    ):
        self.chrome_path = chrome_path
        self.chromedriver_path = chromedriver_path
        self.flash_path = flash_path
        self.flash_version = flash_version

    def create_driver(self):
        options = Options()

        options.binary_location = str(self.chrome_path)
        print(f"Using Chrome binary at: {self.chrome_path}")

        options.add_argument("--high-dpi-support=1")
        options.add_argument("--force-device-scale-factor=1")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-bookmarks-bar")

        if config.SYSTEM == "Linux":
            options.add_argument("--no-sandbox")

        options.add_argument(
            f"--ppapi-flash-path={self.flash_path}"
        )

        options.add_argument(
            f"--ppapi-flash-version={self.flash_version}"
        )

        options.add_experimental_option(
            "excludeSwitches",
            ["enable-automation"]
        )

        return webdriver.Chrome(
            service=Service(str(self.chromedriver_path)),
            options=options,
        )

    @staticmethod
    def set_viewport_size(driver, width, height):
        driver.set_window_size(width, height)

        actual = driver.execute_script("""
            return {
                width: window.innerWidth,
                height: window.innerHeight
            };
        """)

        extra_width = (
            driver.get_window_size()["width"]
            - actual["width"]
        )

        extra_height = (
            driver.get_window_size()["height"]
            - actual["height"]
        )

        driver.set_window_size(
            width + extra_width,
            height + extra_height,
        )

    @staticmethod
    def inject_dom(
        driver,
        html_file: str,
        replacements: dict[str, str] | None = None,
    ) -> None:
        html = Path(html_file).read_text(
            encoding="utf-8"
        )

        if replacements:
            for key, value in replacements.items():
                html = html.replace(
                    f"{{{{{key}}}}}",
                    str(value),
                )

        driver.execute_script("""
            document.open();
            document.write(arguments[0]);
            document.close();
        """, html)
        
    @staticmethod
    def enable_flash(driver):
        current_url = driver.current_url

        driver.get(
            "chrome://settings/content/siteDetails?site="
            + urllib.parse.quote(current_url)
        )

        actions = ActionChains(driver)

        for _ in range(19):
            actions.send_keys(Keys.TAB).perform()
            time.sleep(0.05)

        actions.send_keys(Keys.SPACE).perform()
        actions.send_keys(Keys.ARROW_DOWN).perform()
        actions.send_keys(Keys.ENTER).perform()

        driver.back()
        driver.refresh()