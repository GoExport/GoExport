# GoExport Command-Line Parameters

This document covers all command-line parameters and protocol URL formats supported by GoExport.

## Table of Contents

- [Overview](#overview)
- [CLI Parameters](#cli-parameters)
- [Protocol URL Format](#protocol-url-format)
- [Usage Examples](#usage-examples)
- [Parameter Validation](#parameter-validation)

## Overview

GoExport supports two methods of configuration:

1. **Command-line arguments** - Traditional CLI flags
2. **Protocol URLs** - Custom `goexport://` URLs for browser/system integration

## CLI Parameters

### Basic Parameters

#### `-ni, --no-input`

Skip all user input prompts and run in automated mode.

**Type:** Boolean flag  
**Default:** `false`  
**Example:**

```bash
GoExport.exe --no-input
```

**Note:** When using `--no-input`, you must provide all required parameters via other flags.

#### `-v, --verbose`

Enable verbose logging output for debugging purposes.

**Type:** Boolean flag  
**Default:** `false`  
**Example:**

```bash
GoExport.exe --verbose
```

**Output:** Creates detailed logs in `logs/YYYY-MM-DD/` directory.

#### `-j, --json`

Enable structured JSON output to STDOUT (diagnostics go to STDERR).

**Type:** Boolean flag  
**Default:** `false`  
**Example:**

```bash
GoExport.exe --json
```

**Note:** Useful for integrating GoExport with other tools or scripts that can parse JSON output.

#### `-c, --console`

Force console mode (no GUI).

**Type:** Boolean flag  
**Default:** `false`  
**Example:**

```bash
GoExport.exe --console
```

**Warning:** NOT RECOMMENDED as it may leave orphaned processes. Use with caution.

---

### Service Configuration

#### `-s, --service`

Specify which video service to use.

**Type:** String  
**Valid values:** Any service key from `config.py` `AVAILABLE_SERVICES`

- `local` - Wrapper: Offline
- `ft` - FlashThemes
- `local_beta` - Local Beta (hidden)

**Example:**

```bash
GoExport.exe --service local
```

#### `-r, --resolution`

Set the export resolution.

**Type:** String  
**Valid values:** Depends on aspect ratio

- `240p`, `360p`, `420p`, `480p` (4:3)
- `360p`, `480p`, `720p`, `1080p`, `2k`, `4k`, `5k`, `8k` (16:9 and 14:9)

**Example:**

```bash
GoExport.exe --resolution 1080p
```

#### `-asr, --aspect_ratio`

Set the aspect ratio for export.

**Type:** String  
**Valid values:** `4:3`, `14:9`, `16:9`, `9:16`  
**Default:** `16:9`

**Example:**

```bash
GoExport.exe --aspect_ratio 16:9
```

---

### Video Identifiers

#### `-oi, --owner-id`

Set the owner/user ID for the video (required for some services).

**Type:** String  
**Required for:** FlashThemes (`ft`)  
**Example:**

```bash
GoExport.exe --owner-id user123
```

#### `-mi, --movie-id`

Set the movie/video ID to export.

**Type:** String  
**Required for:** All services  
**Example:**

```bash
GoExport.exe --movie-id video456
```

---

### Export Options

#### `-ae, --auto-edit`

Enable automatic video editing after capture.

**Type:** Boolean flag  
**Default:** `false`  
**Example:**

```bash
GoExport.exe --auto-edit
```

**Note:** Automatically trims and processes the captured video.

#### `-of, --open-file`

Open the output folder after export completes (only in `--no-input` mode).

**Type:** Boolean flag  
**Default:** `false`  
**Example:**

```bash
GoExport.exe --open-file --no-input
```

#### `-uo, --use-outro`

Add an outro to the exported video (only in `--no-input` mode).

**Type:** Boolean flag  
**Default:** `false`  
**Example:**

```bash
GoExport.exe --use-outro --no-input
```

**Note:** Outro files must exist in `assets/outro/` matching the resolution.

---

### OBS WebSocket Configuration

GoExport can connect to OBS Studio via WebSocket for professional-quality capture.

#### `--obs-websocket-address`

Set the OBS WebSocket server address.

**Type:** String  
**Default:** `localhost`  
**Example:**

```bash
GoExport.exe --obs-websocket-address 192.168.1.100
```

#### `--obs-websocket-port`

Set the OBS WebSocket server port.

**Type:** Integer  
**Default:** `4455`  
**Example:**

```bash
GoExport.exe --obs-websocket-port 4455
```

#### `--obs-websocket-password`

Set the OBS WebSocket password.

**Type:** String  
**Default:** Empty string  
**Example:**

```bash
GoExport.exe --obs-websocket-password "mySecurePassword123"
```

**Security Note:** Avoid hardcoding passwords in scripts. Use environment variables or configuration files.

#### `--obs-fps`

Set the OBS recording frame rate.

**Type:** Integer  
**Default:** `60`  
**Valid values:** Any positive integer (common: 24, 30, 60, 120)

**Example:**

```bash
GoExport.exe --obs-fps 30
```

#### `--obs-no-overwrite`

Prevent overwriting existing OBS scene/profile.

**Type:** Boolean flag  
**Default:** `false`  
**Example:**

```bash
GoExport.exe --obs-no-overwrite
```

**Note:** By default, GoExport creates a temporary profile/scene. This flag prevents that behavior.

#### `--obs-required`

Require OBS connection for capture (fail if OBS is unavailable).

**Type:** Boolean flag  
**Default:** `false`  
**Example:**

```bash
GoExport.exe --obs-required
```

**Note:** If OBS is not available and this flag is set, export will fail instead of falling back to native capture.

---

### Output Configuration

#### `--output-path`

Specify a custom output path for the final rendered video.

**Type:** String (file path)  
**Default:** `output/` directory  
**Example:**

```bash
GoExport.exe --output-path "/path/to/my/video.mp4"
```

---

### Timeout Configuration

#### `--load-timeout`

Timeout in minutes to wait for video to load.

**Type:** Integer  
**Default:** `30`  
**Example:**

```bash
GoExport.exe --load-timeout 45
```

**Note:** Set to `0` to disable the timeout.

#### `--video-timeout`

Timeout in minutes to wait for video to finish after loading.

**Type:** Integer  
**Default:** `0` (disabled)  
**Example:**

```bash
GoExport.exe --video-timeout 10
```

---

### Linux-Specific Parameters

#### `--x11grab-display`

**Platform:** Linux only

Set the X11 display for FFmpeg's x11grab input device when using native capture mode.

**Type:** String  
**Default:** `:0.0`  
**Example:**

```bash
GoExport --x11grab-display ":1.0"
```

**Valid formats:**
- `:0.0` - Display 0, screen 0 (default)
- `:1.0` - Display 1, screen 0
- `:0.1` - Display 0, screen 1

**Note:** This parameter only affects Linux systems using native capture mode. It has no effect on Windows or when using OBS capture mode. Use this if you have multiple displays or X11 servers running.

#### `--pulse-audio`

**Platform:** Linux only

Set the PulseAudio source for FFmpeg audio capture when using native capture mode.

**Type:** String  
**Default:** `alsa_output.pci-0000_00_1b.0.analog-stereo.monitor`  
**Example:**

```bash
GoExport --pulse-audio "alsa_output.usb-0000_00_1d.0.analog-stereo.monitor"
```

**Note:** Use `pactl list sources` to find available PulseAudio sources on your system.

---

### Advanced FFmpeg Parameters

These parameters provide advanced control over FFmpeg commands for users who need fine-tuned control over recording and encoding. Use with caution as incorrect values may cause failures.

#### `--ffmpeg-linux-args`

**Platform:** Linux only

Append custom arguments to the FFmpeg command used for Linux screen recording (native capture mode only).

**Type:** String  
**Default:** None  
**Example:**

```bash
GoExport --ffmpeg-linux-args "-threads 4 -filter:v 'eq=brightness=0.06:saturation=2'"
```

**Note:** Arguments are added before the output file. Ensure arguments are properly quoted if they contain spaces. This only affects native capture mode, not OBS mode.

#### `--ffmpeg-windows-args`

**Platform:** Windows only

Append custom arguments to the FFmpeg command used for Windows screen recording (native capture mode only).

**Type:** String  
**Default:** None  
**Example:**

```bash
GoExport.exe --ffmpeg-windows-args "-threads 4 -framerate 60"
```

**Note:** Arguments are added before the output file. Ensure arguments are properly quoted if they contain spaces. This only affects native capture mode, not OBS mode.

#### `--ffmpeg-encode-args`

**Platform:** All

Append custom arguments to the FFmpeg command used for video encoding (re-encoding raw captures to final output).

**Type:** String  
**Default:** None  
**Example:**

```bash
GoExport.exe --ffmpeg-encode-args "-maxrate 5M -bufsize 10M"
```

**Note:** Arguments are added before the output file. Ensure arguments are properly quoted if they contain spaces.

#### `--ffmpeg-linux-override`

**Platform:** Linux only  
**Advanced users only**

Completely override the FFmpeg command used for Linux screen recording. Use `{output}` as a placeholder for the output file path.

**Type:** String  
**Default:** None  
**Example:**

```bash
GoExport --ffmpeg-linux-override "ffmpeg -f x11grab -video_size 1920x1080 -i :0.0 -c:v libx264 -preset ultrafast {output}"
```

**Warning:** This completely replaces the default command. You must ensure the command is valid and includes all necessary parameters. The `{output}` placeholder will be replaced with the actual output file path.

#### `--ffmpeg-windows-override`

**Platform:** Windows only  
**Advanced users only**

Completely override the FFmpeg command used for Windows screen recording. Use `{output}` as a placeholder for the output file path.

**Type:** String  
**Default:** None  
**Example:**

```bash
GoExport.exe --ffmpeg-windows-override "ffmpeg -f dshow -i video=\"screen-capture-recorder\" -c:v libx264 {output}"
```

**Warning:** This completely replaces the default command. You must ensure the command is valid and includes all necessary parameters. The `{output}` placeholder will be replaced with the actual output file path.

#### `--ffmpeg-encode-override`

**Platform:** All  
**Advanced users only**

Completely override the FFmpeg command used for video encoding. Use `{input}` and `{output}` as placeholders for input and output file paths.

**Type:** String  
**Default:** None  
**Example:**

```bash
GoExport.exe --ffmpeg-encode-override "ffmpeg -i {input} -c:v libx265 -crf 28 -preset fast {output}"
```

**Warning:** This completely replaces the default command. You must ensure the command is valid and includes all necessary parameters. The `{input}` and `{output}` placeholders will be replaced with the actual file paths.

---

### Monitor Configuration

#### `--skip-resolution-check`

Skip the resolution check that validates the selected resolution doesn't exceed monitor resolution.

**Type:** Boolean flag  
**Default:** `false`  
**Example:**

```bash
GoExport.exe --skip-resolution-check
```

**Note:** Useful for multi-monitor setups or virtual displays where resolution validation may fail incorrectly.

#### `--monitor-index`

Select which monitor to use for resolution checking in multi-monitor setups.

**Type:** Integer  
**Default:** `0`  
**Example:**

```bash
GoExport.exe --monitor-index 1
```

**Note:** Uses 0-based indexing (0 = first monitor, 1 = second monitor, etc.).

---

### Protocol URL

#### `--protocol`

Accept a `goexport://` protocol URL containing all parameters.

**Type:** String (URL)  
**Format:** `goexport://[service]?[query_parameters]`

**Example:**

```bash
GoExport.exe --protocol "goexport://local?video_id=123&aspect_ratio=16:9&resolution=1080p"
```

See [Protocol URL Format](#protocol-url-format) section for detailed syntax.

---

## Protocol URL Format

The `goexport://` protocol allows external applications and browsers to launch GoExport with pre-configured parameters.

### Syntax

```
goexport://[service]?key1=value1&key2=value2&...
```

**Components:**

- **Scheme:** `goexport://` (required)
- **Service:** Service identifier (e.g., `local`, `ft`) or in query params
- **Query Parameters:** URL-encoded key-value pairs

### Query Parameters

| Parameter                | Maps to CLI Flag               | Type    | Description                                    |
| ------------------------ | ------------------------------ | ------- | ---------------------------------------------- |
| `service`                | `--service`                    | String  | Service identifier                             |
| `video_id`               | `--movie-id`                   | String  | Video/Movie ID                                 |
| `user_id`                | `--owner-id`                   | String  | Owner/User ID                                  |
| `aspect_ratio`           | `--aspect_ratio`               | String  | Aspect ratio (e.g., `16:9`)                    |
| `resolution`             | `--resolution`                 | String  | Resolution (e.g., `1080p`)                     |
| `no_input`               | `--no-input`                   | Boolean | Skip user prompts                              |
| `open_folder`            | `--open-file`                  | Boolean | Open output folder after completion            |
| `use_outro`              | `--use-outro`                  | Boolean | Add outro to video                             |
| `output_path`            | `--output-path`                | String  | Custom output path                             |
| `load_timeout`           | `--load-timeout`               | Integer | Video load timeout (minutes)                   |
| `video_timeout`          | `--video-timeout`              | Integer | Video completion timeout (minutes)             |
| `x11grab_display`        | `--x11grab-display`            | String  | X11 display (Linux only, e.g., `:0.0`)         |
| `pulse_audio`            | `--pulse-audio`                | String  | PulseAudio source (Linux only)                 |
| `ffmpeg_linux_args`      | `--ffmpeg-linux-args`          | String  | Custom FFmpeg args for Linux recording         |
| `ffmpeg_windows_args`    | `--ffmpeg-windows-args`        | String  | Custom FFmpeg args for Windows recording       |
| `ffmpeg_encode_args`     | `--ffmpeg-encode-args`         | String  | Custom FFmpeg args for encoding                |
| `ffmpeg_linux_override`  | `--ffmpeg-linux-override`      | String  | Override FFmpeg Linux recording command        |
| `ffmpeg_windows_override`| `--ffmpeg-windows-override`    | String  | Override FFmpeg Windows recording command      |
| `ffmpeg_encode_override` | `--ffmpeg-encode-override`     | String  | Override FFmpeg encoding command               |
| OBS parameters           | See OBS section                | Various | OBS WebSocket configuration                    |

### Boolean Values

Booleans can be specified as:

- `true`, `1`, `yes`, `y`, `t` → True
- `false`, `0`, `no`, `n`, `f` → False
- Any other value or omitted → False

### Service Specification

The service can be specified in two ways:

**1. In the netloc (recommended):**

```
goexport://local?video_id=123
```

**2. In query parameters:**

```
goexport://?service=local&video_id=123
```

### URL Encoding

Special characters in values must be URL-encoded:

- Space: `%20`
- Colon: `%3A`
- Slash: `%2F`

**Example:**

```
goexport://local?video_id=my%20video&aspect_ratio=16%3A9
```

---

## Usage Examples

### Example 1: Basic Export

Export a Wrapper: Offline video at 1080p:

```bash
GoExport.exe --service local --movie-id m-123 --resolution 1080p --aspect-ratio 16:9
```

### Example 2: Automated FlashThemes Export

Export FlashThemes video with all automation enabled:

```bash
GoExport.exe --no-input --service ft --owner-id user456 --movie-id video789 --resolution 720p --aspect-ratio 16:9 --use-outro --open-file
```

### Example 3: OBS High-Quality Capture

Use OBS for capture with custom settings:

```bash
GoExport.exe --service local --movie-id m-999 --obs-websocket-address localhost --obs-websocket-port 4455 --obs-websocket-password "secret" --obs-fps 60 --resolution 4k
```

### Example 4: Protocol URL (Browser Integration)

```
goexport://local?video_id=m-555&aspect_ratio=16:9&resolution=1080p&no_input=true&use_outro=true
```

### Example 5: Vertical Video (9:16)

Export a vertical video for mobile platforms:

```bash
GoExport.exe --service local --movie-id m-vertical --aspect-ratio 9:16 --resolution 1080p
```

### Example 6: Multiple Videos Workflow

First video:

```bash
GoExport.exe --service local --movie-id m-001 --resolution 1080p
```

When prompted, choose to add another video, then:

```bash
# GoExport will prompt for next video ID
```

### Example 7: Debugging Export Issues

Enable verbose logging:

```bash
GoExport.exe --verbose --service local --movie-id m-debug
```

Check logs in `logs/YYYY-MM-DD/` for detailed execution trace.

### Example 8: Classic 4:3 Export

Export in classic 4:3 aspect ratio:

```bash
GoExport.exe --service local --movie-id m-classic --aspect-ratio 4:3 --resolution 480p
```

---

## Parameter Validation

### Required Parameters

The following parameters are **always required** (either via CLI or prompts):

- Service (`--service`)
- Movie ID (`--movie-id`)
- Aspect Ratio (`--aspect_ratio`, defaults to 16:9)
- Resolution (`--resolution`, defaults to 360p)

### Service-Specific Requirements

Some services require additional parameters:

| Service      | Required Parameters    |
| ------------ | ---------------------- |
| `local`      | `movie_id`             |
| `ft`         | `movie_id`, `owner_id` |
| `local_beta` | `movie_id`             |

### Resolution Validation

Resolutions are validated against the selected aspect ratio. Invalid combinations will be rejected:

**Valid for 4:3:**

- 240p, 360p, 420p, 480p

**Valid for 16:9 and 14:9:**

- 360p, 480p, 720p, 1080p, 2k, 4k, 5k, 8k

**Valid for 9:16:**

- 360p, 480p, 720p, 1080p, 2k, 4k, 5k, 8k

### Parameter Precedence

When parameters are provided through multiple methods:

1. **Protocol URL** (highest priority)
2. **CLI flags**
3. **Saved preferences** (`data.json`)
4. **User prompts** (lowest priority)

Example:

```bash
# Protocol overrides CLI
GoExport.exe --service ft --protocol "goexport://local?video_id=123"
# Result: Uses service=local from protocol
```

---

## Error Handling

### Invalid Service

```bash
GoExport.exe --service invalid_service
# Error: Service 'invalid_service' not found in AVAILABLE_SERVICES
```

### Missing Required Parameter

```bash
GoExport.exe --no-input --service ft --movie-id 123
# Error: FlashThemes requires --owner-id parameter
```

### Invalid Resolution

```bash
GoExport.exe --aspect-ratio 4:3 --resolution 1080p
# Error: Resolution '1080p' not available for aspect ratio '4:3'
```

### Protocol Parse Error

```bash
GoExport.exe --protocol "not-a-valid-url"
# Error: Invalid protocol URL format
```

---

## Best Practices

### 1. Use `--no-input` for Automation

When scripting or integrating with other tools, always use `--no-input` with all required parameters:

```bash
GoExport.exe --no-input --service local --movie-id m-123 --resolution 1080p --aspect-ratio 16:9
```

### 2. Enable Verbose for Troubleshooting

Always use `--verbose` when debugging issues:

```bash
GoExport.exe --verbose --service local --movie-id m-problem
```

### 3. Secure OBS Passwords

Don't hardcode passwords in scripts. Use environment variables:

```bash
# Linux/macOS
export OBS_PASSWORD="myPassword"
GoExport.exe --obs-websocket-password "$OBS_PASSWORD"

# Windows PowerShell
$env:OBS_PASSWORD = "myPassword"
GoExport.exe --obs-websocket-password $env:OBS_PASSWORD
```

### 4. Validate Before Batch Processing

Test with a single video before processing multiple videos:

```bash
# Test first
GoExport.exe --service local --movie-id m-test --resolution 720p

# Then batch process
for id in m-001 m-002 m-003; do
    GoExport.exe --no-input --service local --movie-id $id --resolution 720p
done
```

### 5. Use Protocol URLs for Browser Integration

Register the `goexport://` protocol handler (see [PROTOCOL_SETUP.md](PROTOCOL_SETUP.md)) to enable one-click exports from web interfaces.

---

## See Also

- [PROTOCOL_SETUP.md](PROTOCOL_SETUP.md) - Protocol handler installation guide
- [CONFIGURATION.md](CONFIGURATION.md) - Config.py settings reference
- [OBS.md](../OBS.md) - OBS setup and configuration
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
