import helpers
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
import urllib
import time

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
        self.options.add_argument(f"--app={helpers.convert_to_file_url(helpers.get_path(None, helpers.get_config("DEFAULT_ASSETS_FILENAME"), "start.html"))}")
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.binary_location = chromium
        self.service = Service(executable_path=chromedriver)
        self.driver = None

    def start(self):
        """Initializes and starts the Selenium WebDriver."""
        self.driver = webdriver.Chrome(options=self.options)
        time.sleep(5) # Show message
        return True
    
    def close(self):
        """Stops the Selenium WebDriver."""
        self.driver.quit()
        return True

    def enable_flash(self):
        url = self.driver.current_url
        self.driver.get(f"chrome://settings/content/siteDetails?site={urllib.parse.quote(url)}")

        actions = ActionChains(self.driver)
        actions = actions.send_keys(Keys.TAB * 19)
        actions = actions.send_keys(Keys.SPACE)
        actions = actions.send_keys("a")
        actions = actions.send_keys(Keys.ENTER)    
        actions.perform()
        time.sleep(1)

        self.driver.back()

        return True

    def await_started(self):
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