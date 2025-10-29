# GoExport Development Guide

Complete guide for contributing to GoExport, including architecture, development setup, and best practices.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Architecture](#project-architecture)
- [Code Structure](#code-structure)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Building & Packaging](#building--packaging)
- [Contributing Guidelines](#contributing-guidelines)
- [Style Guide](#style-guide)

## Development Setup

### Prerequisites

**Required:**

- Python 3.8 or later
- pip (Python package installer)
- Git

**Optional:**

- PyCharm or VS Code
- OBS Studio (for testing capture)
- ungoogled-chromium v87

### Clone Repository

```bash
git clone https://github.com/GoExport/GoExport.git
cd GoExport
```

### Create Virtual Environment

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
# Install all requirements
pip install -r requirements.txt

# Or install individually
pip install PyQt6 selenium obs-websocket-py requests rich psutil
```

### Install Development Dependencies

```bash
# Code formatting
pip install black

# Linting
pip install pylint flake8

# Type checking
pip install mypy

# Testing
pip install pytest pytest-cov
```

### Configure IDE

**VS Code (`.vscode/settings.json`):**

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "120"],
  "editor.formatOnSave": true
}
```

**PyCharm:**

1. File → Settings → Project → Python Interpreter
2. Select `venv/bin/python`
3. Enable: Tools → Black → "On Save"

### Run from Source

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Run GoExport
python main.py

# With parameters
python main.py --verbose --service local --movie-id test123
```

## Project Architecture

### High-Level Flow

```
main.py
  ↓
modules/flow.py (Controller)
  ↓
  ├─> modules/compatibility.py (System checks)
  ├─> modules/parameters.py (CLI argument parsing)
  ├─> modules/server.py (Local web server)
  ├─> modules/navigator.py (Browser automation)
  ├─> modules/window.py (Window management)
  ├─> modules/capture.py (Capture orchestration)
  │     ├─> modules/obs_capture.py (OBS WebSocket)
  │     └─> modules/native_capture.py (DirectShow)
  ├─> modules/editor.py (Video editing/FFmpeg)
  └─> modules/legacy_editor.py (Old editing logic)
```

### Module Responsibilities

**`main.py`**

- Entry point
- Initializes Compatibility and Controller
- Error handling

**`config.py`**

- Static configuration
- Service definitions
- Resolution matrices
- Dependency paths

**`helpers.py`**

- Utility functions
- File operations
- Command execution
- Data persistence

**`modules/flow.py`**

- Main export orchestration
- Service selection
- Multi-video workflow
- Calls other modules in sequence

**`modules/parameters.py`**

- CLI argument parsing
- Protocol URL parsing
- Parameter validation

**`modules/compatibility.py`**

- Dependency verification
- System compatibility checks
- Version detection

**`modules/server.py`**

- Local HTTP server
- Serves player HTML
- Asset delivery

**`modules/navigator.py`**

- Chromium/Selenium automation
- Page navigation
- JavaScript injection
- Console log monitoring

**`modules/window.py`**

- Window positioning
- Window title detection
- Multi-monitor support

**`modules/capture.py`**

- Capture mode detection (OBS vs Native)
- Delegates to appropriate capture module
- Start/stop recording

**`modules/obs_capture.py`**

- OBS WebSocket connection
- Profile/scene management
- Recording control

**`modules/native_capture.py`**

- DirectShow capture (Windows only)
- screen-capture-recorder integration

**`modules/editor.py`**

- FFmpeg-based video editing
- Clip management
- Trimming and concatenation
- Rendering

**`modules/legacy_editor.py`**

- Old MoviePy-based editor
- Deprecated, maintained for compatibility

**`modules/logger.py`**

- Logging configuration
- File and console output

**`modules/update.py`**

- GitHub release checking
- Version comparison

### Data Flow

```
1. User Input
   ↓
2. Parameter Parsing (parameters.py)
   ↓
3. Service Configuration (config.py)
   ↓
4. Browser Launch (navigator.py)
   ↓
5. Window Setup (window.py)
   ↓
6. Capture Start (capture.py → obs_capture.py or native_capture.py)
   ↓
7. Video Playback (Browser executes Flash)
   ↓
8. Console Monitoring (navigator.py detects start/stop)
   ↓
9. Capture Stop (capture.py)
   ↓
10. Video Editing (editor.py)
    ├─> Trim
    ├─> Add outro
    └─> Concatenate
   ↓
11. Export (editor.render())
   ↓
12. Output File
```

## Code Structure

### Adding a New Service

1. **Update `config.py`:**

```python
AVAILABLE_SERVICES = {
    # ... existing services ...
    "my_service": {
        "name": "My Custom Service",
        "requires": {"movieId"},
        "domain": ["https://myservice.com"],
        "player": [
            "https://myservice.com/player",
            "?id={movie_id}&w={width}&h={height}"
        ],
        "window": "My Service Player",
        "afterloadscripts": []
    }
}
```

See [ADDING_NEW_SERVICES.md](ADDING_NEW_SERVICES.md) for complete guide.

2. **Test:**

```bash
python main.py --service my_service --movie-id test123
```

### Adding a New Resolution

1. **Update `config.py`:**

```python
AVAILABLE_SIZES = {
    "16:9": {
        # ... existing resolutions ...
        "1440p": (2560, 1440, True),  # Add new resolution
    }
}
```

2. **Create matching outro (optional):**

```bash
# Place in assets/outro/wide/
assets/outro/wide/2560x1440.mp4
```

### Adding a New Parameter

1. **Update `modules/parameters.py`:**

```python
parser.add_argument(
    "--my-param",
    help="Description of parameter",
    dest="my_param",
    type=str,
    default="default_value"
)
```

2. **Access in code:**

```python
import helpers

my_value = helpers.get_param("my_param")
```

3. **Add to protocol URL parsing:**

```python
# In _parse_protocol() method
proto_map = {
    # ... existing mappings ...
    "my_param": "my_param",
}
```

### Adding a New Capture Mode

1. **Create module `modules/my_capture.py`:**

```python
class MyCapture:
    def __init__(self):
        pass

    def start_recording(self, output_path):
        # Start capture
        pass

    def stop_recording(self):
        # Stop capture
        pass
```

2. **Update `modules/capture.py`:**

```python
from modules.my_capture import MyCapture

class Capture:
    def __init__(self):
        if detect_my_capture():
            self.capture_mode = MyCapture()
            self.is_my = True
        # ... existing detection ...
```

## Development Workflow

### Branch Strategy

**Main branches:**

- `main` - Stable release code
- `dev` - Development branch

**Feature branches:**

- `feature/service-xyz` - New service support
- `feature/gui-improvements` - GUI enhancements
- `bugfix/capture-crash` - Bug fixes

### Workflow

```bash
# Create feature branch
git checkout dev
git pull origin dev
git checkout -b feature/my-feature

# Make changes
# ... edit files ...

# Test changes
python main.py --verbose

# Commit
git add .
git commit -m "Add feature: description"

# Push and create PR
git push origin feature/my-feature
# Create Pull Request on GitHub: feature/my-feature → dev
```

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

**Types:**

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Code style (formatting)
- `refactor` - Code refactoring
- `test` - Adding tests
- `chore` - Maintenance

**Examples:**

```
feat: Add FlashThemes service support

- Add service configuration in config.py
- Implement custom player injection
- Update documentation

Closes #123
```

```
fix: Resolve OBS connection timeout

- Increase connection timeout to 10s
- Add retry logic
- Better error messages

Fixes #456
```

## Testing

### Manual Testing

```bash
# Test basic export
python main.py --service local --movie-id test123 --resolution 720p

# Test with verbose logging
python main.py --verbose --service local --movie-id test123

# Test no-input mode
python main.py --no-input --service local --movie-id test123 --resolution 1080p --aspect-ratio 16:9

# Test protocol URL
python main.py --protocol "goexport://local?video_id=test123&resolution=720p"
```

### Unit Testing (Future)

```bash
# Run tests
pytest

# With coverage
pytest --cov=modules --cov-report=html

# Specific test
pytest tests/test_editor.py
```

### Integration Testing

```bash
# Test capture modes
python tests/test_gui_integration.py

# Test compiled UI
python tests/test_compiled_ui.py
```

### Test Checklist

**Before committing:**

- [ ] Code runs without errors
- [ ] No syntax errors (run `python -m py_compile main.py`)
- [ ] Verbose mode works (`--verbose`)
- [ ] Logs are meaningful
- [ ] No hardcoded paths
- [ ] Cross-platform compatibility considered

**Before releasing:**

- [ ] All services work
- [ ] OBS mode works
- [ ] Native mode works (Windows)
- [ ] GUI loads correctly
- [ ] Protocol URLs work
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

## Building & Packaging

### Build Executable

**Using PyInstaller:**

```bash
# Install PyInstaller
pip install pyinstaller

# Build using spec file
pyinstaller GoExport.spec

# Output in dist/GoExport/
```

**`GoExport.spec` structure:**

```python
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('server', 'server'),
        ('dependencies', 'dependencies'),
        ('libs', 'libs'),
        # ...
    ],
    hiddenimports=['obs-websocket-py'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GoExport',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GoExport',
)
```

### Create Windows Installer

**Using Inno Setup:**

```bash
# Install Inno Setup: https://jrsoftware.org/isdl.php

# Compile installer
iscc setup/GoExport.iss

# Output: setup/Output/GoExport-Setup.exe
```

### GitHub Actions

**`.github/workflows/release_and_build.yml`:**

Automatically builds on push to tags:

```bash
# Create tag
git tag v0.16.0
git push origin v0.16.0

# GitHub Actions will:
# 1. Build Windows executable
# 2. Build Linux binary
# 3. Create installer
# 4. Upload to GitHub Releases
```

## Contributing Guidelines

### Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn

### How to Contribute

1. **Find an issue** or create one
2. **Comment** on issue to claim it
3. **Fork** repository
4. **Create branch** from `dev`
5. **Make changes** with clear commits
6. **Test thoroughly**
7. **Submit Pull Request** to `dev`
8. **Respond to review** feedback

### Pull Request Template

```markdown
## Description

Brief description of changes

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

- [ ] Tested on Windows
- [ ] Tested on Linux
- [ ] Tested with OBS mode
- [ ] Tested with Native mode

## Checklist

- [ ] Code follows style guide
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Added tests (if applicable)

## Screenshots (if applicable)
```

### Review Process

1. Maintainer reviews code
2. CI/CD runs automated checks
3. Feedback provided
4. Changes requested/approved
5. Merge to `dev`
6. Scheduled release to `main`

## Style Guide

### Python Style (PEP 8)

**Indentation:**

```python
# 4 spaces, no tabs
def my_function():
    if condition:
        do_something()
```

**Naming:**

```python
# snake_case for functions and variables
def calculate_duration():
    video_length = 120

# PascalCase for classes
class VideoEditor:
    pass

# UPPER_CASE for constants
DEFAULT_RESOLUTION = "1080p"
```

**Line Length:**

```python
# Max 120 characters
very_long_function_call(
    parameter1="value1",
    parameter2="value2",
    parameter3="value3"
)
```

**Imports:**

```python
# Standard library
import os
import sys

# Third-party
from PyQt6.QtWidgets import QApplication

# Local
from modules.editor import Editor
import helpers
```

**Docstrings:**

```python
def trim_video(clip_id: int, start: float, end: float):
    """
    Trim a video clip to specified time range.

    :param clip_id: ID of the clip to trim
    :param start: Start time in seconds
    :param end: End time in seconds
    :raises IndexError: If clip_id is invalid
    :return: Path to trimmed clip
    """
    pass
```

**Comments:**

```python
# Use comments for non-obvious logic
# Avoid obvious comments

# Good:
# Convert seconds to milliseconds for FFmpeg
time_ms = time_sec * 1000

# Bad:
# Set x to 10
x = 10
```

### Error Handling

```python
# Specific exceptions
try:
    file_content = open(file_path).read()
except FileNotFoundError:
    logger.error(f"File not found: {file_path}")
    raise
except PermissionError:
    logger.error(f"Permission denied: {file_path}")
    raise

# Log errors
import modules.logger as logger

try:
    risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise
```

### Logging

```python
from modules.logger import logger

# Debug - Detailed diagnostic info
logger.debug(f"Processing clip {clip_id}")

# Info - General information
logger.info("Export started")

# Warning - Something unexpected but recoverable
logger.warning("Outro file not found, skipping")

# Error - Error occurred
logger.error(f"Failed to trim clip: {e}")

# Critical - Severe error, application may not recover
logger.critical("FFmpeg not found, cannot continue")
```

### Platform Compatibility

```python
import helpers

# Check platform
if helpers.os_is_windows():
    path = helpers.get_config("PATH_FFMPEG_WINDOWS")
elif helpers.os_is_linux():
    path = helpers.get_config("PATH_FFMPEG_LINUX")
else:
    raise NotImplementedError("Unsupported platform")

# Use os.path for paths
import os
path = os.path.join("folder", "file.mp4")

# Or use helpers.get_path()
path = helpers.get_path(base, ["folder", "file.mp4"])
```

## Documentation

### Code Documentation

- Docstrings for all public functions/classes
- Inline comments for complex logic
- Type hints where helpful

```python
def get_clip_length(self, clip_id: int) -> float:
    """
    Get duration of a video clip.

    :param clip_id: Index of clip in clips list
    :return: Duration in seconds
    :raises IndexError: If clip_id out of range
    """
    pass
```

### User Documentation

- Update relevant `.md` files in `docs/`
- Add examples for new features
- Document breaking changes in CHANGELOG.md

### Changelog Format (CHANGELOG.md)

```markdown
# Changelog

## [0.16.0] - 2025-10-29

### Added

- New feature X with parameter Y
- Support for Z service

### Changed

- Improved performance of video concatenation
- Updated OBS connection timeout

### Fixed

- Crash when outro file missing
- Audio desync in multi-video exports

### Deprecated

- Legacy editor mode (will be removed in v0.17.0)

### Security

- Updated dependency X to fix CVE-YYYY-NNNN
```

## Resources

**Official:**

- GitHub: https://github.com/GoExport/GoExport
- Discord: https://discord.gg/ejwJYtQDrS
- Website: https://goexport.lexian.dev

**Documentation:**

- [README.md](../readme.md) - Main documentation
- [PARAMETERS.md](PARAMETERS.md) - CLI parameters
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration reference
- [CAPTURE_MODES.md](CAPTURE_MODES.md) - Capture modes
- [FFMPEG_OPERATIONS.md](FFMPEG_OPERATIONS.md) - Video processing

**Tools:**

- FFmpeg: https://ffmpeg.org/documentation.html
- OBS Studio: https://obsproject.com/wiki/
- Selenium: https://www.selenium.dev/documentation/
- PyQt6: https://www.riverbankcomputing.com/static/Docs/PyQt6/

## See Also

- [ADDING_NEW_SERVICES.md](ADDING_NEW_SERVICES.md) - Service creation
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
- [LICENSE](../LICENSE) - GPL v3.0 License
