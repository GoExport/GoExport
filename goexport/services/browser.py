import logging
import os
import time
import urllib.parse
import uuid
from collections.abc import Mapping
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from goexport import config
from goexport.services.chromium import (
    ChromiumDependencyCheckError,
    find_linux_chromium_missing_dependencies,
)
from goexport.services.display import LinuxDisplay

logger = logging.getLogger(__name__)

FLASH_PERMISSION_WAIT_SECONDS = 5
FLASH_PERMISSION_POLL_SECONDS = 0.1
CAPTURE_TARGET_WAIT_SECONDS = 5
CAPTURE_TARGET_POLL_SECONDS = 0.1


# Chromium 87's site-details page defines Flash as the `plugins` content
# setting. Its <select id="permission"> lives in a site-details-permission
# component's open Shadow DOM. This script walks all open shadow roots because
# the component is itself nested inside several settings components.
FLASH_PERMISSION_SCRIPT = """
    const roots = [document];
    const seenRoots = new Set();
    let flashPermission = null;

    while (roots.length && !flashPermission) {
        const root = roots.pop();
        if (seenRoots.has(root)) {
            continue;
        }
        seenRoots.add(root);

        for (const element of root.querySelectorAll('*')) {
            if (element.shadowRoot) {
                roots.push(element.shadowRoot);
            }
            if (element.localName === 'site-details-permission' &&
                element.category === 'plugins') {
                flashPermission = element;
                break;
            }
        }
    }

    if (!flashPermission) {
        return {status: 'not-found'};
    }

    const select = flashPermission.shadowRoot.querySelector('#permission');
    if (!select || !select.getClientRects().length) {
        return {status: 'not-ready'};
    }
    if (select.disabled) {
        return {status: 'disabled'};
    }

    const allow = select.querySelector('option[value="allow"]');
    if (!allow || allow.hidden || allow.disabled) {
        return {status: 'allow-unavailable'};
    }
    if (select.value === 'allow') {
        return {status: 'allowed'};
    }

    select.value = 'allow';
    select.dispatchEvent(new Event('change', {bubbles: true, composed: true}));
    return {status: select.value === 'allow' ? 'changed' : 'change-failed'};
"""


