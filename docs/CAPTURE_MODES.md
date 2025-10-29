# GoExport Capture Modes

Complete guide to OBS and Native capture modes, including setup, configuration, and troubleshooting.

## Table of Contents

- [Overview](#overview)
- [OBS Capture Mode](#obs-capture-mode)
- [Native Capture Mode](#native-capture-mode)
- [Comparison](#comparison)
- [Auto-Detection](#auto-detection)
- [Troubleshooting](#troubleshooting)

## Overview

GoExport supports two capture methods for recording Flash content:

1. **OBS Mode** - Uses OBS Studio via WebSocket API (Recommended)
2. **Native Mode** - Uses screen-capture-recorder (Windows only)

The application automatically detects which mode is available and uses the best option.

## OBS Capture Mode

### What is OBS Mode?

OBS Mode connects to OBS Studio via WebSocket API to control recording. This provides:

- **Higher quality** - Professional-grade encoding
- **Better performance** - Hardware acceleration support
- **Cross-platform** - Works on Windows, Linux, macOS
- **More control** - Customizable encoding settings

### Requirements

1. **OBS Studio** (v28.0.0 or later)

   - Download: https://obsproject.com/
   - Must be running during export

2. **WebSocket Server Plugin**
   - Included in OBS 28+
   - Enable in OBS: Tools → WebSocket Server Settings

### OBS Setup

See [OBS.md](../OBS.md) for complete setup guide. Quick steps:

#### Step 1: Enable WebSocket Server

1. Open OBS Studio
2. Go to **Tools → WebSocket Server Settings**
3. Check **Enable WebSocket server**
4. Note the port (default: 4455)
5. Set a password (optional but recommended)
6. Click **OK**

#### Step 2: Configure GoExport

**Method 1: Command-line parameters**

```bash
GoExport.exe --obs-websocket-address localhost --obs-websocket-port 4455 --obs-websocket-password "yourpassword" --obs-fps 60
```

**Method 2: Saved preferences**

Run GoExport once, it will prompt for OBS settings and save them to `data.json`.

**Method 3: Edit data.json**

```json
{
  "obs_websocket_address": "localhost",
  "obs_websocket_port": 4455,
  "obs_websocket_password": "yourpassword",
  "obs_fps": 60
}
```

#### Step 3: Keep OBS Running

OBS must be running (minimized is fine) during exports.

### How OBS Mode Works

1. **Connection** - GoExport connects to OBS via WebSocket
2. **Profile Creation** - Creates temporary profile "GoExport"
3. **Scene Setup** - Creates scene with window capture source
4. **Audio Muting** - Mutes all audio sources to prevent interference
5. **Recording** - Starts recording when video begins
6. **Cleanup** - Stops recording, restores original profile

### OBS Mode Parameters

All OBS parameters can be set via CLI:

```bash
--obs-websocket-address <host>   # Default: localhost
--obs-websocket-port <port>       # Default: 4455
--obs-websocket-password <pass>   # Default: empty
--obs-fps <framerate>             # Default: 60
--obs-no-overwrite               # Prevent profile/scene overwrites
```

### OBS Mode Configuration Files

**Location:** OBS creates profiles in:

- **Windows:** `%APPDATA%\obs-studio\basic\profiles\GoExport\`
- **Linux:** `~/.config/obs-studio/basic/profiles/GoExport/`
- **macOS:** `~/Library/Application Support/obs-studio/basic/profiles/GoExport/`

**Profile Settings:**

```ini
# GoExport/basic.ini
[Video]
BaseCX=1920
BaseCY=1080
OutputCX=1920
OutputCY=1080
FPSType=0
FPSNum=60
FPSDen=1

[Output]
Mode=Simple
FilePath=D:\Documents\Python Projects\GoExport - Main\output
RecFormat=mp4
```

### OBS Window Capture Source

GoExport creates a window capture source that targets the browser window.

**Source Configuration:**

- **Source Name:** `Window Capture (GoExport)`
- **Capture Method:** Windows 10 (1903+) - Window Graphics Capture
- **Window Match Priority:** Window title must match
- **Window Title:** From service config `"window"` field

**Example service window names:**

```python
"local": {"window": "GoExport Viewer"},
"ft": {"window": "FlashThemes"},
```

### OBS Audio Muting

To prevent audio interference, GoExport mutes all audio sources during recording.

**Muted sources:**

- Desktop Audio
- Mic/Auxiliary Audio
- All additional audio input sources

**Note:** Audio from the browser window is still captured via window capture.

### Benefits of OBS Mode

**Quality:**

- Hardware-accelerated encoding (NVENC, QuickSync, AMF)
- Customizable bitrate and quality settings
- Multiple codec support (H.264, H.265, AV1)

**Performance:**

- Lower CPU usage with GPU encoding
- Better frame consistency
- No frame drops on modern hardware

**Features:**

- Automatic scene management
- Multi-monitor support
- Advanced filters and effects

## Native Capture Mode

### What is Native Mode?

Native Mode uses screen-capture-recorder-to-video library to capture the screen directly. This is a fallback mode when OBS is unavailable.

**Platform Support:** Windows only

### Requirements

**Bundled with GoExport:**

1. screen-capture-recorder DLL (`libs/screen-capture-recorder-x64.dll`)
2. virtual-audio-capture-grabber-device
3. Microsoft Visual C++ Redistributable (x64)

**All included in GoExport distribution - no manual installation needed.**

### How Native Mode Works

1. **Driver Registration** - Registers screen capture driver
2. **Window Positioning** - Positions browser window precisely
3. **DirectShow Capture** - Uses DirectShow filter graph
4. **Audio Capture** - Captures system audio via virtual audio device
5. **Encoding** - Real-time encoding to MP4

### Native Mode Configuration

**Config File:** `ScreenCaptureRecorder.ini`

```ini
[screen-capture-recorder]
capture_width=1920
capture_height=1080
default_max_fps=60
capture_mouse_default_1=0
capture_foreground_window_default_1=0
hwnd_to_track=0
start_x=0
start_y=0
```

**Parameters:**

- `capture_width/height` - Set by GoExport based on resolution
- `default_max_fps` - Frame rate (typically 60)
- `capture_mouse` - Show mouse cursor (0=off, 1=on)
- `hwnd_to_track` - Window handle to capture

### Native Mode Limitations

**Quality:**

- Software encoding only (CPU-based)
- Fixed encoding settings
- Limited codec options

**Performance:**

- Higher CPU usage
- Potential frame drops on slower systems
- No hardware acceleration

**Features:**

- Windows only
- Single monitor only
- No advanced filters

**Compatibility:**

- Requires Windows 7 or later
- May conflict with other capture software
- Requires Visual C++ runtime

### When Native Mode is Used

Native Mode is automatically used when:

1. OBS Studio is not installed
2. OBS is not running
3. OBS WebSocket connection fails
4. User prefers native mode (via config)

## Comparison

| Feature                   | OBS Mode        | Native Mode     |
| ------------------------- | --------------- | --------------- |
| **Platform**              | Win/Linux/Mac   | Windows only    |
| **Setup Required**        | Install OBS     | None (bundled)  |
| **Quality**               | Excellent       | Good            |
| **CPU Usage**             | Low (GPU accel) | High (software) |
| **Encoding Options**      | Many            | Limited         |
| **Hardware Acceleration** | Yes             | No              |
| **Frame Consistency**     | Excellent       | Good            |
| **Multi-monitor**         | Yes             | No              |
| **Custom Filters**        | Yes             | No              |

### Recommended Mode

**Use OBS Mode when:**

- You need highest quality
- You have OBS installed
- You want lower CPU usage
- You're on Linux or macOS

**Use Native Mode when:**

- OBS is not available
- Quick setup needed
- Testing/debugging
- Running on older hardware

## Auto-Detection

GoExport automatically detects the best available capture mode on startup.

### Detection Process

```python
# Simplified detection logic
def detect_capture_mode():
    if obs_is_available():
        return "OBS"
    elif is_windows():
        return "Native"
    else:
        raise Error("No capture mode available")
```

### Detection Steps

1. **Check OBS WebSocket**

   - Attempt connection to configured address/port
   - Verify OBS is running and responsive
   - Check WebSocket server is enabled

2. **Fallback to Native** (Windows)

   - Check if screen-capture-recorder DLL exists
   - Verify Visual C++ runtime is installed
   - Confirm Windows version compatibility

3. **Error if Neither Available**
   - Linux/Mac without OBS → Error
   - Connection failures → Error message

### Checking Active Mode

The active capture mode is logged on startup:

```
[INFO] Capture mode: OBS (connected to localhost:4455)
```

or

```
[INFO] Capture mode: Native (screen-capture-recorder)
```

**Programmatic check:**

```python
from modules.capture import capture

if capture.is_obs:
    print("Using OBS mode")
else:
    print("Using Native mode")
```

## Troubleshooting

### OBS Mode Issues

#### "Failed to connect to OBS WebSocket"

**Causes:**

- OBS not running
- WebSocket server disabled
- Wrong port
- Firewall blocking connection

**Solutions:**

```bash
# 1. Verify OBS is running
tasklist | findstr obs64.exe  # Windows
ps aux | grep obs             # Linux

# 2. Check WebSocket settings in OBS
# Tools → WebSocket Server Settings → Enable WebSocket server

# 3. Test connection
telnet localhost 4455

# 4. Try different port
GoExport.exe --obs-websocket-port 4455

# 5. Disable password temporarily
GoExport.exe --obs-websocket-password ""
```

#### "OBS connection timeout"

**Cause:** OBS is busy or unresponsive

**Solution:**

- Close other applications using OBS
- Restart OBS
- Update OBS to latest version

#### "Window capture source not found"

**Cause:** Window title mismatch

**Solution:**

Check service configuration:

```python
# config.py
"local": {
    "window": "GoExport Viewer",  # Must match browser title
}
```

Verify browser window title matches exactly.

#### "Recording failed to start"

**Causes:**

- Disk space full
- Output folder doesn't exist
- Permission issues

**Solutions:**

```bash
# Check disk space
df -h  # Linux
wmic logicaldisk get size,freespace,caption  # Windows

# Verify output folder
ls -la output/  # Linux
dir output\     # Windows

# Check permissions
chmod 755 output/  # Linux
icacls output\ /grant Users:F  # Windows
```

### Native Mode Issues

#### "screen-capture-recorder not found"

**Cause:** DLL missing or not registered

**Solution:**

```bash
# Verify DLL exists
ls libs/screen-capture-recorder-x64.dll

# Re-extract GoExport (may be corrupted)
# Or download from: https://github.com/rdp/screen-capture-recorder-to-video-windows-free/releases
```

#### "DirectShow filter registration failed"

**Cause:** Missing Visual C++ runtime

**Solution:**

Install Microsoft Visual C++ Redistributable (included in `redist/`):

```bash
redist\vcredist_x64.exe
```

Or download from:
https://www.microsoft.com/en-us/download/details.aspx?id=26999

#### "Capture region invalid"

**Cause:** Window positioned off-screen

**Solution:**

```python
# helpers.py - Check window positioning
def position_window():
    # Ensure window is within screen bounds
    pass
```

Restart GoExport to reset window position.

#### High CPU usage during capture

**Cause:** Software encoding overhead

**Solution:**

- Lower resolution
- Reduce FPS in config
- Close other applications
- Consider using OBS mode instead

#### Audio not captured

**Causes:**

- Virtual audio device not installed
- Audio source muted
- Driver conflict

**Solutions:**

```bash
# Check virtual audio device
# Control Panel → Sound → Recording → Virtual Audio Capturer

# Verify device is enabled and default

# Reinstall audio driver
redist\virtual-audio-capturer-setup.exe
```

### General Capture Issues

#### Black screen in recording

**Causes:**

- Browser rendering issue
- GPU acceleration conflict
- Wrong window captured

**Solutions:**

```bash
# Disable GPU acceleration
# Add to navigator.py chrome options:
chrome_options.add_argument('--disable-gpu')

# Force software rendering
chrome_options.add_argument('--disable-software-rasterizer')

# Increase page load wait time
time.sleep(5)  # Before starting capture
```

#### Video/audio desync

**Causes:**

- Frame drops during capture
- Audio buffer overflow
- Encoding lag

**Solutions:**

```bash
# Use constant frame rate
--obs-fps 30  # Lower, more consistent

# Reduce resolution
--resolution 720p

# Close background applications

# Use OBS hardware encoding (NVENC, QuickSync)
```

#### Capture stops mid-recording

**Causes:**

- Disk space exhausted
- Memory overflow
- Application crash

**Solutions:**

```bash
# Monitor disk space
df -h  # Linux
wmic logicaldisk  # Windows

# Check logs
cat logs/$(date +%Y-%m-%d)/goexport.log

# Increase system resources
# Close other applications
```

### Performance Optimization

**For OBS Mode:**

```ini
# Use hardware encoder
[Output]
RecEncoder=obs_qsv11  # Intel QuickSync
# or
RecEncoder=ffmpeg_nvenc  # NVIDIA NVENC
# or
RecEncoder=amd_amf_h264  # AMD AMF
```

**For Native Mode:**

```ini
# Reduce capture quality
default_max_fps=30
capture_width=1280
capture_height=720
```

**General:**

```bash
# Use lower resolution
--resolution 720p

# Disable outro
--no-outro

# Skip audio if not needed
# (Requires code modification)
```

## See Also

- [OBS.md](../OBS.md) - OBS Studio setup guide
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration reference
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting
- [README.md](../readme.md) - Main documentation
