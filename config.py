# Configuration
APP_NAME = "GoExport"
APP_VERSION = "0.10.0"
APP_BETA = True
DEFAULT_DEPENDENCIES_FILENAME = "dependencies"
DEFAULT_LIBS_FILENAME = "libs"
DEFAULT_SERVER_FILENAME = "server"
DEFAULT_OUTPUT_FILENAME = "data"
DEFAULT_ASSETS_FILENAME = "assets"
DEFAULT_OUTROS_FILENAME = "outro"
DEFAULT_FOLDER_OUTPUT_FILENAME = "output"
DEFAULT_STANDARD_OUTROS_FILENAME = "standard"
DEFAULT_WIDE_OUTROS_FILENAME = "wide"
DEFAULT_CLASSIC_OUTROS_FILENAME = "classic"
DEFAULT_TALL_OUTROS_FILENAME = "tall"
DEFAULT_OUTPUT_EXTENSION = ".mp4"

# Server
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 26519
SERVER_PROTOCOL = "http"

AVAILABLE_ASPECT_RATIOS = [
    "4:3",
    "14:9",
    "9:16",
    "16:9",
]

AVAILABLE_SIZES = {
    # 4:3
    "4:3": {
        "320x240": (320, 240, False),
        "480x360": (480, 360, False),
        "560x420": (560, 420, False),
        "640x480": (640, 480, False),
    },

    # 14:9
    "14:9": {
        "640x432": (640, 432, False),
        "720x480": (720, 480, False),
        "768x576": (768, 576, False),
        "848x576": (848, 576, False),
    },

    # 16:9
    "16:9": {
        "640x360": (640, 360, True),
        "854x480": (854, 480, True),
        "1280x720": (1280, 720, True),
        "1920x1080": (1920, 1080, True),
    },

    # 9:16
    "9:16": {
        "360x640": (360, 640, False),
        "480x854": (480, 854, False),
        "720x1280": (720, 1280, False),
        "1080x1920": (1080, 1920, False),
    },
}

AVAILABLE_SERVICES = {
    "local": {
        "name": "Local",
        "requires": {
            "movieId",
        },
        "domain": ["http://127.0.0.1:4343"],
        "player": [
            f"{SERVER_PROTOCOL}://{SERVER_HOST}:{SERVER_PORT}",
            "index.html?environment=local&movieId={movie_id}&playerWidth={width}&playerHeight={height}&isWide={wide}&isVideoRecord=1",
        ],
    },
    "ft": {
        "name": "FlashThemes",
        "requires": {
            "movieId",
            "movieOwnerId",
        },
        "domain": ["https://flashthemes.net"],
        "player": [
            f"{SERVER_PROTOCOL}://{SERVER_HOST}:{SERVER_PORT}",
            "index.html?environment=ft&swf=https://lightspeed.flashthemes.net/static/animation/aisd82ij/player.swf?v=2&movieId={movie_id}&ownerId={owner_id}&playerWidth={width}&playerHeight={height}&isWide={wide}&isVideoRecord=1&ut=-1&apiserver=https://flashthemes.net/&autostart=1&storePath=https://flashthemes.net/static/store/<store>?v={owner_id}&clientThemePath=https://lightspeed.flashthemes.net/static/ct/ad44370a650793d9/<client_theme>&isEmbed=1&chain_mids=&ad=0&endStyle=1&isWide={wide}&pwm=1&isSpeedy=1&allowFullScreen=true&allowScriptAccess=always",
        ],
    },
}

# Outros
OUTRO_WIDE_1920x1080 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_WIDE_OUTROS_FILENAME, "1920x1080.mp4"]
OUTRO_WIDE_1280x720 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_WIDE_OUTROS_FILENAME, "1280x720.mp4"]
OUTRO_WIDE_854x480 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_WIDE_OUTROS_FILENAME, "854x480.mp4"]
OUTRO_WIDE_640x360 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_WIDE_OUTROS_FILENAME, "640x360.mp4"]

OUTRO_STANDARD_320x240 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_STANDARD_OUTROS_FILENAME, "320x240.mp4"]
OUTRO_STANDARD_480x360 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_STANDARD_OUTROS_FILENAME, "480x360.mp4"]
OUTRO_STANDARD_560x420 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_STANDARD_OUTROS_FILENAME, "560x420.mp4"]
OUTRO_STANDARD_640x480 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_STANDARD_OUTROS_FILENAME, "640x480.mp4"]

OUTRO_CLASSIC_848x576 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_CLASSIC_OUTROS_FILENAME, "848x576.mp4"]
OUTRO_CLASSIC_768x576 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_CLASSIC_OUTROS_FILENAME, "768x576.mp4"]
OUTRO_CLASSIC_720x480 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_CLASSIC_OUTROS_FILENAME, "720x480.mp4"]
OUTRO_CLASSIC_640x432 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_CLASSIC_OUTROS_FILENAME, "640x432.mp4"]

OUTRO_TALL_1080x1920 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_TALL_OUTROS_FILENAME, "1080x1920.mp4"]
OUTRO_TALL_720x1280 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_TALL_OUTROS_FILENAME, "720x1280.mp4"]
OUTRO_TALL_480x854 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_TALL_OUTROS_FILENAME, "480x854.mp4"]
OUTRO_TALL_360x640 = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, DEFAULT_TALL_OUTROS_FILENAME, "360x640.mp4"]

# Dependencies for Windows
PATH_FFMPEG_WINDOWS = [DEFAULT_DEPENDENCIES_FILENAME, "ffmpeg", "bin", "ffmpeg.exe"]
PATH_FFPROBE_WINDOWS = [DEFAULT_DEPENDENCIES_FILENAME, "ffmpeg", "bin", "ffprobe.exe"]
PATH_FFPLAY_WINDOWS = [DEFAULT_DEPENDENCIES_FILENAME, "ffmpeg", "bin", "ffplay.exe"]
PATH_CHROMIUM_WINDOWS = [DEFAULT_DEPENDENCIES_FILENAME, "ungoogled-chromium", "chrome.exe"]
PATH_CHROMEDRIVER_WINDOWS = [DEFAULT_DEPENDENCIES_FILENAME, "chromedriver", "chromedriver.exe"]

# Dependencies for Linux
# PATH_FFMPEG_LINUX  = helpers.search_path("ffmpeg")
# PATH_FFPROBE_LINUX = helpers.search_path("ffprobe")
# PATH_FFPLAY_LINUX  = helpers.search_path("ffplay")
# PATH_CHROMIUM_LINUX = helpers.search_path("chromium-browser") or helpers.search_path("chromium")
# PATH_CHROMEDRIVER_LINUX = helpers.search_path("chromedriver")

# Development Settings
DEBUG_MODE = False
SKIP_COMPAT = False
