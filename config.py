# Configuration
APP_NAME = "GoExport"
APP_VERSION = "0.15.3"
APP_BETA = False
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
SERVER_HOST = "localhost"
SERVER_PORT = 26519
SERVER_PROTOCOL = "http"

# OBS Server
OBS_SERVER_HOST = "localhost"
OBS_SERVER_PORT = 4455
OBS_SERVER_PASSWORD = ""
OBS_FPS = 60

# Wrapper Server
WRAPPER_SERVER_HOST = "127.0.0.1"
WRAPPER_SERVER_PORT = 4343
WRAPPER_SERVER_PROTOCOL = "http"

AVAILABLE_ASPECT_RATIOS = [
    "4:3",
    "14:9",
    "9:16",
    "16:9",
]

AVAILABLE_SIZES = {
    # 4:3
    "4:3": {
        "240p": (320, 240, False),
        "360p": (480, 360, False),
        "420p": (560, 420, False),
        "480p": (640, 480, False),
    },

    # 14:9
    "14:9": {
        "360p": (640, 360, False),
        "480p": (854, 480, False),
        "720p": (1280, 720, False),
        "1080p": (1920, 1080, False),
    },

    # 16:9
    "16:9": {
        "360p": (640, 360, True),
        "480p": (854, 480, True),
        "720p": (1280, 720, True),
        "1080p": (1920, 1080, True),
    },

    # 9:16
    "9:16": {
        "360p": (360, 640, False),
        "480p": (480, 854, False),
        "720p": (720, 1280, False),
        "1080p": (1080, 1920, False),
    },
}

AVAILABLE_SERVICES = {
    "local": {
        "name": "Wrapper: Offline",
        "requires": {
            "movieId",
        },
        "domain": [
            f"{WRAPPER_SERVER_PROTOCOL}://{WRAPPER_SERVER_HOST}:{WRAPPER_SERVER_PORT}",
        ],
        "player": [
            f"{SERVER_PROTOCOL}://{SERVER_HOST}:{SERVER_PORT}",
            (
                "index.html?"
                "environment=local"
                "&movieId={movie_id}"
                "&playerWidth={width}"
                "&playerHeight={height}"
                "&isWide={wide}"
                "&isVideoRecord=1"
            ),
        ],
        "host": True,
        "hostable": True,
        "legacy": False,
        "testing": False,
        "window": "GoExport Viewer",
        "afterloadscripts": []
    },
    "ft": {
        "name": "FlashThemes",
        "requires": {
            "movieId",
            "movieOwnerId",
        },
        "domain": [
            "https://flashthemes.net",
        ],
        "player": [
            f"https://flashthemes.net"
        ],
        "host": False,
        "hostable": False,
        "legacy": False,
        "testing": False,
        "window": "FlashThemes",
        "afterloadscripts": [
            "document.open();",
            "document.write(\"<!DOCTYPE html><html><head><title>FlashThemes</title><style>html,body{{margin:0;padding:0;width:100%;height:100%;overflow:hidden}}object,embed{{width:100%;height:100%}}</style><script>function obj_DoFSCommand(command,args){{switch(command){{case'start':startRecord=Date.now();console.log('Video started '+startRecord);if(document.getElementById('obj').pause)document.getElementById('obj').pause();if(document.getElementById('obj').seek)document.getElementById('obj').seek(0);break;case'stop':stopRecord=Date.now();console.log('Video stopped '+stopRecord);break;}}}}</script></head><body><object type=\\\"application/x-shockwave-flash\\\" data=\\\"https://lightspeed.flashthemes.net/static/animation/aisd82ij/player.swf?v=2\\\" width=\\\"100%\\\" height=\\\"100%\\\" id=\\\"obj\\\"><param name=\\\"movie\\\" value=\\\"https://lightspeed.flashthemes.net/static/animation/aisd82ij/player.swf?v=2\\\"/><param name=\\\"allowFullScreen\\\" value=\\\"true\\\"/><param name=\\\"allowScriptAccess\\\" value=\\\"always\\\"/><param name=\\\"flashvars\\\" value=\\\"autostart=1&amp;isWide={wide}&amp;ut=-1&amp;isEmbed=1&amp;playerWidth={width}&amp;playerHeight={height}&amp;apiserver=https://flashthemes.net/&amp;storePath=https://flashthemes.net/static/store/<store>?v={owner_id}&amp;clientThemePath=https://lightspeed.flashthemes.net/static/ct/ad44370a650793d9/<client_theme>&amp;movieId={movie_id}&amp;isVideoRecord=1&amp;isSpeedy=0\\\"/></object></body></html>\");"
            "document.close();"
        ]
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
PATH_OBS_WINDOWS = ["C:\\Program Files", "obs-studio", "bin", "64bit", "obs64.exe"]
PATH_FLASH_WINDOWS = [DEFAULT_DEPENDENCIES_FILENAME, "ungoogled-chromium", 'extensions', "pepflashplayer.dll"]
PATH_FLASH_VERSION_WINDOWS = "34.0.0.330"

# Dependencies for Linux
PATH_FFMPEG_LINUX  = [DEFAULT_DEPENDENCIES_FILENAME, "ffmpeg", "bin", "ffmpeg"]
PATH_FFPROBE_LINUX = [DEFAULT_DEPENDENCIES_FILENAME, "ffmpeg", "bin", "ffprobe"]
PATH_FFPLAY_LINUX  = [DEFAULT_DEPENDENCIES_FILENAME, "ffmpeg", "bin", "ffplay"]
PATH_CHROMIUM_LINUX = [DEFAULT_DEPENDENCIES_FILENAME, "ungoogled-chromium", "chrome"]
PATH_CHROMEDRIVER_LINUX = [DEFAULT_DEPENDENCIES_FILENAME, "ungoogled-chromium", "chromedriver"]
PATH_OBS_LINUX = None
PATH_FLASH_LINUX = [DEFAULT_DEPENDENCIES_FILENAME, "ungoogled-chromium", 'extensions', "libpepflashplayer.so"]
PATH_FLASH_VERSION_LINUX = "34.0.0.137"

# Data
UPDATE_CHECK_INTERVAL = 60 * 1000  # 1 minute in milliseconds
PATH_DATA_FILE = ["data.json"]

# Development Settings
DEBUG_MODE = False
SKIP_COMPAT = False
