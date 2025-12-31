# GoExport FFmpeg Operations

Complete reference for video processing pipeline, FFmpeg commands, and troubleshooting.

## Table of Contents

- [Overview](#overview)
  - [Custom FFmpeg Arguments](#custom-ffmpeg-arguments-v119)
  - [Built-in Default FFmpeg Commands](#built-in-default-ffmpeg-commands)
- [Editor Architecture](#editor-architecture)
- [FFmpeg Commands](#ffmpeg-commands)
- [Video Processing Pipeline](#video-processing-pipeline)
- [Concatenation Modes](#concatenation-modes)
- [Troubleshooting](#troubleshooting)

## Overview

GoExport uses **FFmpeg directly** (not MoviePy) for all video processing operations:

- **Clip trimming** - Precise frame-accurate cuts
- **Video concatenation** - Joining multiple videos
- **Format conversion** - Transcoding to MP4/H.264
- **Resolution scaling** - Resize and aspect ratio correction
- **Outro addition** - Append end screens

**Why FFmpeg?**

- Better performance
- Lower memory usage
- More reliable across platforms
- Direct control over encoding parameters

### Custom FFmpeg Arguments (v1.1.9+)

GoExport now supports custom FFmpeg arguments for advanced users who need fine-grained control:

**Append Custom Arguments:**
- `--ffmpeg-linux-args` - Add arguments to Linux recording commands
- `--ffmpeg-windows-args` - Add arguments to Windows recording commands  
- `--ffmpeg-encode-args` - Add arguments to encoding commands

**Override Complete Commands:**
- `--ffmpeg-linux-override` - Replace entire Linux recording command
- `--ffmpeg-windows-override` - Replace entire Windows recording command
- `--ffmpeg-encode-override` - Replace entire encoding command

Use `{output}` placeholder for output files and `{input}` for input files when using override commands.

**Example:**
```bash
# Add custom arguments
GoExport --ffmpeg-encode-args "-maxrate 5M -bufsize 10M"

# Override entire command
GoExport --ffmpeg-encode-override "ffmpeg -i {input} -c:v libx265 -crf 28 {output}"
```

See [PARAMETERS.md](PARAMETERS.md) for detailed usage.

### Built-in Default FFmpeg Commands

This section documents the exact FFmpeg commands GoExport uses by default. Understanding these helps you decide what custom arguments to add or override.

#### Windows Screen Recording (Native Capture)

**Default Command:**
```bash
ffmpeg -y -f dshow -rtbufsize 1500M \
  -i video=screen-capture-recorder:audio=virtual-audio-capturer \
  -vf crop={width}:{height}:0:0 \
  -c:v libx264 -preset ultrafast -crf 0 -tune zerolatency \
  -pix_fmt yuv420p -c:a pcm_s16le -ar 44100 \
  {output}
```

**Parameter Breakdown:**
- `-y` - Overwrite output file without asking
- `-f dshow` - Use DirectShow input format (Windows)
- `-rtbufsize 1500M` - Increase real-time buffer to prevent frame drops
- `-i video=screen-capture-recorder:audio=virtual-audio-capturer` - Capture device names
- `-vf crop={width}:{height}:0:0` - Crop to exact dimensions from top-left
- `-c:v libx264` - Use H.264 video codec
- `-preset ultrafast` - Fastest encoding to keep up with real-time capture
- `-crf 0` - Lossless quality (CRF 0 = no compression loss)
- `-tune zerolatency` - Optimize for real-time encoding
- `-pix_fmt yuv420p` - Standard pixel format for compatibility
- `-c:a pcm_s16le` - Uncompressed 16-bit PCM audio
- `-ar 44100` - Audio sample rate (44.1kHz)

**Why These Settings:**
- `ultrafast` preset minimizes CPU load during capture
- `crf 0` ensures no quality loss during recording
- Raw audio (`pcm_s16le`) avoids encoding overhead
- High buffer size prevents dropped frames

**Common Customizations:**
```bash
# Increase framerate to 60fps
--ffmpeg-windows-args "-framerate 60"

# Add video filter for brightness
--ffmpeg-windows-args "-vf 'eq=brightness=0.06'"
```

#### Linux Screen Recording (Native Capture)

**Default Command:**
```bash
ffmpeg -y -f x11grab -s {width}x{height} -i {display} \
  -f pulse -i {audio_source} -ac 2 \
  -c:v libx264 -preset ultrafast -crf 0 -tune zerolatency \
  -pix_fmt yuv420p -c:a pcm_s16le -ar 44100 \
  {output}
```

**Parameter Breakdown:**
- `-y` - Overwrite output file without asking
- `-f x11grab` - Use X11 screen grabber (Linux)
- `-s {width}x{height}` - Capture dimensions
- `-i {display}` - X11 display to capture (default: `:0.0`)
- `-f pulse` - Use PulseAudio for audio capture
- `-i {audio_source}` - PulseAudio source (default: `alsa_output.pci-0000_00_1b.0.analog-stereo.monitor`)
- `-ac 2` - Stereo audio (2 channels)
- `-c:v libx264` - Use H.264 video codec
- `-preset ultrafast` - Fastest encoding for real-time capture
- `-crf 0` - Lossless quality
- `-tune zerolatency` - Optimize for real-time encoding
- `-pix_fmt yuv420p` - Standard pixel format
- `-c:a pcm_s16le` - Uncompressed 16-bit PCM audio
- `-ar 44100` - Audio sample rate (44.1kHz)

**Why These Settings:**
- X11grab directly captures from X server
- PulseAudio monitor captures system audio
- Same quality/performance philosophy as Windows

**Common Customizations:**
```bash
# Capture from different display
--x11grab-display ":1.0"

# Use different audio source
--pulse-audio "alsa_output.usb-0000_00_1d.0.analog-stereo.monitor"

# Add custom threading
--ffmpeg-linux-args "-threads 4"
```

#### Video Encoding (Post-Capture Processing)

**Default Command:**
```bash
ffmpeg -y -i {input} \
  -vf crop={width}:{height}:0:0,format=yuv420p \
  -c:v libx264 -preset {preset} -crf {crf} -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 44100 \
  {output}
```

**Parameter Breakdown:**
- `-y` - Overwrite output file without asking
- `-i {input}` - Input file (raw capture)
- `-vf crop={width}:{height}:0:0,format=yuv420p` - Video filters for cropping and format
- `-c:v libx264` - Use H.264 video codec
- `-preset {preset}` - Encoding speed/quality trade-off (default: `medium`)
- `-crf {crf}` - Constant Rate Factor quality (default: `23`, range: 0-51)
- `-pix_fmt yuv420p` - Standard pixel format for maximum compatibility
- `-c:a aac` - Use AAC audio codec
- `-b:a 128k` - Audio bitrate (128 kbps)
- `-ar 44100` - Audio sample rate (44.1kHz)

**Preset Options (Speed vs Quality):**
- `ultrafast` - Fastest, largest file size
- `superfast`, `veryfast`, `faster`, `fast` - Speed/size trade-offs
- `medium` - **Default** - Good balance
- `slow`, `slower`, `veryslow` - Better compression, slower encoding

**CRF Quality Scale:**
- `0` - Lossless (huge file size)
- `18-23` - Visually lossless to high quality
- `23` - **Default** - Good quality, reasonable file size
- `28-32` - Medium quality, smaller files
- `51` - Worst quality (smallest files)

**Why These Settings:**
- Converts raw capture to compressed MP4
- AAC audio is universally compatible
- CRF 23 provides excellent quality at reasonable file size
- `medium` preset balances speed and compression

**Common Customizations:**
```bash
# Higher quality encoding
--ffmpeg-encode-args "-crf 18 -preset slow"

# Smaller file size
--ffmpeg-encode-args "-crf 28 -preset faster"

# Add bitrate limiting
--ffmpeg-encode-args "-maxrate 5M -bufsize 10M"

# Switch to HEVC/H.265 (smaller files, slower encoding)
--ffmpeg-encode-override "ffmpeg -i {input} -c:v libx265 -crf 28 -preset medium -c:a aac -b:a 128k {output}"
```

#### Finding Available Audio Sources (Linux)

To find PulseAudio sources on your system:

```bash
pactl list sources | grep -E '(Name:|Description:)'
```

Example output:
```
Name: alsa_output.pci-0000_00_1b.0.analog-stereo.monitor
Description: Monitor of Built-in Audio Analog Stereo
Name: alsa_input.pci-0000_00_1b.0.analog-stereo
Description: Built-in Audio Analog Stereo
```

Use the `Name:` value with `--pulse-audio` parameter.

## Editor Architecture

### Editor Class (`modules/editor.py`)

The `Editor` class manages video clips and rendering:

```python
from modules.editor import Editor

# Create editor instance
editor = Editor()

# Add clips
editor.add_clip("video1.mp4")
editor.add_clip("video2.mp4")

# Trim clip (clip_id, start_seconds, end_seconds)
editor.trim(0, 5.0, 30.0)

# Render final video
editor.render("output.mp4", reencode=True, target_width=1920, target_height=1080, fps=30)
```

### Core Methods

**`add_clip(path, position=-1)`**

- Adds video file to clip list
- Optional position parameter for insertion
- Validates file existence

**`trim(clip_id, start, end)`**

- Trims clip using FFmpeg `-ss` and `-t`
- Creates new file with `_trimmed_{start}_{end}` suffix
- Updates clip reference in list

**`get_clip_length(clip_id)`**

- Uses `ffprobe` to get duration
- Returns float (seconds)

**`render(output, reencode, target_width, target_height, fps)`**

- Two modes: fast concat (no re-encode) or safe concat (re-encode)
- See [Concatenation Modes](#concatenation-modes)

**`export_to_file()`**

- Creates `clips.txt` for FFmpeg concat demuxer
- Normalizes paths for cross-platform compatibility

## FFmpeg Commands

### Getting Clip Duration

**Command:**

```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 video.mp4
```

**Parameters:**

- `-v error` - Suppress info messages
- `-show_entries format=duration` - Show only duration
- `-of default=noprint_wrappers=1:nokey=1` - Output just the number

**Output:**

```
120.5
```

### Trimming a Clip

**Command:**

```bash
ffmpeg -ss 5.0 -i input.mp4 -c copy -t 25.0 output_trimmed_5.0_30.0.mp4
```

**Parameters:**

- `-ss 5.0` - Start time (seek to 5 seconds)
- `-i input.mp4` - Input file
- `-c copy` - Stream copy (no re-encode)
- `-t 25.0` - Duration (30.0 - 5.0 = 25 seconds)

**Why `-ss` before `-i`?**

- Faster seeking (input seeking vs output seeking)
- More accurate for H.264 keyframes

**Stream Copy vs Re-encode:**

- **Stream copy (`-c copy`)** - Fast, lossless, but limited to keyframe boundaries
- **Re-encode** - Slower, frame-accurate, quality loss

### Fast Concatenation (No Re-encode)

**clips.txt:**

```
file 'D:/Videos/clip1.mp4'
file 'D:/Videos/clip2.mp4'
file 'D:/Videos/clip3.mp4'
```

**Command:**

```bash
ffmpeg -y -f concat -safe 0 -i clips.txt -c copy output.mp4
```

**Parameters:**

- `-y` - Overwrite output without asking
- `-f concat` - Use concat demuxer
- `-safe 0` - Allow absolute paths
- `-i clips.txt` - Input file list
- `-c copy` - Stream copy (no transcoding)

**Requirements:**

- All clips must have identical:
  - Video codec
  - Audio codec
  - Resolution
  - Frame rate
  - Pixel format

### Safe Concatenation (Re-encode)

**Command:**

```bash
ffmpeg -y \
  -i clip1.mp4 \
  -i clip2.mp4 \
  -i clip3.mp4 \
  -filter_complex "
    [0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,setpts=PTS-STARTPTS[v0];
    [1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,setpts=PTS-STARTPTS[v1];
    [2:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,setpts=PTS-STARTPTS[v2];
    [0:a]aresample=async=1:min_comp=0.001:first_pts=0,asetpts=PTS-STARTPTS[a0];
    [1:a]aresample=async=1:min_comp=0.001:first_pts=0,asetpts=PTS-STARTPTS[a1];
    [2:a]aresample=async=1:min_comp=0.001:first_pts=0,asetpts=PTS-STARTPTS[a2];
    [v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[outv][outa]
  " \
  -map "[outv]" \
  -map "[outa]" \
  -r 30 \
  -c:v libx264 \
  -preset veryfast \
  -crf 23 \
  -pix_fmt yuv420p \
  -c:a aac \
  -b:a 128k \
  -ar 44100 \
  -ac 2 \
  -movflags +faststart \
  output.mp4
```

**Filter Complex Breakdown:**

**Video Processing:**

```
[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,setpts=PTS-STARTPTS[v0]
```

- `scale=1920:1080:force_original_aspect_ratio=decrease` - Scale to fit within bounds
- `pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black` - Add black bars to exact size
- `setsar=1` - Set Sample Aspect Ratio to 1:1
- `setpts=PTS-STARTPTS` - Reset presentation timestamps

**Audio Processing:**

```
[0:a]aresample=async=1:min_comp=0.001:first_pts=0,asetpts=PTS-STARTPTS[a0]
```

- `aresample=async=1:min_comp=0.001:first_pts=0` - Async audio resampling
- `asetpts=PTS-STARTPTS` - Reset audio timestamps

**Concatenation:**

```
[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[outv][outa]
```

- `n=3` - 3 input segments
- `v=1` - 1 video stream per segment
- `a=1` - 1 audio stream per segment
- `[outv][outa]` - Output video and audio

**Encoding Parameters:**

- `-r 30` - Output frame rate
- `-c:v libx264` - H.264 video codec
- `-preset veryfast` - Encoding speed (faster = larger file)
- `-crf 23` - Constant Rate Factor (quality: 0=lossless, 51=worst)
- `-pix_fmt yuv420p` - Pixel format (universal compatibility)
- `-c:a aac` - AAC audio codec
- `-b:a 128k` - Audio bitrate
- `-ar 44100` - Audio sample rate
- `-ac 2` - Audio channels (stereo)
- `-movflags +faststart` - Enable streaming (moov atom at start)

## Video Processing Pipeline

### Export Flow

```
1. Capture
   ├─> OBS Recording
   └─> Native Screen Capture

2. Initial Processing
   ├─> Detect capture start/stop markers
   ├─> Calculate trim points
   └─> Add to editor.clips[]

3. Trimming (Optional)
   ├─> editor.trim(clip_id, start, end)
   └─> Create trimmed_*.mp4 files

4. Add Outro (Optional)
   ├─> Select outro by resolution
   └─> editor.add_clip(outro_path)

5. Concatenation
   ├─> Fast mode: concat demuxer + stream copy
   └─> Safe mode: filter_complex + re-encode

6. Final Output
   └─> Save to output/ folder
```

### Multi-Video Workflow

```
Video 1:
  Capture → Trim → Add to list

Video 2:
  Capture → Trim → Add to list

Video 3:
  Capture → Trim → Add to list

Final:
  Concatenate all → Add outro → Export
```

### Trim Detection

GoExport detects video start/end by monitoring browser console:

**JavaScript Events:**

```javascript
// Video started
obj_DoFSCommand("start"); // Logs timestamp

// Video stopped
obj_DoFSCommand("stop"); // Logs timestamp
```

**Python Detection:**

```python
# Capture console logs
start_time = detect_start_marker()
stop_time = detect_stop_marker()

# Calculate trim points
trim_start = start_time - recording_start
trim_end = stop_time - recording_start

# Trim clip
editor.trim(0, trim_start, trim_end)
```

## Concatenation Modes

### Fast Mode (No Re-encode)

**When to use:**

- All clips from same capture session
- Identical codec/resolution/fps
- Speed is priority
- No format conversion needed

**Advantages:**

- Very fast (seconds, not minutes)
- No quality loss
- Low CPU usage

**Disadvantages:**

- Requires identical formats
- Limited to keyframe boundaries
- May have brief glitches at joins

**Enable:**

```python
editor.render(output="final.mp4", reencode=False)
```

### Safe Mode (Re-encode)

**When to use:**

- Mixed source formats
- Different resolutions
- Adding outro with different specs
- Need frame-accurate joins

**Advantages:**

- Handles any input format
- Perfect frame alignment
- Consistent quality output
- Can resize/scale

**Disadvantages:**

- Slower (minutes for long videos)
- Small quality loss from re-encoding
- High CPU usage

**Enable:**

```python
editor.render(
    output="final.mp4",
    reencode=True,
    target_width=1920,
    target_height=1080,
    fps=30
)
```

### Automatic Mode Selection

GoExport automatically chooses based on scenario:

**Fast mode when:**

- Single video
- No outro
- Auto-edit disabled

**Safe mode when:**

- Multiple videos
- Outro added
- Mixed resolutions
- Format inconsistencies detected

## Troubleshooting

### "Codec does not support stream copy"

**Cause:** Trying to use `-c copy` with incompatible streams

**Solution:** Force re-encode

```python
editor.render(output="final.mp4", reencode=True)
```

### "Invalid duration specification"

**Cause:** Bad trim times (negative, NaN, or beyond clip duration)

**Solution:** Validate trim parameters

```python
duration = editor.get_clip_length(0)
if start < 0 or end > duration or start >= end:
    raise ValueError("Invalid trim times")
```

### "Concat demuxer failed: Unsafe file name"

**Cause:** Absolute paths in `clips.txt` without `-safe 0`

**Solution:** Already handled in `export_to_file()`:

```python
# clips.txt uses normalized paths
file 'D:/Videos/clip1.mp4'  # Forward slashes
```

### "Non-monotonous DTS in output stream"

**Cause:** Timestamp issues when concatenating

**Solution:** Use safe mode with PTS reset:

```python
editor.render(output="final.mp4", reencode=True)
```

The `setpts=PTS-STARTPTS` filter fixes this.

### "Height not divisible by 2"

**Cause:** H.264 requires even dimensions

**Solution:** Already handled in scaling:

```python
# Editor ensures even dimensions
target_width = (target_width // 2) * 2
target_height = (target_height // 2) * 2
```

### Black segments in concatenated video

**Causes:**

- PTS not reset between clips
- Keyframe alignment issues
- Decoder state mismatch

**Solutions:**

**Use safe mode:**

```python
editor.render(output="final.mp4", reencode=True)
```

**Check input files:**

```bash
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate clip.mp4
```

**Validate PTS:**

```bash
ffprobe -v error -show_frames -select_streams v:0 clip.mp4
```

### Audio/Video desync

**Causes:**

- Variable frame rate input
- Audio resampling issues
- Timestamp drift

**Solutions:**

**Force constant frame rate:**

```python
editor.render(output="final.mp4", reencode=True, fps=30)
```

**Check input frame rate:**

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate clip.mp4
```

**Use safe mode with audio resampling:**

```python
# Already included in safe mode
aresample=async=1:min_comp=0.001:first_pts=0
```

### "No such filter: 'aresample'"

**Cause:** Old FFmpeg version without audio filters

**Solution:** Update FFmpeg

```bash
# Check version
ffmpeg -version

# Should be 4.0+
# GoExport bundles recent FFmpeg
```

### Encoding too slow

**Causes:**

- High resolution
- Slow preset
- Software encoding

**Solutions:**

**Use faster preset:**

```python
# Modify editor.py render() method
"-preset", "ultrafast",  # Faster, larger files
```

**Available presets (speed → quality):**

- `ultrafast` - Fastest, largest
- `superfast`
- `veryfast` - GoExport default
- `faster`
- `fast`
- `medium` - Balanced
- `slow`
- `slower`
- `veryslow` - Slowest, smallest

**Hardware encoding (requires modification):**

**NVIDIA NVENC:**

```python
"-c:v", "h264_nvenc",
"-preset", "fast",
"-rc", "vbr",
"-cq", "23",
```

**Intel QuickSync:**

```python
"-c:v", "h264_qsv",
"-preset", "fast",
"-global_quality", "23",
```

**AMD AMF:**

```python
"-c:v", "h264_amf",
"-quality", "speed",
"-rc", "vbr_latency",
"-qp_i", "23",
```

### Output file size too large

**Causes:**

- Low CRF (high quality)
- Fast preset
- High resolution

**Solutions:**

**Increase CRF (lower quality):**

```python
# Modify editor.py render()
"-crf", "28",  # Default: 23, Range: 0-51
```

**Use slower preset:**

```python
"-preset", "slow",  # Better compression
```

**Two-pass encoding (best size):**

```python
# Pass 1
ffmpeg -i input.mp4 -c:v libx264 -b:v 2M -pass 1 -f null /dev/null

# Pass 2
ffmpeg -i input.mp4 -c:v libx264 -b:v 2M -pass 2 output.mp4
```

### "Error trimming clip: ..."

**Causes:**

- File locked by another process
- Insufficient disk space
- Permission denied

**Solutions:**

**Check file locks:**

```bash
# Windows
handle.exe clip.mp4

# Linux
lsof | grep clip.mp4
```

**Check disk space:**

```bash
# Windows
wmic logicaldisk get size,freespace

# Linux
df -h
```

**Check permissions:**

```bash
# Windows
icacls clip.mp4

# Linux
ls -l clip.mp4
chmod 644 clip.mp4
```

## Advanced Operations

### Custom Filters

To add custom FFmpeg filters, modify `editor.render()`:

**Add watermark:**

```python
filter_complex += ";[outv]drawtext=text='GoExport':x=10:y=10:fontsize=24:fontcolor=white[outv]"
```

**Add fade transitions:**

```python
# Between clips
v_chains[0] += ",fade=t=out:st=5:d=1"
v_chains[1] += ",fade=t=in:st=0:d=1"
```

**Color correction:**

```python
v_chains[i] += ",eq=brightness=0.1:saturation=1.2"
```

### Extract Audio Only

```python
import helpers

helpers.try_command(
    helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_FFMPEG_WINDOWS")),
    "-i", "input.mp4",
    "-vn",  # No video
    "-c:a", "copy",
    "audio.aac"
)
```

### Convert to Different Format

```python
import helpers

helpers.try_command(
    helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_FFMPEG_WINDOWS")),
    "-i", "input.mp4",
    "-c:v", "libvpx-vp9",  # VP9 codec
    "-c:a", "libopus",      # Opus audio
    "output.webm"
)
```

### Generate Thumbnail

```python
import helpers

helpers.try_command(
    helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_FFMPEG_WINDOWS")),
    "-i", "input.mp4",
    "-ss", "00:00:05",  # 5 seconds in
    "-vframes", "1",     # 1 frame
    "thumbnail.jpg"
)
```

## See Also

- [CONFIGURATION.md](CONFIGURATION.md) - Configuration reference
- [CAPTURE_MODES.md](CAPTURE_MODES.md) - Capture system details
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting
- [README.md](../readme.md) - Main documentation
