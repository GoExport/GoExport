import helpers
from modules.logger import logger
from modules.exceptions import TimeoutError, BrowserClosedError
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException, InvalidSessionIdException, NoSuchWindowException, WebDriverException
import urllib
import os

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

        self.start_url = helpers.convert_to_file_url(
            helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_ASSETS_FILENAME"), "start.html")
        ) + f"?obs={str(obs).lower()}"

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
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # Capture everything Chromium exposes through the DevTools console. Selenium's
        # browser log includes console.log/warn/error calls, uncaught JavaScript
        # exceptions, and browser-generated console messages such as failed resources.
        self.options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
        self.options.binary_location = chromium
        self.service = Service(executable_path=chromedriver)
        self.driver = None

    @staticmethod
    def _is_browser_closed_error(error):
        """Return True when Selenium lost the Chromium window/session."""
        if isinstance(error, (NoSuchWindowException, InvalidSessionIdException)):
            return True

        if isinstance(error, WebDriverException):
            message = str(error).lower()
            closed_markers = (
                "chrome not reachable",
                "no such window",
                "target window already closed",
                "web view not found",
                "invalid session id",
                "not connected to devtools",
                "disconnected: not connected to devtools",
                "session deleted because of page crash",
            )
            return any(marker in message for marker in closed_markers)

        return False

    def _translate_webdriver_error(self, error):
        if self._is_browser_closed_error(error):
            raise BrowserClosedError(
                "Chromium was closed before GoExport finished. "
                "Please leave the Chromium window open until the export is complete."
            ) from error
        raise error

    def log_browser_console(self):
        """Forward Chromium's DevTools console entries to the GoExport console/log."""
        if self.driver is None:
            return

        try:
            entries = self.driver.get_log("browser")
        except Exception as error:
            if self._is_browser_closed_error(error):
                self._translate_webdriver_error(error)
            # Console forwarding is diagnostic and should never break an otherwise
            # healthy export if ChromeDriver cannot provide a log entry.
            logger.debug(f"Could not read Chromium console log: {error}")
            return

        for entry in entries:
            level = str(entry.get("level", "INFO")).upper()
            message = entry.get("message", "")
            line = f"[Chromium console][{level}] {message}"

            if level == "SEVERE":
                logger.error(line)
            elif level == "WARNING":
                logger.warning(line)
            else:
                # Keep INFO/DEBUG console messages visible without requiring --verbose.
                logger.info(line)

    def _execute_script(self, script):
        try:
            result = self.driver.execute_script(script)
        except Exception as error:
            self._translate_webdriver_error(error)
        self.log_browser_console()
        return result

    def _execute_cdp_cmd(self, command, params):
        try:
            result = self.driver.execute_cdp_cmd(command, params)
        except Exception as error:
            self._translate_webdriver_error(error)
        self.log_browser_console()
        return result

    def navigate(self, url):
        """Navigate Chromium while translating a manually closed browser cleanly."""
        try:
            self.driver.get(url)
        except Exception as error:
            self._translate_webdriver_error(error)
        self.log_browser_console()
        return True

    def start(self):
        """Initializes and starts the Selenium WebDriver."""
        # On Linux, set DISPLAY environment variable to match x11grab_display parameter
        if helpers.os_is_linux():
            display = helpers.get_param('x11grab_display') or ':0.0'
            os.environ['DISPLAY'] = display
            logger.info(f"Set DISPLAY environment variable to {display}")
            
        self.driver = webdriver.Chrome(options=self.options, service=self.service)
        self.navigate(self.start_url)
        helpers.wait(2)
        self.log_browser_console()
        return True
    
    def warning(self, width=1280, height=720):
        """Displays a warning on the browser for 5 seconds."""
        self.navigate(helpers.convert_to_file_url(helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_ASSETS_FILENAME"), "warning.html")) + f"?w={width}&h={height}")
        try:
            print(self.driver.current_url)
        except Exception as error:
            self._translate_webdriver_error(error)
        helpers.wait(3)
        return True

    def close(self):
        """Stops the Selenium WebDriver."""
        self.log_browser_console()
        try:
            self.driver.quit()
        except Exception as error:
            self._translate_webdriver_error(error)
        finally:
            self.driver = None
        return True

    def inject_now(self, script: str):
        """Injects a JavaScript snippet into the page immediately."""
        self._execute_script(script)
        logger.info("Injected script into page")

    def inject_in_future(self, script: str):
        """Injects a JavaScript snippet into the page."""
        self._execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": f'{script}'})
        logger.info("Injecting script in the future")
        return True

    def check_data(self, url: str):
        """
        Checks if there is any data stored for the given URL, including cookies.
        Returns True if any data exists, False otherwise.
        """
        # Check general storage (localStorage, IndexedDB, service workers)
        storage = self._execute_cdp_cmd("Storage.getUsageAndQuota", {"origin": url})
        if storage.get("usage", 0) > 0:
            return True

        # Check cookies
        all_cookies = self._execute_cdp_cmd("Network.getAllCookies", {}).get("cookies", [])
        # Extract domain from URL
        domain = urllib.parse.urlparse(url).netloc
        site_cookies = [c for c in all_cookies if domain in c["domain"]]

        if site_cookies:
            return True

        # No data found
        return False

    def enable_flash(self, offset: int = 0):
        # If people start having issues, revert 0.05 to 0.1
        """Enables the Flash Player."""
        try:
            url = self.driver.current_url
            self.navigate(f"chrome://settings/content/siteDetails?site={urllib.parse.quote(url)}")

            actions = ActionChains(self.driver)
            for _ in range(19 + offset): # Find a way around this
                actions.send_keys(Keys.TAB)
                actions.perform()
                helpers.wait(0.05)
            actions.send_keys(Keys.SPACE)
            actions.perform()
            helpers.wait(0.05)
            actions.send_keys(Keys.ARROW_DOWN)
            actions.perform()
            helpers.wait(0.05)
            actions.send_keys(Keys.ENTER)
            actions.perform()
            self.tried = True

            self.driver.back()
            self.driver.refresh()
            self.log_browser_console()
        except Exception as error:
            if isinstance(error, BrowserClosedError):
                raise
            self._translate_webdriver_error(error)

        return True

    def await_started(self, timeout_minutes: int = 30):
        """
        Wait for the video to start loading/playing.
        
        :param timeout_minutes: Maximum minutes to wait (0 to disable timeout)
        :raises TimeoutError: If timeout is reached
        :return: True if started successfully
        """
        # Convert minutes to seconds, 0 means infinite wait
        timeout_seconds = timeout_minutes * 60 if timeout_minutes > 0 else float('inf')
        
        try:
            WebDriverWait(self.driver, timeout_seconds).until(
                lambda driver: self._execute_script("return window.startRecord !== undefined")
            )
        except TimeoutException:
            raise TimeoutError(
                f"Video failed to load within {timeout_minutes} minutes",
                timeout_type="load"
            )

        self.startedDelay = helpers.get_timestamp("Recording started")
        return True

    def play(self):
        """Start the video player if supported"""
        self._execute_script('document.getElementById("obj").play()')
        return True
    
    def pause(self):
        """Pause the video player if supported"""
        self._execute_script('document.getElementById("obj").pause()')
        return True

    def await_completed(self, timeout_minutes: int = 0):
        """
        Wait for the video to finish playing.
        
        :param timeout_minutes: Maximum minutes to wait (0 to disable timeout)
        :raises TimeoutError: If timeout is reached
        :return: True if completed successfully
        """
        # Convert minutes to seconds, 0 means infinite wait
        timeout_seconds = timeout_minutes * 60 if timeout_minutes > 0 else float('inf')
        
        try:
            WebDriverWait(self.driver, timeout_seconds).until(
                lambda driver: self._execute_script("return window.stopRecord !== undefined")
            )
        except TimeoutException:
            raise TimeoutError(
                f"Video did not finish within {timeout_minutes} minutes after loading",
                timeout_type="video"
            )
        
        self.endedDelay = helpers.get_timestamp("Recording ended")
        return True
    
    def get_timestamps(self):
        start_record = self._execute_script("return window.startRecord")
        stop_record = self._execute_script("return window.stopRecord")

        start_offset = self.startedDelay - start_record # ms delay
        stop_offset = self.endedDelay - stop_record # ms delay

        length = stop_record - start_record # ms length, negligible delay

        return [start_record, stop_record, length, start_offset, stop_offset]