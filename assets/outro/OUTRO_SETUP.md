# Outro Setup Guide

This directory contains outro video files for GoExport.

## Quick Start

To use a custom outro (like the original GoAnimate 2007-2011 outro):

1. Download the outro file from: https://drive.google.com/drive/folders/1s612SdbTAtfQrdNlhx0F5OTzlYyBF_I4
2. Place it in the appropriate subdirectory below
3. Restart GoExport

## Directory Structure

```
outro/
├── wide/       # 16:9 aspect ratio (most common)
├── standard/   # 4:3 aspect ratio
├── classic/    # 14:9 aspect ratio
├── tall/       # 9:16 aspect ratio
└── OUTRO_SETUP.md (this file)
```

## File Naming Convention

Files must be named by their resolution: `{width}x{height}.mp4`

### Wide (16:9) Examples
- `7680x4320.mp4` (8K)
- `3840x2160.mp4` (4K)
- `1920x1080.mp4` (1080p) ← GoAnimate outro goes here
- `1280x720.mp4` (720p)
- `854x480.mp4` (480p)
- `640x360.mp4` (360p)

## Adding the GoAnimate Outro

The original GoAnimate 2007-2011 outro (1920x1080, 16:9) should be placed in:

```
assets/outro/wide/1920x1080.mp4
```

For detailed setup instructions, see: [CUSTOM_OUTROS.md](../docs/CUSTOM_OUTROS.md)

## Video Requirements

All outro files must meet these specifications:

- **Video Codec:** H.264 (libx264)
- **Audio Codec:** AAC
- **Container:** MP4
- **Resolution:** Must match filename exactly
- **Frame Rate:** Match your export FPS (typically 24fps)
- **Duration:** 3-10 seconds recommended

## Creating Custom Resolutions

If you need a resolution not in the folders, create it by resizing an existing outro:

```bash
# Resize to 1280x720
ffmpeg -i wide/1920x1080.mp4 -vf scale=1280:720 -c:a copy wide/1280x720.mp4

# Resize to 640x480 (4:3)
ffmpeg -i wide/1920x1080.mp4 -vf "scale=640:480,pad=640:480:(ow-iw)/2:(oh-ih)/2" -c:a copy standard/640x480.mp4
```

## Support

For issues with outros, see:
- [CUSTOM_OUTROS.md](../docs/CUSTOM_OUTROS.md) - Full custom outro guide
- [CONFIGURATION.md](../docs/CONFIGURATION.md) - Outro configuration reference
- [TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) - Troubleshooting guide
