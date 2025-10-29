# GoExport Troubleshooting Guide

Comprehensive troubleshooting for common GoExport issues across all platforms.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Launch & Startup Issues](#launch--startup-issues)
- [Capture Issues](#capture-issues)
- [Video Quality Issues](#video-quality-issues)
- [Export & Rendering Issues](#export--rendering-issues)
- [OBS Issues](#obs-issues)
- [Browser Automation Issues](#browser-automation-issues)
- [Platform-Specific Issues](#platform-specific-issues)
- [Error Messages](#error-messages)

## Installation Issues

### "Missing dependencies" error on startup

**Windows:**

```bash
# Check if dependencies folder exists
dir dependencies\

# Verify FFmpeg
dependencies\ffmpeg\bin\ffmpeg.exe -version

# Verify Chromium
dir dependencies\ungoogled-chromium\chrome.exe
```

**Linux:**

```bash
# Check dependencies
ls -la dependencies/

# Verify FFmpeg
dependencies/ffmpeg/bin/ffmpeg -version

# Check library dependencies
ldd dependencies/ungoogled-chromium/chrome
```

**Solution:** Re-extract GoExport archive or download dependencies separately.

### "Python not found" (Running from source)

**Solution:**

```bash
# Windows
python --version

# If not found, install Python 3.8+
# Download from: https://www.python.org/downloads/

# Linux
sudo apt install python3 python3-pip  # Debian/Ubuntu
sudo dnf install python3 python3-pip  # Fedora
```

### "ModuleNotFoundError: No module named 'PyQt6'"

**Solution:**

```bash
# Install requirements
pip install -r requirements.txt

# Or specifically
pip install PyQt6 selenium obs-websocket-py requests rich psutil
```

### Visual C++ Runtime error (Windows)

**Error:** "The program can't start because VCRUNTIME140.dll is missing"

**Solution:**

```bash
# Install from included redistributable
redist\vcredist_x64.exe

# Or download from Microsoft:
# https://aka.ms/vs/17/release/vc_redist.x64.exe
```

## Launch & Startup Issues

### GoExport won't start (no window, no error)

**Windows:**

```bash
# Run from command line to see errors
GoExport.exe --verbose

# Check if process is running
tasklist | findstr GoExport

# Check logs
type logs\%date:~-4,4%-%date:~-7,2%-%date:~-10,2%\goexport.log
```

**Linux:**

```bash
# Run from terminal
./GoExport --verbose

# Check process
ps aux | grep GoExport

# Check logs
cat logs/$(date +%Y-%m-%d)/goexport.log
```

### GUI doesn't load (Linux X11)

See [LINUX_SETUP.md - GUI Troubleshooting](LINUX_SETUP.md#gui-troubleshooting)

**Quick fix:**

```bash
sudo apt install libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxkbcommon-x11-0 libxcb-cursor0
```

### "Permission denied" error

**Windows:**

```bash
# Run as Administrator (right-click → Run as administrator)
# Or add exception to antivirus

# If in Program Files, use different location
# Recommended: C:\GoExport\
```

**Linux:**

```bash
# Make executable
chmod +x GoExport

# Check ownership
ls -l GoExport
chown $USER:$USER GoExport

# If in /opt, may need sudo
sudo ./GoExport
```

### Antivirus blocks GoExport (Windows)

**Windows Defender:**

```bash
# Add exclusion
# Settings → Update & Security → Windows Security → Virus & threat protection
# → Manage settings → Add or remove exclusions
# Add: C:\Program Files\GoExport\

# Or via PowerShell (Admin)
Add-MpPreference -ExclusionPath "C:\Program Files\GoExport\"
```

**Third-party antivirus:**

- Add GoExport folder to exclusions
- Temporarily disable real-time protection during exports

## Capture Issues

### Black screen in recording

**Causes:**

- Wrong window captured
- Browser not visible
- GPU acceleration issue

**Solutions:**

**Check window title:**

```python
# config.py - Verify service window name
"local": {
    "window": "GoExport Viewer",  # Must match browser title
}
```

**Disable GPU acceleration:**

```python
# modules/navigator.py
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-software-rasterizer')
```

**Ensure window is visible:**

```python
# Don't minimize browser during capture
# Check window positioning code in modules/window.py
```

### No audio in recording

**OBS Mode:**

```bash
# Check OBS audio sources
# OBS → Settings → Audio
# Ensure "Desktop Audio" is configured

# Verify OBS is capturing audio
# Start manual recording test
```

**Native Mode (Windows):**

```bash
# Check virtual audio device
# Control Panel → Sound → Recording
# Verify "Virtual Audio Capturer" is enabled and default

# Reinstall if needed
redist\virtual-audio-capturer-setup.exe
```

### Video lags/stutters during capture

**Reduce load:**

```bash
# Close other applications
# Use lower resolution
GoExport.exe --resolution 720p

# Lower FPS (OBS mode)
GoExport.exe --obs-fps 30
```

**Hardware acceleration:**

```bash
# Enable in OBS
# Settings → Output → Recording
# Encoder: Use NVENC/QuickSync/AMF instead of x264
```

### Capture stops mid-recording

**Check disk space:**

```bash
# Windows
wmic logicaldisk get size,freespace,caption

# Linux
df -h
```

**Check memory:**

```bash
# Windows
wmic OS get FreePhysicalMemory

# Linux
free -h
```

**Solutions:**

- Free up disk space (10GB+ recommended)
- Close memory-intensive applications
- Use SSD for output folder

## Video Quality Issues

### Exported video is blurry

**Increase quality:**

```python
# Modify modules/editor.py render() method
"-crf", "18",  # Lower = higher quality (default: 23)
```

**Use slower preset:**

```python
"-preset", "slow",  # Better compression (default: veryfast)
```

**Increase bitrate:**

```python
# Replace CRF with bitrate mode
"-b:v", "5M",  # 5 Mbps
```

### Colors look washed out

**Check color space:**

```bash
# Verify input color space
ffprobe -v error -select_streams v:0 -show_entries stream=color_space,color_transfer,color_primaries input.mp4
```

**Force color space:**

```python
# Modify editor.py
"-colorspace", "bt709",
"-color_primaries", "bt709",
"-color_trc", "bt709",
```

### Aspect ratio is wrong

**Check configuration:**

```bash
# Verify aspect ratio in config
GoExport.exe --aspect-ratio 16:9 --resolution 1080p
```

**Check resolution matrix:**

```python
# config.py - AVAILABLE_SIZES
"16:9": {
    "1080p": (1920, 1080, True),  # (width, height, is_wide)
}
```

### Video has black bars

**Cause:** Padding from resolution mismatch

**Solution:** Use native resolution or adjust source

```python
# Editor scales to fit and pads
# To avoid: Match capture resolution to export resolution
```

## Export & Rendering Issues

### "No clips to render" error

**Cause:** No videos captured or clips cleared

**Check:**

```python
# Verify clips were added
editor.clips  # Should not be empty
```

**Solution:** Ensure capture completed successfully before rendering

### Rendering takes too long

**Speed up:**

```bash
# Use fast mode (no re-encode)
# Only works with identical formats
editor.render(output="final.mp4", reencode=False)

# Use faster preset
# Modify editor.py
"-preset", "ultrafast",
```

**Hardware encoding:**

```python
# NVIDIA
"-c:v", "h264_nvenc",

# Intel
"-c:v", "h264_qsv",

# AMD
"-c:v", "h264_amf",
```

### Output file is huge

**Reduce size:**

```python
# Increase CRF (lower quality)
"-crf", "28",  # Default: 23, Range: 0-51

# Lower resolution
GoExport.exe --resolution 720p

# Lower bitrate
"-b:a", "96k",  # Audio (default: 128k)
```

### "Error rendering video: ..."

**Check FFmpeg:**

```bash
# Test FFmpeg
ffmpeg -version

# Windows
dependencies\ffmpeg\bin\ffmpeg.exe -version

# Linux
dependencies/ffmpeg/bin/ffmpeg -version
```

**Check logs:**

```bash
# Look for detailed error
logs/YYYY-MM-DD/goexport.log
```

**Common causes:**

- Corrupted input file
- Insufficient disk space
- File locked by another process

## OBS Issues

See [CAPTURE_MODES.md - Troubleshooting](CAPTURE_MODES.md#troubleshooting) for detailed OBS troubleshooting.

### "Failed to connect to OBS WebSocket"

**Solutions:**

```bash
# 1. Verify OBS is running
tasklist | findstr obs  # Windows
ps aux | grep obs       # Linux

# 2. Enable WebSocket in OBS
# Tools → WebSocket Server Settings → Enable

# 3. Test connection
telnet localhost 4455

# 4. Check password
GoExport.exe --obs-websocket-password ""  # Try no password

# 5. Try different port
GoExport.exe --obs-websocket-port 4455
```

### OBS recording doesn't start

**Check:**

- Output folder exists and is writable
- OBS not already recording manually
- Disk space available
- OBS is not frozen/crashed

**Restart OBS:**

```bash
# Windows
taskkill /F /IM obs64.exe
start "" "C:\Program Files\obs-studio\bin\64bit\obs64.exe"

# Linux
killall obs
obs &
```

### OBS captures wrong window

**Check window title:**

```python
# config.py
"window": "GoExport Viewer",  # Must match exactly
```

**Manual test:**

1. Open browser manually
2. Check exact window title
3. Update config.py if needed
4. Restart GoExport

## Browser Automation Issues

### Chromedriver version mismatch

**Error:** "This version of ChromeDriver only supports Chrome version X"

**Solution:**

```bash
# GoExport includes matching chromedriver
# If error occurs, download matching version:
# https://chromedriver.chromium.org/downloads

# Replace in:
# dependencies/chromedriver/chromedriver.exe (Windows)
# dependencies/chromedriver/chromedriver (Linux)
```

### Browser doesn't navigate to video

**Check URL:**

```bash
# Enable verbose logging
GoExport.exe --verbose

# Check logs for navigation URL
logs/YYYY-MM-DD/goexport.log
```

**Check service config:**

```python
# config.py - AVAILABLE_SERVICES
"local": {
    "domain": ["http://127.0.0.1:4343"],  # Must match server
    "player": ["http://localhost:26519", "index.html?..."],
}
```

**Check server:**

```bash
# For "local" service, server must be running
# Check if port 26519 is open
netstat -an | findstr 26519  # Windows
netstat -tuln | grep 26519   # Linux
```

### Flash content doesn't load

**Check Flash plugin:**

```bash
# Windows
dir dependencies\ungoogled-chromium\extensions\pepflashplayer.dll

# Linux
ls dependencies/ungoogled-chromium/extensions/libpepflashplayer.so
```

**Check Flash version:**

```python
# config.py
PATH_FLASH_VERSION_WINDOWS = "34.0.0.330"
PATH_FLASH_VERSION_LINUX = "34.0.0.137"
```

**Reinstall CleanFlash:**

- Download from: https://web.archive.org/web/20241221081401/https://cdn.cleanflash.org/CleanFlash_34.0.0.308_Installer.exe

### Browser crashes during export

**Causes:**

- Memory leak
- GPU driver issue
- Flash player crash

**Solutions:**

```bash
# Reduce resolution
GoExport.exe --resolution 720p

# Disable GPU acceleration
# Edit modules/navigator.py:
chrome_options.add_argument('--disable-gpu')

# Increase system memory
# Close other applications

# Update GPU drivers
```

## Platform-Specific Issues

### Windows

#### UAC prompt every time

**Solution:**

```bash
# Create compatibility shim
# Right-click GoExport.exe → Properties → Compatibility
# Check "Run this program as an administrator"
# Uncheck "Run this program in compatibility mode"
```

#### Windows Defender SmartScreen warning

**Solution:**

```bash
# Click "More info" → "Run anyway"

# Or add publisher exception
# Settings → Update & Security → Windows Security
# → App & browser control → Reputation-based protection settings
```

#### High DPI display issues

**Solution:**

```bash
# Right-click GoExport.exe → Properties → Compatibility
# Change high DPI settings
# Check "Override high DPI scaling behavior"
# Scaling performed by: Application
```

### Linux

#### Missing library errors

**Solution:**

```bash
# Check missing libraries
ldd GoExport

# Install missing dependencies
sudo apt install <missing-lib>
```

#### Wayland vs X11 issues

**Force X11:**

```bash
# Set environment variable
export QT_QPA_PLATFORM=xcb
./GoExport

# Or in launcher script
#!/bin/bash
export QT_QPA_PLATFORM=xcb
/opt/GoExport/GoExport "$@"
```

#### SELinux blocks execution (Fedora/RHEL)

**Solution:**

```bash
# Temporarily permissive
sudo setenforce 0

# Or add exception
sudo semanage fcontext -a -t bin_t "/opt/GoExport/GoExport"
sudo restorecon -v /opt/GoExport/GoExport

# Re-enable
sudo setenforce 1
```

### macOS

#### "App is damaged and can't be opened"

**Solution:**

```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine /Applications/GoExport.app

# Or allow in System Preferences
# System Preferences → Security & Privacy → General
# Click "Open Anyway"
```

#### Gatekeeper blocks execution

**Solution:**

```bash
# Right-click → Open
# Or via terminal:
open /Applications/GoExport.app

# Disable Gatekeeper (not recommended)
sudo spctl --master-disable
```

## Error Messages

### "MovieId is required"

**Cause:** Missing video ID parameter

**Solution:**

```bash
# Provide movie ID
GoExport.exe --movie-id m-123

# Or use protocol URL
goexport://local?video_id=m-123
```

### "Service 'X' not found"

**Cause:** Invalid service name

**Solution:**

```bash
# Check available services in config.py
# Valid: local, ft, local_beta

GoExport.exe --service local
```

### "Resolution 'X' not available for aspect ratio 'Y'"

**Cause:** Invalid resolution for selected aspect ratio

**Solution:**

```bash
# Check AVAILABLE_SIZES in config.py
# Example: 4:3 only supports 240p-480p

# Use valid combination
GoExport.exe --aspect-ratio 16:9 --resolution 1080p
```

### "Failed to start server"

**Cause:** Port already in use

**Solution:**

```bash
# Check what's using port 26519
netstat -ano | findstr 26519  # Windows
lsof -i :26519                # Linux

# Kill process or use different port
# (Requires code modification)
```

### "FFmpeg command failed"

**Check command:**

```bash
# Enable verbose
GoExport.exe --verbose

# Check logs for full command
logs/YYYY-MM-DD/goexport.log

# Test command manually
# Copy command from log and run
```

**Common causes:**

- Invalid input file
- Unsupported codec
- Insufficient permissions
- Disk full

### "Trim times invalid"

**Cause:** Start time >= end time or beyond video duration

**Solution:**

```bash
# Check video duration first
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 video.mp4

# Ensure: 0 <= start < end <= duration
```

### "Outro file not found"

**Cause:** Missing outro for selected resolution

**Solution:**

```bash
# Check outro exists
# Windows
dir assets\outro\wide\1920x1080.mp4

# Linux
ls assets/outro/wide/1920x1080.mp4

# If missing, download outros or disable outro
GoExport.exe --no-input  # Skips outro prompt
```

## Getting Help

### Collecting Debug Information

```bash
# Run with verbose logging
GoExport.exe --verbose

# Logs location
# Windows: logs\YYYY-MM-DD\goexport.log
# Linux: logs/YYYY-MM-DD/goexport.log

# System info
GoExport.exe --version

# Python version (if running from source)
python --version

# FFmpeg version
dependencies\ffmpeg\bin\ffmpeg.exe -version  # Windows
dependencies/ffmpeg/bin/ffmpeg -version      # Linux

# OBS version (if using OBS mode)
obs --version  # Linux
# Windows: Help → About in OBS
```

### Reporting Issues

Include in bug report:

1. GoExport version
2. Operating system and version
3. Capture mode (OBS or Native)
4. Command-line parameters used
5. Full error message
6. Relevant log excerpt
7. Steps to reproduce

**Submit to:** https://github.com/GoExport/GoExport/issues

### Community Support

- **Discord:** https://discord.gg/ejwJYtQDrS
- **GitHub Discussions:** https://github.com/GoExport/GoExport/discussions

## See Also

- [PARAMETERS.md](PARAMETERS.md) - Command-line parameters
- [CAPTURE_MODES.md](CAPTURE_MODES.md) - Capture system details
- [LINUX_SETUP.md](LINUX_SETUP.md) - Linux-specific setup
- [FFMPEG_OPERATIONS.md](FFMPEG_OPERATIONS.md) - Video processing
- [README.md](../readme.md) - Main documentation
