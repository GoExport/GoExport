import logging
import os
import time
import urllib.parse
from pathlib import Path

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from goexport import config

logger = logging.getLogger(__name__)

THRESHOLD_WIDTH = 980
NARROW_TABS = 11
WIDE_TABS = 19


class BrowserService:
    VIRTUAL_RENDERER_KEYWORDS = (
        "virtual",
        "vmware",
        "virtualbox",
        "vbox",
        "qxl",
        "virtio",
        "parallels",
        "swiftshader",
        "llvmpipe",
        "basic render driver",
    )

    def __init__(
        self,
        chrome_path: Path,
        chromedriver_path: Path,
        flash_path: Path,
        flash_version: str,
        width: int = config.WIDTH,
        height: int = config.HEIGHT,
        check_screen_resolution: bool = True,
        check_frame_resolution: bool = True,
    ):
        self.chrome_path = chrome_path
        self.chromedriver_path = chromedriver_path
        self.flash_path = flash_path
        self.flash_version = flash_version
        self.width = width
        self.height = height
        self.display = None
        self.driver = None
        self.check_screen_resolution = check_screen_resolution
        self.check_frame_resolution = check_frame_resolution
        self._virtual_display_logged = False

    def create_driver(self):
        self.start_display()
        options = Options()

        options.binary_location = str(self.chrome_path)

        options.add_argument("--high-dpi-support=1")
        options.add_argument("--force-device-scale-factor=1")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--kiosk")

        options.add_argument("--disable-infobars")
        options.add_argument("--disable-bookmarks-bar")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-features=CalculateNativeWinOcclusion")

        options.add_argument(f"--ppapi-flash-path={str(self.flash_path)}")

        options.add_argument(f"--ppapi-flash-version={self.flash_version}")

        if config.SYSTEM == "Linux":
            options.add_argument("--no-sandbox")

        options.add_experimental_option("excludeSwitches", ["enable-automation"])

        self.driver = webdriver.Chrome(
            service=Service(str(self.chromedriver_path)),
            options=options,
        )

        return self.driver

    def start_display(self):
        if config.SYSTEM != "Linux":
            return

        # PyScap's Linux X11 backend captures the root window of DISPLAY and
        # does not expose individual windows through scap.targets().
        os.environ["SCAP_BACKEND"] = "x11"

        try:
            self.display = Display(
                visible=False,
                size=(self.width, self.height),
                color_depth=24,
            )
            self.display.start()

            logger.info("Started virtual display.")

        except Exception as e:
            self.display = None
            logger.warning(
                "Could not start virtual display (%s). "
                "Falling back to the current display.",
                e,
            )

    def stop_display(self):
        if self.display is not None:
            self.display.stop()
            self.display = None

    def close(self):
        """Release the display even if Chromium fails to shut down."""
        try:
            if self.driver is not None:
                self.driver.quit()
        finally:
            self.driver = None
            self.stop_display()

    @staticmethod
    def get_capture_target(driver):
        if config.SYSTEM == "Linux":
            # The X11 capturer uses the current DISPLAY when target is None.
            # Window enumeration is unavailable on this backend.
            return None

        import scap

        window_title = driver.title
        targets = [
            target
            for target in scap.targets()
            if target.kind == "window"
            and (
                target.title == window_title
                or target.title.startswith(f"{window_title} - ")
            )
        ]

        if len(targets) != 1:
            logger.error(
                "Capture-target lookup for %r matched %d window(s): %s",
                window_title,
                len(targets),
                [getattr(target, "title", repr(target)) for target in targets],
            )
            raise RuntimeError(
                "Could not identify the Selenium window for capture. "
                f"Expected one window titled {window_title!r}, found "
                f"{len(targets)}."
            )

        return targets[0]

    @staticmethod
    def enter_fullscreen(driver):
        driver.fullscreen_window()

    @staticmethod
    def _get_viewport_size(driver):
        return driver.execute_script("""
            return {
                width: window.innerWidth,
                height: window.innerHeight
            };
        """)

    @staticmethod
    def _get_display_metrics(driver):
        return driver.execute_script("""
            return {
                screenWidth: window.screen.width,
                screenHeight: window.screen.height,
                availWidth: window.screen.availWidth,
                availHeight: window.screen.availHeight,
                devicePixelRatio: window.devicePixelRatio
            };
        """)

    @staticmethod
    def _get_renderer_signature(driver):
        return driver.execute_script("""
            try {
                const canvas = document.createElement('canvas');
                const gl = canvas.getContext('webgl')
                    || canvas.getContext('experimental-webgl');

                if (!gl) {
                    return '';
                }

                const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                const renderer = debugInfo
                    ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
                    : gl.getParameter(gl.RENDERER);
                const vendor = debugInfo
                    ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL)
                    : gl.getParameter(gl.VENDOR);

                return `${vendor || ''} ${renderer || ''}`.trim();
            } catch (e) {
                return '';
            }
        """)

    def _has_virtual_display_driver(self, driver):
        if self.display is not None:
            if not self._virtual_display_logged:
                logger.info(
                    "Skipping screen-resolution check because an internal virtual display is active."
                )
                self._virtual_display_logged = True
            return True

        signature = self._get_renderer_signature(driver)

        if not signature:
            return False

        lowered = signature.lower()

        for keyword in self.VIRTUAL_RENDERER_KEYWORDS:
            if keyword in lowered:
                if not self._virtual_display_logged:
                    logger.info(
                        "Skipping screen-resolution check due to detected virtual display driver '%s'.",
                        signature,
                    )
                    self._virtual_display_logged = True
                return True

        return False

    def validate_screen_resolution(self, driver):
        if not self.check_screen_resolution:
            return

        if self._has_virtual_display_driver(driver):
            return

        metrics = self._get_display_metrics(driver)

        screen_width = max(
            int(metrics["screenWidth"]),
            int(metrics["availWidth"]),
        )
        screen_height = max(
            int(metrics["screenHeight"]),
            int(metrics["availHeight"]),
        )

        if self.width > screen_width or self.height > screen_height:
            raise RuntimeError(
                "Selected resolution "
                f"{self.width}x{self.height} exceeds display size "
                f"{screen_width}x{screen_height}. "
                "Use --skip-screen-resolution-check to bypass this validation."
            )

    def assert_full_resolution(self):
        if not self.check_frame_resolution:
            return

        if self.driver is None:
            raise RuntimeError(
                "Cannot validate frame resolution before the browser is initialized."
            )

        viewport = self._get_viewport_size(self.driver)

        if int(viewport["width"]) < self.width or int(viewport["height"]) < self.height:
            raise RuntimeError(
                "Fullscreen browser is smaller than the configured crop resolution. "
                f"Required at least {self.width}x{self.height}, got "
                f"{int(viewport['width'])}x{int(viewport['height'])}. "
                "Use --skip-frame-resolution-check to bypass this validation."
            )

    @staticmethod
    def inject_dom(
        driver,
        html_file: str | Path,
        replacements: dict[str, object] | None = None,
    ) -> None:
        html = Path(html_file).read_text(encoding="utf-8")

        if replacements:
            for key, value in replacements.items():
                html = html.replace(
                    f"{{{{{key}}}}}",
                    str(value),
                )

        driver.execute_script(
            """
            document.open();
            document.write(arguments[0]);
            document.close();
        """,
            html,
        )

    @staticmethod
    def enable_flash(driver):
        current_url = driver.current_url

        driver.get(
            "chrome://settings/content/siteDetails?site="
            + urllib.parse.quote(current_url)
        )

        # Give the settings page a moment to render.
        time.sleep(0.5)

        width = driver.execute_script("""
            return window.innerWidth;
        """)

        is_narrow = width < THRESHOLD_WIDTH

        if is_narrow:
            logger.info("Detected narrow toolbar layout.")
            tab_count = NARROW_TABS
        else:
            logger.info("Detected wide toolbar layout.")
            tab_count = WIDE_TABS

        actions = ActionChains(driver)

        for _ in range(tab_count):
            actions.send_keys(Keys.TAB).perform()
            time.sleep(0.05)

        actions.send_keys(Keys.SPACE).perform()
        actions.send_keys(Keys.ARROW_DOWN).perform()
        actions.send_keys(Keys.ENTER).perform()

        driver.get(current_url)
