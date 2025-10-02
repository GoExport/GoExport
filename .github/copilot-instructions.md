# GoExport - AI Coding Agent Instructions

## Project Overview

GoExport is a Python application that automates video export from Flash-based video makers (Wrapper Offline, FlashThemes). It uses browser automation, screen capture, and video processing to export Flash content as MP4 files.

## Architecture & Key Components

### Main Flow (`main.py` → `modules/flow.py`)

- Entry point initializes `Compatibility`, `Controller` classes
- `Controller.setup()` handles service selection, resolution setup, server management
- `Controller.export()` orchestrates browser automation → capture → editing workflow
- Multi-video workflow allows concatenating multiple exports

### Capture System (`modules/capture.py`)

**Dual capture modes** - automatically detects available method:

- **OBS Mode**: Uses OBS WebSocket API (`modules/obs_capture.py`) - preferred for all platforms
- **Native Mode**: Windows-only using screen-capture-recorder (`modules/native_capture.py`)
- Check `capture.is_obs` to determine active mode

### Browser Automation (`modules/navigator.py`)

- Uses ungoogled-chromium (v87) + chromedriver for Flash compatibility
- Window management for precise capture area
- Service-specific URL patterns and navigation logic
- Injects `afterloadscripts` for service customization

### Video Processing (`modules/editor.py`)

- **FFmpeg-based** (not MoviePy) for performance
- Clip management: add, trim, concatenate operations
- Uses `clips.txt` file format for FFmpeg concat demuxer
- All video operations go through FFmpeg subprocess calls

### Configuration System

- **Static config** in `config.py` (app metadata, paths, resolution matrices)
- **Runtime parameters** via `modules/parameters.py` (CLI args)
- **Persistent storage** via `helpers.save()`/`helpers.load()` in `data.json`
- **Memory storage** via `helpers.remember()`/`helpers.recall()`

## Service Architecture

Services defined in `config.py` `AVAILABLE_SERVICES`:

```python
"service_name": {
    "host": bool,        # Whether to start local server
    "domain": [urls],    # Allowed domains for navigation
    "player": [urls],    # Player URL patterns
    "legacy": bool,      # Use legacy editor mode
    "afterloadscripts": [js_scripts]  # Post-load customization
}
```

## Critical Dependencies & Paths

- **FFmpeg**: `dependencies/ffmpeg/bin/` - video processing
- **Chrome**: `dependencies/ungoogled-chromium/` - Flash player
- **Chromedriver**: `dependencies/chromedriver/` - automation
- **Capture libs**: `libs/screen-capture-recorder-x64.dll` (Windows native)
- **Output folder**: `output/` for final videos

## Development Patterns

### Error Handling

- Use `modules.logger.logger` for all logging
- `helpers.try_command()` for subprocess execution with error handling
- `helpers.try_path()` for file existence checks
- Validate user inputs against config arrays before processing

### Platform Detection

- `helpers.os_is_windows()` for Windows-specific features
- Native capture only works on Windows
- FFmpeg paths differ by platform (`PATH_FFMPEG_WINDOWS` vs others)

### Parameter Management

- CLI args via `helpers.get_param(key)`
- User preferences via `helpers.load(key, default)`
- Runtime state via `helpers.recall(key)`
- Always provide defaults for user-facing prompts

### OBS Integration

- Connect to WebSocket on init: `obs_capture.py`
- Creates temporary profile/scene for recording
- Mutes audio sources to avoid interference
- Command-line parameters: `--obs-websocket-address`, `--obs-websocket-port`, `--obs-websocket-password`
- Check OBS.md for setup requirements

## Testing & Debugging

- Use `--verbose` for detailed logging
- Use `--no-input` with required params for automated testing
- Log files in `logs/YYYY-MM-DD/` directory
- FFmpeg operations create temporary files in output directory
- Browser automation can be debugged by disabling headless mode in navigator.py

## Build System

- PyInstaller spec: `GoExport.spec`
- Bundles all dependencies except CleanFlash (user must install)
- Windows installer: `setup/GoExport.iss` (Inno Setup)
- GitHub Actions: `.github/workflows/release_and_build.yml`

## Common Workflows

1. **Adding new service**: Update `AVAILABLE_SERVICES` in config.py, add domain/player patterns
2. **Resolution support**: Add to `AVAILABLE_SIZES` matrix in config.py
3. **OBS issues**: Check WebSocket connection, verify window capture source matches `window` config
4. **FFmpeg problems**: Validate input files exist, check command construction in editor.py
