from pathlib import Path


APP_NAME = "GoExport"
VERSION = "2.0.0"

SUPPORTED_FORMATS = {
    "mp4",
    "avi",
    "mov",
    "mkv",
    "gif",
}

BASE_DIR = Path(__file__).resolve().parent.parent

CHROME_PATH = BASE_DIR / "bin" / "ungoogled-chromium" / "chrome.exe"
CHROMEDRIVER_PATH = BASE_DIR / "bin" / "ungoogled-chromium" / "chromedriver.exe"
FFMPEG_PATH = BASE_DIR / "bin" / "ffmpeg" / "bin" / "ffmpeg.exe"
FLASH_PLUGIN_PATH = BASE_DIR / "bin" / "ungoogled-chromium" / "extensions" / "pepflashplayer.dll"
PATH_FLASH_VERSION_WINDOWS = "34.0.0.330"
TEMPLATE_HTML_PATH = BASE_DIR / "resources" / "template.html"
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