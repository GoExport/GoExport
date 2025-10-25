import helpers
from modules.logger import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
import urllib

class Interface:
    def __init__(self, obs: bool = False):
        # Select Chromium and Chromedriver paths based on OS
        if helpers.os_is_windows():
            chromium = helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_CHROMIUM_WINDOWS"))
            chromedriver = helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_CHROMEDRIVER_WINDOWS"))
            flash_path = helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_FLASH_WINDOWS"))
            flash_ver = helpers.get_config("PATH_FLASH_VERSION_WINDOWS")
        elif helpers.os_is_linux():
            chromium = helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_CHROMIUM_LINUX"))
            chromedriver = helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_CHROMEDRIVER_LINUX"))
            flash_path = helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_FLASH_LINUX"))
            flash_ver = helpers.get_config("PATH_FLASH_VERSION_LINUX")
        else:
            raise RuntimeError("Unsupported OS")

        self.options = Options()

        if helpers.os_is_windows():
            self.options.add_argument("--disable-infobars")
            self.options.add_argument("--disable-bookmarks-bar")
            self.options.add_argument("--kiosk")
            self.options.add_argument("--allow-running-insecure-content")
            self.options.add_argument("--force-device-scale-factor=1")
            self.options.add_argument("--high-dpi-support=1")
            self.options.add_argument(f"--ppapi-flash-path={flash_path}")
            self.options.add_argument(f"--ppapi-flash-version={flash_ver}")
            self.options.add_argument("--enable-unsafe-publish")
        elif helpers.os_is_linux():
            self.options.add_argument("--disable-infobars")
            self.options.add_argument("--disable-bookmarks-bar")
            self.options.add_argument("--kiosk")
            self.options.add_argument("--no-sandbox")
            self.options.add_argument("--force-device-scale-factor=1")
            self.options.add_argument("--high-dpi-support=1")
            self.options.add_argument(f"--ppapi-flash-path={flash_path}")
            self.options.add_argument(f"--ppapi-flash-version={flash_ver}")

        # Common options for both OSes
        self.options.add_argument(f"--user-data-dir={helpers.get_path(None, helpers.get_config("DEFAULT_OUTPUT_FILENAME"), f"{helpers.get_timestamp()}_chrome_profile_temp")}")
        start_url = helpers.convert_to_file_url(
            helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_ASSETS_FILENAME"), "start.html")
        ) + f"?obs={str(obs).lower()}"
        self.options.add_argument(f"--app={start_url}")
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.binary_location = chromium
        self.service = Service(executable_path=chromedriver)
        self.driver = None

    def start(self):
        """Initializes and starts the Selenium WebDriver."""
        self.driver = webdriver.Chrome(options=self.options, service=self.service)
        helpers.wait(2)
        return True
    
    def warning(self, width=1280, height=720):
        """Displays a warning on the browser for 5 seconds."""
        self.driver.get(helpers.convert_to_file_url(helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_ASSETS_FILENAME"), "warning.html")) + f"?w={width}&h={height}")
        print(self.driver.current_url)
        helpers.wait(3)
        return True

    def close(self):
        """Stops the Selenium WebDriver."""
        self.driver.quit()
        return True

    def inject_now(self, script: str):
        """Injects a JavaScript snippet into the page immediately."""
        self.driver.execute_script(script)
        logger.info("Injected script into page")

    def inject_in_future(self, script: str):
        """Injects a JavaScript snippet into the page."""
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": f'{script}'})
        logger.info("Injecting script in the future")
        return True

    def check_data(self, url: str):
        """
        Checks if there is any data stored for the given URL, including cookies.
        Returns True if any data exists, False otherwise.
        """
        # Check general storage (localStorage, IndexedDB, service workers)
        storage = self.driver.execute_cdp_cmd("Storage.getUsageAndQuota", {"origin": url})
        if storage.get("usage", 0) > 0:
            return True

        # Check cookies
        all_cookies = self.driver.execute_cdp_cmd("Network.getAllCookies", {}).get("cookies", [])
        # Extract domain from URL
        domain = urllib.parse.urlparse(url).netloc
        site_cookies = [c for c in all_cookies if domain in c["domain"]]

        if site_cookies:
            return True

        # No data found
        return False

    def enable_flash(self, offset: int = 0):
        """Enables the Flash Player."""
        url = self.driver.current_url
        self.driver.get(f"chrome://settings/content/siteDetails?site={urllib.parse.quote(url)}")

        actions = ActionChains(self.driver)
        for _ in range(19 + offset): # Find a way around this
            actions.send_keys(Keys.TAB)
            actions.perform()
            helpers.wait(0.1)
        actions.send_keys(Keys.SPACE)
        actions.perform()
        helpers.wait(0.5)
        actions.send_keys(Keys.ARROW_DOWN)
        actions.perform()
        helpers.wait(0.5)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        self.tried = True

        self.driver.back()
        self.driver.refresh()

        return True

    def await_started(self):
        WebDriverWait(self.driver, float('inf')).until(
            lambda driver: driver.execute_script("return window.startRecord !== undefined")
        )

        self.startedDelay = helpers.get_timestamp("Recording started")
        return True

    def play(self):
        """Start the video player if supported"""
        self.driver.execute_script('document.getElementById("obj").play()')
        return True
    
    def pause(self):
        """Pause the video player if supported"""
        self.driver.execute_script('document.getElementById("obj").pause()')
        return True

    def await_completed(self):
        WebDriverWait(self.driver, float('inf')).until(
            lambda driver: driver.execute_script("return window.stopRecord !== undefined")
        )
        self.endedDelay = helpers.get_timestamp("Recording ended")
        return True
    
    def get_timestamps(self):
        start_record = self.driver.execute_script("return window.startRecord")
        stop_record = self.driver.execute_script("return window.stopRecord")

        start_offset = self.startedDelay - start_record # ms delay
        stop_offset = self.endedDelay - stop_record # ms delay

        length = stop_record - start_record # ms length, negligible delay

        return [start_record, stop_record, length, start_offset, stop_offset]