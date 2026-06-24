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