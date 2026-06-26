from pathlib import Path
import platform
import sys

APP_NAME = "GoExport"
VERSION = "2.0.0"

SUPPORTED_FORMATS = {
    "mp4",
    "avi",
    "mov",
    "mkv",
    "gif",
}

if getattr(sys, "frozen", False):
    # dist/GoExport
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # Project root
    BASE_DIR = Path(__file__).resolve().parent.parent

SYSTEM = platform.system()

CHROMIUM_DIR = BASE_DIR / "bin" / "ungoogled-chromium"
FFMPEG_DIR = BASE_DIR / "bin" / "ffmpeg"
RESOURCES_DIR = BASE_DIR / "resources"

if SYSTEM == "Windows":
    CHROME_PATH = CHROMIUM_DIR / "chrome.exe"
    CHROMEDRIVER_PATH = CHROMIUM_DIR / "chromedriver.exe"
    FFMPEG_PATH = FFMPEG_DIR / "bin" / "ffmpeg.exe"
    FLASH_PLUGIN_PATH = CHROMIUM_DIR / "extensions" / "pepflashplayer.dll"
    FLASH_PLUGIN_VERSION = "34.0.0.330"

elif SYSTEM == "Linux":
    CHROME_PATH = CHROMIUM_DIR / "chrome"
    CHROMEDRIVER_PATH = CHROMIUM_DIR / "chromedriver"
    FFMPEG_PATH = FFMPEG_DIR / "bin" / "ffmpeg"
    FLASH_PLUGIN_PATH = CHROMIUM_DIR / "extensions" / "libpepflashplayer.so"
    FLASH_PLUGIN_VERSION = "32.0.0.xxx"  # Whatever version you're shipping

elif SYSTEM == "Darwin":
    CHROME_PATH = CHROMIUM_DIR / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
    CHROMEDRIVER_PATH = CHROMIUM_DIR / "chromedriver"
    FFMPEG_PATH = FFMPEG_DIR / "bin" / "ffmpeg"
    FLASH_PLUGIN_PATH = CHROMIUM_DIR / "extensions" / "PepperFlashPlayer.plugin"
    FLASH_PLUGIN_VERSION = "..."

else:
    raise RuntimeError(f"Unsupported operating system: {SYSTEM}")

TEMPLATE_HTML_PATH = RESOURCES_DIR / "template.html"

OUTPUT_FORMAT = "mp4"

IS_WIDE = True
WIDTH = 1280
HEIGHT = 720
FPS = 24

URL = "http://localhost:4343/"
API_URL = "http://localhost:4343/"
SWF_URL = "http://localhost:4664/animation/414827163ad4eb60/player.swf"

STORE_PATH = "http://localhost:4664/store/3a981f5cb2739137/<store>"
CLIENT_THEME_PATH = "http://localhost:4664/static/ad44370a650793d9/<client_theme>"