class BrowserService:
    # The requested dimensions are for the page viewport. Chromium needs extra
    # framebuffer space for its own frame when it runs under Xvfb.
    VIRTUAL_DISPLAY_MARGIN = 256
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
        electron: bool = False,
        width: int = config.WIDTH,
        height: int = config.HEIGHT,
        check_screen_resolution: bool = True,
        check_frame_resolution: bool = True,
        use_virtual_display: bool = True,
    ):
        self.chrome_path = chrome_path
        self.chromedriver_path = chromedriver_path
        self.flash_path = flash_path
        self.flash_version = flash_version
        self.electron = electron
        self.width = width
        self.height = height
        self.display: LinuxDisplay | None = None
        self.driver = None
        self.check_screen_resolution = check_screen_resolution
        self.check_frame_resolution = check_frame_resolution
        self.use_virtual_display = use_virtual_display
        self._virtual_display_logged = False
        self._capture_target_id = None

    def create_driver(self):
        self.validate_linux_dependencies()
        self.start_display()
        options = Options()

        options.binary_location = str(self.chrome_path)

        if self.electron:
            options.add_argument("--remote-debugging-port=9222")

        options.add_argument("--high-dpi-support=1")
        options.add_argument("--force-device-scale-factor=1")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--kiosk")
        options.add_argument("--window-position=0,0")
        options.add_argument(f"--window-size={self.width},{self.height}")

        options.add_argument("--disable-infobars")
        options.add_argument("--disable-bookmarks-bar")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-features=CalculateNativeWinOcclusion")

        options.add_argument(f"--ppapi-flash-path={str(self.flash_path)}")

        options.add_argument(f"--ppapi-flash-version={self.flash_version}")

        options.add_argument("--allow-outdated-plugins")

        if config.SYSTEM == "Linux":
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

        options.add_experimental_option("excludeSwitches", ["enable-automation"])

        self.driver = webdriver.Chrome(
            service=Service(str(self.chromedriver_path)),
            options=options,
        )

        return self.driver

    def validate_linux_dependencies(self):
        """Fail before Selenium starts when bundled Chromium lacks Linux libraries."""

        if config.SYSTEM != "Linux":
            return

        try:
            missing = find_linux_chromium_missing_dependencies(self.chrome_path)
        except ChromiumDependencyCheckError as error:
            raise RuntimeError(
                "Could not validate Chromium's Linux shared libraries: "
                f"{error}\n\nRun `GoExport doctor` for additional diagnostics."
            ) from error

        if missing:
            libraries = "\n".join(f"  - {library}" for library in missing)
            raise RuntimeError(
                "Chromium cannot start because required Linux shared libraries are missing:\n"
                f"{libraries}\n\nRun `GoExport doctor` for additional diagnostics."
            )

    def start_display(self):
        if config.SYSTEM != "Linux" or not self.use_virtual_display:
            return

        try:
            self.display = LinuxDisplay(
                size=(
                    self.width + self.VIRTUAL_DISPLAY_MARGIN,
                    self.height + self.VIRTUAL_DISPLAY_MARGIN,
                ),
                color_depth=24,
            )
            capture_display = self.display.start()

            logger.info("Started virtual display %s.", capture_display)

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

    @property
    def capture_display(self):
        """The X display shared by this browser and Linux capture session."""
        if self.display is not None:
            return self.display.capture_display
        return os.environ.get("DISPLAY")

    def close(self):
        """Release the display even if Chromium fails to shut down."""
        try:
            if self.driver is not None:
                self.driver.quit()
        finally:
            self.driver = None
            self.stop_display()

    def get_capture_target(self, driver):
        if self.display is not None or config.SYSTEM == "Linux":
            # The X11 capturer uses the current DISPLAY when target is None.
            # Window enumeration is unavailable on this backend.
            return None

        import scap

        window_title = driver.title
        all_targets = list(scap.targets())

        if self._capture_target_id is not None:
            remembered = [
                target
                for target in all_targets
                if target.kind == "window" and target.id == self._capture_target_id
            ]
            if len(remembered) == 1:
                return remembered[0]
            raise RuntimeError(
                "The Selenium window changed identity after entering fullscreen. "
                f"Expected macOS window ID {self._capture_target_id}, found "
                f"{len(remembered)} matching windows."
            )

        targets = [
            target
            for target in all_targets
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

    def remember_capture_target(self, driver):
        """Bind the current macOS Chromium window before fullscreen changes its title."""
        if config.SYSTEM != "Darwin" or self.electron:
            return

        import scap

        original_title = driver.title
        marker = f"GoExport Capture Probe {uuid.uuid4().hex}"
        driver.execute_script("document.title = arguments[0];", marker)
        deadline = time.monotonic() + CAPTURE_TARGET_WAIT_SECONDS
        try:
            while True:
                matches = [
                    target
                    for target in scap.targets()
                    if target.kind == "window"
                    and (
                        target.title == marker
                        or target.title.startswith(f"{marker} - ")
                    )
                ]
                if len(matches) == 1:
                    self._capture_target_id = matches[0].id
                    logger.info(
                        "Bound Chromium to macOS capture window ID %s before fullscreen.",
                        self._capture_target_id,
                    )
                    return
                if len(matches) > 1:
                    raise RuntimeError(
                        "Could not uniquely identify the Selenium window before "
                        f"fullscreen; marker {marker!r} matched {len(matches)} windows."
                    )
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "Could not identify the Selenium window before fullscreen. "
                        "macOS did not publish Chromium's temporary capture title."
                    )
                time.sleep(CAPTURE_TARGET_POLL_SECONDS)
        finally:
            driver.execute_script("document.title = arguments[0];", original_title)

    def get_capture_crop_area(self, driver):
        viewport = driver.execute_script("""
            return {
                innerHeight: window.innerHeight,
                outerHeight: window.outerHeight
            };
        """)

        top_inset = max(0, int(viewport["outerHeight"]) - int(viewport["innerHeight"]))

        if top_inset == 0:
            return None

        if self.display is not None:
            # Linux/X11 display capture: coordinates are display-relative.
            window = driver.get_window_rect()

            return (
                int(window["x"]),
                int(window["y"]) + top_inset,
                self.width,
                self.height,
            )

        if self.electron:
            # Windows/macOS window capture: crop relative to captured window.
            return (
                0,
                top_inset,
                self.width,
                self.height,
            )

        return None

    def enter_fullscreen(self, driver):
        if self.electron:
            logger.info("Skipping Selenium fullscreen for Electron browser.")
            return

        if self.display is None:
            driver.fullscreen_window()
            return

        # Xvfb commonly has no window manager, so fullscreen_window() does not
        # reliably grow Chromium to the requested viewport.
        driver.set_window_rect(x=0, y=0, width=self.width, height=self.height)
        for _ in range(3):
            viewport = self._get_viewport_size(driver)
            missing_width = max(0, self.width - int(viewport["width"]))
            missing_height = max(0, self.height - int(viewport["height"]))
            if missing_width == 0 and missing_height == 0:
                return
            window = driver.get_window_rect()
            driver.set_window_rect(
                x=0,
                y=0,
                width=int(window["width"]) + missing_width,
                height=int(window["height"]) + missing_height,
            )

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
        replacements: Mapping[str, object] | None = None,
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

    def enable_flash(self, driver):
        if self.electron:
            logger.info(
                "Skipping Chromium Flash permission setup for Electron browser."
            )
            return
        current_url = driver.current_url

        driver.get(
            "chrome://settings/content/siteDetails?site="
            + urllib.parse.quote(current_url)
        )

        deadline = time.monotonic() + FLASH_PERMISSION_WAIT_SECONDS
        result = {"status": "not-found"}
        while True:
            result = driver.execute_script(FLASH_PERMISSION_SCRIPT)
            status = result["status"]

            if status in {"allowed", "changed"}:
                logger.info("Enabled Flash through Chromium site settings.")
                break

            if status in {"disabled", "allow-unavailable", "change-failed"}:
                raise RuntimeError(
                    "Could not enable Flash in Chromium site settings: "
                    f"the Flash permission control is {status.replace('-', ' ')}."
                )

            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "Could not locate a usable Flash permission control in "
                    "Chromium site settings."
                )

            time.sleep(FLASH_PERMISSION_POLL_SECONDS)

        driver.get(current_url)
