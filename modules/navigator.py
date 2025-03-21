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
    def __init__(self):
        chromium = helpers.get_path(None, helpers.get_config("PATH_CHROMIUM"))
        chromedriver = helpers.get_path(None, helpers.get_config("PATH_CHROMEDRIVER"))

        self.options = Options()
        self.options.add_argument("--disable-infobars")
        self.options.add_argument("--disable-bookmarks-bar")
        self.options.add_argument("--allow-running-insecure-content")
        self.options.add_argument("force-device-scale-factor=1")
        self.options.add_argument("--high-dpi-support=1")
        self.options.add_argument("--kiosk")
        self.options.add_argument(f"--app={helpers.convert_to_file_url(helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_ASSETS_FILENAME"), "start.html"))}")
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.binary_location = chromium
        self.service = Service(executable_path=chromedriver)
        self.driver = None

    def start(self):
        """Initializes and starts the Selenium WebDriver."""
        self.driver = webdriver.Chrome(options=self.options, service=self.service)
        helpers.wait(5)
        return True
    
    def close(self):
        """Stops the Selenium WebDriver."""
        self.driver.quit()
        return True

    def enable_flash(self, manual=False):
        """Enables the Flash Player."""
        url = self.driver.current_url
        self.driver.get(f"chrome://settings/content/siteDetails?site={urllib.parse.quote(url)}")

        actions = ActionChains(self.driver)
        for _ in range(19):
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

        return True
    
    def check_flash(self):
        """Checks if the Flash Player is enabled."""
        return self.driver.execute_script("return navigator.plugins['Shockwave Flash'] !== undefined")

    def await_started(self):
        if not self.check_flash():
            logger.error(f"Failed to enable Flash Player: {self.tried}")
            return False
        
        WebDriverWait(self.driver, float('inf')).until(
            lambda driver: driver.execute_script("return window.startRecord !== undefined")
        )

        self.startedDelay = helpers.get_timestamp("Recording started")
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