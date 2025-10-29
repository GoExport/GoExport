# GoExport Configuration Reference

Complete reference for `config.py` settings, resolution matrices, aspect ratios, and service configuration.

## Table of Contents

- [Application Configuration](#application-configuration)
- [Server Settings](#server-settings)
- [Aspect Ratios & Resolutions](#aspect-ratios--resolutions)
- [Service Configuration](#service-configuration)
- [Outro Configuration](#outro-configuration)
- [Dependencies Configuration](#dependencies-configuration)
- [Data Persistence](#data-persistence)

## Application Configuration

### Basic Application Settings

```python
APP_NAME = "GoExport"
APP_REPO = "goexport/goexport"
APP_VERSION = "0.16.0"
APP_BETA = False
```

**`APP_NAME`** - Application display name  
**`APP_REPO`** - GitHub repository identifier for update checks  
**`APP_VERSION`** - Current version string (semantic versioning)  
**`APP_BETA`** - Beta release flag (affects update channel)

### File and Folder Names

```python
DEFAULT_DEPENDENCIES_FILENAME = "dependencies"
DEFAULT_LIBS_FILENAME = "libs"
DEFAULT_SERVER_FILENAME = "server"
DEFAULT_OUTPUT_FILENAME = "data"
DEFAULT_ASSETS_FILENAME = "assets"
DEFAULT_GUI_FILENAME = "gui"
DEFAULT_OUTROS_FILENAME = "outro"
DEFAULT_FOLDER_OUTPUT_FILENAME = "output"
```

These constants define the directory structure:

```
GoExport/
├── dependencies/    # FFmpeg, Chromium, etc.
├── libs/            # Native capture libraries
├── server/          # Local web server files
├── assets/          # UI assets and outros
│   └── outro/       # Outro video files
├── gui/             # PyQt6 UI files
├── output/          # Exported videos
└── data.json        # User preferences
```

### Output Settings

```python
DEFAULT_OUTPUT_EXTENSION = ".mp4"
```

All exported videos are saved as `.mp4` (H.264/AAC).

## Server Settings

### GoExport Local Server

```python
SERVER_HOST = "localhost"
SERVER_PORT = 26519
SERVER_PROTOCOL = "http"
```

Used for serving local video player when `"host": True` in service config.

**Full URL:** `http://localhost:26519`

### OBS WebSocket Server

```python
OBS_SERVER_HOST = "localhost"
OBS_SERVER_PORT = 4455
OBS_SERVER_PASSWORD = ""
OBS_FPS = 60
```

Default connection settings for OBS Studio WebSocket.

**Configuration:**

- **Host:** Where OBS is running (usually `localhost`)
- **Port:** OBS WebSocket port (default: 4455)
- **Password:** Set in OBS → Tools → WebSocket Server Settings
- **FPS:** Recording frame rate (24, 30, 60, 120)

Override via command-line:

```bash
GoExport.exe --obs-websocket-port 4455 --obs-websocket-password "mypass" --obs-fps 60
```

### Wrapper Server

```python
WRAPPER_SERVER_HOST = "127.0.0.1"
WRAPPER_SERVER_PORT = 4343
WRAPPER_SERVER_PROTOCOL = "http"
```

Connection settings for Wrapper: Offline server.

**Full URL:** `http://127.0.0.1:4343`

## Aspect Ratios & Resolutions

### Available Aspect Ratios

```python
AVAILABLE_ASPECT_RATIOS = [
    "4:3",    # Classic/Standard
    "14:9",   # Transitional
    "9:16",   # Vertical/Mobile
    "16:9",   # Widescreen (most common)
]
```

### Resolution Matrix

```python
AVAILABLE_SIZES = {
    "aspect_ratio": {
        "label": (width, height, is_wide),
    }
}
```

**Format:** `(width: int, height: int, is_wide: bool)`

- **width/height:** Pixel dimensions
- **is_wide:** Flag for outro selection

### 4:3 (Classic) Resolutions

```python
"4:3": {
    "240p": (320, 240, False),
    "360p": (480, 360, False),
    "420p": (560, 420, False),
    "480p": (640, 480, False),
}
```

**Use case:** Classic computer monitors, old videos

### 14:9 (Transitional) Resolutions

```python
"14:9": {
    "360p": (640, 360, False),
    "480p": (854, 480, False),
    "720p": (1280, 720, False),
    "1080p": (1920, 1080, False),
    "2k": (2560, 1440, False),
    "4k": (3840, 2160, False),
    "5k": (5120, 2880, False),
    "8k": (7680, 4320, False),
}
```

**Use case:** Transitional format between 4:3 and 16:9

### 16:9 (Widescreen) Resolutions

```python
"16:9": {
    "360p": (640, 360, True),
    "480p": (854, 480, True),
    "720p": (1280, 720, True),
    "1080p": (1920, 1080, True),
    "2k": (2560, 1440, True),
    "4k": (3840, 2160, True),
    "5k": (5120, 2880, True),
    "8k": (7680, 4320, True),
}
```

**Use case:** Most modern videos, YouTube standard

**Note:** `is_wide=True` uses wide outro files

### 9:16 (Vertical) Resolutions

```python
"9:16": {
    "360p": (360, 640, False),
    "480p": (480, 854, False),
    "720p": (720, 1280, False),
    "1080p": (1080, 1920, False),
    "2k": (1440, 2560, False),
    "4k": (2160, 3840, False),
    "5k": (2880, 5120, False),
    "8k": (4320, 7680, False),
}
```

**Use case:** Mobile videos, TikTok, Instagram Stories

### Adding Custom Resolutions

To add a custom resolution:

```python
AVAILABLE_SIZES = {
    "16:9": {
        "360p": (640, 360, True),
        # Add custom resolution
        "custom": (1366, 768, True),  # Example: 1366x768
    }
}
```

**Requirements:**

- Resolution label must be unique within aspect ratio
- Width and height must match aspect ratio
- `is_wide` determines outro type (True for 16:9-ish)

## Service Configuration

### Service Dictionary Structure

```python
AVAILABLE_SERVICES = {
    "service_id": {
        "name": str,              # Required
        "requires": set,          # Optional
        "domain": list,           # Optional
        "player": list,           # Optional
        "host": bool,             # Optional, default: False
        "hostable": bool,         # Optional, default: False
        "legacy": bool,           # Optional, default: False
        "testing": bool,          # Optional, default: False
        "hidden": bool,           # Optional, default: False
        "window": str,            # Optional
        "afterloadscripts": list, # Optional
    }
}
```

### Field Descriptions

#### `name` (Required)

Display name shown in UI.

```python
"name": "Wrapper: Offline"
```

#### `requires` (Optional)

Set of required parameters for this service.

```python
"requires": {
    "movieId",         # Video ID required
    "movieOwnerId",    # Owner ID required
}
```

**Valid values:**

- `"movieId"` - Video/Movie ID
- `"movieOwnerId"` - Owner/User ID

#### `domain` (Optional)

List of allowed domains for browser navigation.

```python
"domain": [
    "https://flashthemes.net",
    "https://api.flashthemes.net",
]
```

**Purpose:** Browser automation security - only navigate to these domains

#### `player` (Optional)

Player URL pattern with placeholders.

```python
"player": [
    "https://example.com/player",
    "?video={movie_id}&owner={owner_id}&w={width}&h={height}&wide={wide}"
]
```

**Placeholders:**

- `{movie_id}` - Movie/Video ID
- `{owner_id}` - Owner/User ID
- `{width}` - Video width in pixels
- `{height}` - Video height in pixels
- `{wide}` - Boolean ("1" or "0") for widescreen
- `{store}` - Store path (service-specific)
- `{client_theme}` - Client theme path (service-specific)

**Format:**

- Element 0: Base URL
- Element 1+: Query string parts (joined automatically)

#### `host` (Optional)

Whether to start local web server.

```python
"host": True  # Start server on SERVER_HOST:SERVER_PORT
```

**Default:** `False`

**Use case:** Services that need local player hosting

#### `hostable` (Optional)

Whether service can be hosted locally.

```python
"hostable": True
```

**Default:** `False`

#### `legacy` (Optional)

Use legacy editor mode instead of modern editor.

```python
"legacy": False
```

**Default:** `False`

**Note:** Legacy editor uses different trimming logic

#### `testing` (Optional)

Hide service from UI (for development).

```python
"testing": True
```

**Default:** `False`

**Use case:** Work-in-progress services not ready for users

#### `hidden` (Optional)

Hide from UI permanently.

```python
"hidden": True
```

**Default:** `False`

#### `window` (Optional)

Window title for capture software to target.

```python
"window": "GoExport Viewer"
```

**Purpose:** OBS/Native capture uses this to find the browser window

#### `afterloadscripts` (Optional)

JavaScript to inject after page loads.

```python
"afterloadscripts": [
    "console.log('Loaded!');",
    "document.title = 'Custom Title';",
]
```

**Use case:** Customize player behavior, remove ads, inject controls

### Example Services

#### Wrapper: Offline

```python
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
    "hidden": False,
    "window": "GoExport Viewer",
    "afterloadscripts": []
}
```

#### FlashThemes

```python
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
        "https://flashthemes.net"
    ],
    "host": False,
    "hostable": False,
    "legacy": False,
    "testing": False,
    "hidden": False,
    "window": "FlashThemes",
    "afterloadscripts": [
        "document.open();",
        "document.write(\"...\");",  # Embedded player HTML
        "document.close();"
    ]
}
```

### Adding New Services

See [ADDING_NEW_SERVICES.md](ADDING_NEW_SERVICES.md) for detailed guide.

Quick example:

```python
"my_service": {
    "name": "My Custom Service",
    "requires": {"movieId"},
    "domain": ["https://myservice.com"],
    "player": [
        "https://myservice.com/embed",
        "?id={movie_id}&w={width}&h={height}"
    ],
    "window": "My Service Player",
}
```

## Outro Configuration

### Outro File Paths

Outros are organized by aspect ratio category:

```python
# Wide (16:9)
OUTRO_WIDE_8K = ["assets", "outro", "wide", "7680x4320.mp4"]
OUTRO_WIDE_5K = ["assets", "outro", "wide", "5120x2880.mp4"]
OUTRO_WIDE_4K = ["assets", "outro", "wide", "3840x2160.mp4"]
OUTRO_WIDE_2K = ["assets", "outro", "wide", "2560x1440.mp4"]
OUTRO_WIDE_1080P = ["assets", "outro", "wide", "1920x1080.mp4"]
OUTRO_WIDE_720P = ["assets", "outro", "wide", "1280x720.mp4"]
OUTRO_WIDE_480P = ["assets", "outro", "wide", "854x480.mp4"]
OUTRO_WIDE_360P = ["assets", "outro", "wide", "640x360.mp4"]

# Standard (4:3)
OUTRO_STANDARD_480P = ["assets", "outro", "standard", "640x480.mp4"]
OUTRO_STANDARD_420P = ["assets", "outro", "standard", "560x420.mp4"]
OUTRO_STANDARD_360P = ["assets", "outro", "standard", "480x360.mp4"]
OUTRO_STANDARD_240P = ["assets", "outro", "standard", "320x240.mp4"]

# Classic (14:9)
OUTRO_CLASSIC_848x576 = ["assets", "outro", "classic", "848x576.mp4"]
OUTRO_CLASSIC_768x576 = ["assets", "outro", "classic", "768x576.mp4"]
OUTRO_CLASSIC_720x480 = ["assets", "outro", "classic", "720x480.mp4"]
OUTRO_CLASSIC_640x432 = ["assets", "outro", "classic", "640x432.mp4"]

# Tall (9:16)
OUTRO_TALL_1080P = ["assets", "outro", "tall", "1080x1920.mp4"]
OUTRO_TALL_720P = ["assets", "outro", "tall", "720x1280.mp4"]
OUTRO_TALL_480P = ["assets", "outro", "tall", "480x854.mp4"]
OUTRO_TALL_360P = ["assets", "outro", "tall", "360x640.mp4"]
```

### Outro Selection Logic

GoExport selects outros based on:

1. **Aspect ratio category** (wide/standard/classic/tall)
2. **Exact resolution match**

**Algorithm:**

```python
if is_wide:
    outro_folder = "wide"
elif aspect_ratio == "4:3":
    outro_folder = "standard"
elif aspect_ratio == "14:9":
    outro_folder = "classic"
elif aspect_ratio == "9:16":
    outro_folder = "tall"

outro_file = f"{width}x{height}.mp4"
outro_path = f"assets/outro/{outro_folder}/{outro_file}"
```

### Adding Custom Outros

To add custom outro:

1. Create outro video matching exact resolution
2. Save as MP4 (H.264 video, AAC audio)
3. Place in appropriate folder:
   - `assets/outro/wide/` - 16:9 videos
   - `assets/outro/standard/` - 4:3 videos
   - `assets/outro/classic/` - 14:9 videos
   - `assets/outro/tall/` - 9:16 videos
4. Name file `{width}x{height}.mp4`

**Example:**

```bash
# Custom 2560x1440 outro for 16:9
assets/outro/wide/2560x1440.mp4
```

**Technical Requirements:**

- Codec: H.264 (libx264)
- Audio: AAC
- Frame rate: Match video export FPS
- Duration: Typically 3-10 seconds

## Dependencies Configuration

### Windows Dependencies

```python
PATH_FFMPEG_WINDOWS = ["dependencies", "ffmpeg", "bin", "ffmpeg.exe"]
PATH_FFPROBE_WINDOWS = ["dependencies", "ffmpeg", "bin", "ffprobe.exe"]
PATH_FFPLAY_WINDOWS = ["dependencies", "ffmpeg", "bin", "ffplay.exe"]
PATH_CHROMIUM_WINDOWS = ["dependencies", "ungoogled-chromium", "chrome.exe"]
PATH_CHROMEDRIVER_WINDOWS = ["dependencies", "chromedriver", "chromedriver.exe"]
PATH_OBS_WINDOWS = ["C:\\Program Files", "obs-studio", "bin", "64bit", "obs64.exe"]
PATH_FLASH_WINDOWS = ["dependencies", "ungoogled-chromium", "extensions", "pepflashplayer.dll"]
PATH_FLASH_VERSION_WINDOWS = "34.0.0.330"
```

### Linux Dependencies

```python
PATH_FFMPEG_LINUX = ["dependencies", "ffmpeg", "bin", "ffmpeg"]
PATH_FFPROBE_LINUX = ["dependencies", "ffmpeg", "bin", "ffprobe"]
PATH_FFPLAY_LINUX = ["dependencies", "ffmpeg", "bin", "ffplay"]
PATH_CHROMIUM_LINUX = ["dependencies", "ungoogled-chromium", "chrome"]
PATH_CHROMEDRIVER_LINUX = ["dependencies", "ungoogled-chromium", "chromedriver"]
PATH_OBS_LINUX = None  # OBS installed via system package manager
PATH_FLASH_LINUX = ["dependencies", "ungoogled-chromium", "extensions", "libpepflashplayer.so"]
PATH_FLASH_VERSION_LINUX = "34.0.0.137"
```

**Note:** Linux users typically install OBS system-wide via:

```bash
sudo apt install obs-studio  # Debian/Ubuntu
sudo dnf install obs-studio  # Fedora
```

### Path Resolution

Paths are resolved using `helpers.get_path()`:

```python
def get_path(base, path_array):
    """
    Joins path array into full path.
    Example: ["dependencies", "ffmpeg", "bin", "ffmpeg.exe"]
          -> "dependencies/ffmpeg/bin/ffmpeg.exe"
    """
    return os.path.join(base, *path_array)
```

## Data Persistence

### data.json Structure

User preferences are saved in `data.json`:

```json
{
  "service": "local",
  "aspect_ratio": "16:9",
  "resolution": "1080p",
  "movie_id": "m-123",
  "owner_id": "user456",
  "obs_websocket_address": "localhost",
  "obs_websocket_port": 4455,
  "use_outro": true,
  "last_output_folder": "D:\\Videos\\GoExport"
}
```

### Saving Data

```python
import helpers

# Save single value
helpers.save("resolution", "1080p")

# Save complex data
helpers.save("recent_videos", ["m-001", "m-002", "m-003"])
```

### Loading Data

```python
import helpers

# Load with default
resolution = helpers.load("resolution", "360p")

# Load without default (returns False if not found)
service = helpers.load("service")
```

### Memory Storage (Runtime Only)

For temporary runtime data:

```python
import helpers

# Store in memory
helpers.remember("current_clip_duration", 120.5)

# Retrieve from memory
duration = helpers.recall("current_clip_duration")

# Clear from memory
helpers.forget("current_clip_duration")
```

**Note:** Memory storage is cleared when application exits.

## Development Settings

```python
DEBUG_MODE = False
SKIP_COMPAT = False
FORCE_WINDOW = False
```

**`DEBUG_MODE`** - Enable debug features and logging  
**`SKIP_COMPAT`** - Skip compatibility checks on startup  
**`FORCE_WINDOW`** - Force windowed mode (disable headless browser)

## Miscellaneous

### Update Check Interval

```python
UPDATE_CHECK_INTERVAL = 60 * 1000  # 1 minute in milliseconds
```

Controls how often GoExport checks for updates.

### Browser Configuration

```python
BROWSER_NAME = "Chromium"
```

Display name for browser automation logs.

## See Also

- [ADDING_NEW_SERVICES.md](ADDING_NEW_SERVICES.md) - Service creation guide
- [PARAMETERS.md](PARAMETERS.md) - CLI parameter reference
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development setup guide
- [README.md](../readme.md) - Main documentation
