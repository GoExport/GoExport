# Configuration
APP_NAME = "GoExport"
APP_VERSION = "0.5.1"
DEFAULT_DEPENDENCIES_FILENAME = "dependencies"
DEFAULT_LIBS_FILENAME = "libs"
DEFAULT_OUTPUT_FILENAME = "data"
DEFAULT_ASSETS_FILENAME = "assets"
DEFAULT_OUTROS_FILENAME = "outro"
DEFAULT_OUTPUT_EXTENSION = ".mp4"

AVAILABLE_SIZES = {
    # 4:3
    "320x240": (320, 240, False),
    "480x360": (480, 360, False),
    "560x420": (560, 420, False),
    "640x480": (640, 480, False),

    # 14:9
    "640x432": (640, 432, False),
    "720x480": (720, 480, False),
    "768x576": (768, 576, False),
    "848x576": (848, 576, False),

    # 16:9
    "640x360": (640, 360, True),
    "854x480": (854, 480, True),
    "1280x720": (1280, 720, True),
    "1920x1080": (1920, 1080, True),
}

AVAILABLE_SERVICES = {
    "local": {
        "name": "Local",
        "requires": {
            "movieId",
        },
        "domain": ["http://127.0.0.1:4343"],
        "player": [
            "https://goexport.github.io",
            "Universal-Wrapper-Player",
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
            "https://goexport.github.io",
            "Universal-Wrapper-Player",
            "index.html?environment=ft&swf=https://lightspeed.flashthemes.net/static/animation/aisd82ij/player.swf?v=2&movieId={movie_id}&ownerId={owner_id}&playerWidth={width}&playerHeight={height}&isWide={wide}&isVideoRecord=1&ut=-1&apiserver=https://flashthemes.net/&autostart=1&storePath=https://flashthemes.net/static/store/<store>?v={owner_id}&clientThemePath=https://lightspeed.flashthemes.net/static/ct/ad44370a650793d9/<client_theme>&isEmbed=1&chain_mids=&ad=0&endStyle=1&isWide={wide}&pwm=1&isSpeedy=1&allowFullScreen=true&allowScriptAccess=always",
        ],
    },
}

# Outros
OUTRO_WIDE = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, "Wide.mp4"]
OUTRO_STANDARD = [DEFAULT_ASSETS_FILENAME, DEFAULT_OUTROS_FILENAME, "Default.mp4"]

# Dependencies
PATH_FFMPEG = [DEFAULT_DEPENDENCIES_FILENAME, "ffmpeg", "bin", "ffmpeg.exe"]
PATH_FFPROBE = [DEFAULT_DEPENDENCIES_FILENAME, "ffmpeg", "bin", "ffprobe.exe"]
PATH_FFPLAY = [DEFAULT_DEPENDENCIES_FILENAME, "ffmpeg", "bin", "ffplay.exe"]
PATH_CHROMIUM = [DEFAULT_DEPENDENCIES_FILENAME, "ungoogled-chromium", "chrome.exe"]
PATH_CHROMEDRIVER = [DEFAULT_DEPENDENCIES_FILENAME, "chromedriver", "chromedriver.exe"]
PATH_LIBS_RECORD_64 = [DEFAULT_LIBS_FILENAME, "screen-capture-recorder-x64.dll"]
PATH_LIBS_RECORD_32 = [DEFAULT_LIBS_FILENAME, "screen-capture-recorder.dll"]
PATH_LIBS_AUDIO_64 = [DEFAULT_LIBS_FILENAME, "audio_sniffer-x64.dll"]
PATH_LIBS_AUDIO_32 = [DEFAULT_LIBS_FILENAME, "audio_sniffer.dll"]
PATH_FLASH = ["Program Files (x86)", "Flash Player", "FlashUtil_Uninstall.exe"]

# Development Settings
DEBUG_MODE = False
SKIP_COMPAT = False
