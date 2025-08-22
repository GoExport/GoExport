# OBS Studio Integration for GoExport

This document describes the OBS Studio integration implemented for GoExport to replace ScreenCaptureRecorder.

## Overview

The GoExport recording software has been successfully adapted to utilize OBS Studio instead of ScreenCaptureRecorder, providing modern recording capabilities with automatic Chromium window capture.

## Key Features

### 1. OBS WebSocket Integration
- Custom WebSocket client implementation for OBS Studio control
- Automatic connection to OBS WebSocket server (default: localhost:4455)
- Real-time scene and source management
- Start/stop recording commands via WebSocket API

### 2. Automatic Chromium Window Capture
- Automatic detection of Chromium browser process
- Dynamic window capture source creation
- Focused recording on the Chromium window used by GoExport
- No manual scene configuration required

### 3. Fallback Compatibility
- Graceful fallback to ScreenCaptureRecorder if OBS is unavailable
- Maintains existing workflow compatibility
- No breaking changes to existing functionality

### 4. Flexible Configuration
- Command line parameter control (`--use-obs`, `--use-screen-capture`)
- Configuration file settings (`USE_OBS_CAPTURE = True/False`)
- Configurable WebSocket connection settings

## Implementation Details

### New Files Added

#### `modules/obs_capture.py`
- `OBSWebSocketClient`: WebSocket client for OBS communication
- `OBSCapture`: Main OBS recording interface
- Window detection and scene management logic

### Modified Files

#### `modules/capture.py`
- Enhanced with OBS integration support
- Added constructor parameter `use_obs` (default: True)
- Integrated fallback logic to ScreenCaptureRecorder

#### `config.py`
- Added OBS configuration options:
  - `USE_OBS_CAPTURE = True`
  - `OBS_WEBSOCKET_HOST = "localhost"`
  - `OBS_WEBSOCKET_PORT = 4455`
  - `OBS_WEBSOCKET_PASSWORD = None`

#### `modules/parameters.py`
- Added command line arguments:
  - `--use-obs`: Force OBS Studio usage
  - `--use-screen-capture`: Force ScreenCaptureRecorder usage

#### `modules/flow.py`
- Updated Controller to use configurable capture method
- Integrated parameter-based capture selection

#### `requirements.txt`
- Added `obs-websocket-py==1.0` dependency

#### `readme.md`
- Comprehensive documentation for OBS setup
- Usage instructions and configuration examples
- Dependencies section reorganized for clarity

## Setup Instructions

### 1. Install OBS Studio
1. Download and install OBS Studio from https://obsproject.com/
2. Launch OBS Studio

### 2. Enable WebSocket Server
1. Go to **Tools > WebSocket Server Settings**
2. Check **"Enable WebSocket server"**
3. Set **Server Port** to `4455` (default)
4. Leave **Server Password** empty (or configure in `config.py`)
5. Click **"Apply"** and **"OK"**

### 3. Run GoExport
GoExport will automatically:
- Connect to OBS WebSocket on localhost:4455
- Create a "GoExport_Scene" scene
- Add a "Chromium_Capture" window capture source
- Start and stop recording as needed

## Usage Examples

```bash
# Use OBS Studio (default behavior)
python main.py

# Explicitly use OBS Studio
python main.py --use-obs

# Use legacy ScreenCaptureRecorder
python main.py --use-screen-capture
```

## Configuration Options

### Via config.py
```python
USE_OBS_CAPTURE = True          # Enable OBS recording
OBS_WEBSOCKET_HOST = "localhost" # OBS WebSocket host
OBS_WEBSOCKET_PORT = 4455       # OBS WebSocket port
OBS_WEBSOCKET_PASSWORD = None   # WebSocket password (optional)
```

### Via Command Line
```bash
--use-obs                 # Use OBS Studio
--use-screen-capture      # Use ScreenCaptureRecorder
```

## Technical Architecture

### WebSocket Communication Flow
1. **Connection**: Establish WebSocket connection to OBS
2. **Authentication**: Handle optional password authentication
3. **Scene Setup**: Create/configure recording scene
4. **Source Creation**: Add window capture source for Chromium
5. **Recording Control**: Start/stop recording via WebSocket commands
6. **Cleanup**: Properly disconnect and clean up resources

### Window Detection Logic
1. **Process Enumeration**: Find Chromium/Chrome processes
2. **Window Identification**: Identify the correct browser window
3. **Title Formatting**: Format window title for OBS capture
4. **Fallback Handling**: Use default title if detection fails

### Error Handling
- Connection failure fallback to ScreenCaptureRecorder
- Process detection with graceful degradation
- WebSocket communication error recovery
- Resource cleanup on application exit

## Benefits Over ScreenCaptureRecorder

1. **Modern Recording**: Uses contemporary OBS Studio technology
2. **Better Quality**: Superior video encoding and capture options
3. **Window-Specific Capture**: Precise Chromium window recording
4. **Real-time Control**: Dynamic scene and source management
5. **Future-Proof**: Built on actively maintained OBS Studio
6. **Flexibility**: Easy configuration and customization options

## Compatibility

- **Windows**: Full support (primary platform)
- **Linux/macOS**: Framework ready (OBS detection may need platform-specific adjustments)
- **Fallback**: Automatic fallback to ScreenCaptureRecorder maintains compatibility

## Testing

The implementation has been validated with comprehensive tests covering:
- Configuration parsing and validation
- Command line parameter handling
- OBS WebSocket client functionality
- Capture module integration
- Workflow integration
- Error handling and fallback mechanisms

All tests pass successfully, confirming the implementation meets the requirements specified in the problem statement.