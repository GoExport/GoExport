# Custom GoAnimate Outros

This guide explains how to install custom outro videos for GoExport, including the original GoAnimate 2007-2011 outro.

## Original GoAnimate Outro (2007-2011)

The original GoAnimate outro from 2007-2011 (without watermark) is available for download:

**Download Link:** https://drive.google.com/drive/folders/1s612SdbTAtfQrdNlhx0F5OTzlYyBF_I4

### Installation Steps

1. **Download the file** from the Google Drive link above
2. **Locate your GoExport installation directory**
3. **Navigate to:** `assets/outro/wide/`
4. **Rename the downloaded file to:** `1920x1080.mp4`
5. **Place the file** in the `assets/outro/wide/` directory
6. **Restart GoExport** if it's running

### File Requirements

- **Resolution:** 1920x1080 (16:9 aspect ratio)
- **Format:** MP4 (H.264 video, AAC audio)
- **Filename:** `1920x1080.mp4`
- **Location:** `assets/outro/wide/1920x1080.mp4`

### Directory Structure

```
GoExport/
├── assets/
│   └── outro/
│       └── wide/
│           ├── 1920x1080.mp4      ← Place the GoAnimate outro here
│           ├── 1280x720.mp4
│           ├── 854x480.mp4
│           └── 640x360.mp4
```

## Using the Custom Outro

### Via GUI
1. Open GoExport
2. Configure your export settings
3. Check the **"Outro"** checkbox before exporting
4. The custom outro will be appended to your video

### Via Command Line
```bash
GoExport.exe --use-outro --no-input --service local --movie-id m-123 --resolution 1080p --aspect-ratio 16:9
```

### Via Protocol URL
```
goexport://local?video_id=m-123&resolution=1080p&aspect_ratio=16:9&use_outro=true
```

## Creating Custom Outros for Other Resolutions

If you need outros for other resolutions (720p, 480p, etc.), you can:

1. **Resize the 1920x1080 outro** to your needed resolution
2. **Use FFmpeg** to resize:

```bash
ffmpeg -i 1920x1080.mp4 -vf scale=1280:720 -c:a copy 1280x720.mp4
```

3. **Place the resized file** in the appropriate folder

### Available Folders by Aspect Ratio

- **Wide (16:9):** `assets/outro/wide/`
- **Standard (4:3):** `assets/outro/standard/`
- **Classic (14:9):** `assets/outro/classic/`
- **Tall (9:16):** `assets/outro/tall/`

## Troubleshooting

### "Outro file not found" error
- Verify the file is in the correct directory
- Check the filename matches the exact resolution (e.g., `1920x1080.mp4`)
- Ensure the file is in MP4 format

### Video codec issues
- The outro must be H.264 (libx264) video codec
- Audio should be AAC codec
- Use FFmpeg to re-encode if needed:

```bash
ffmpeg -i input.mp4 -c:v libx264 -c:a aac output.mp4
```

### File location issues on different platforms

**Windows:**
```
C:\Program Files\GoExport\assets\outro\wide\1920x1080.mp4
```

**Linux:**
```
/opt/GoExport/assets/outro/wide/1920x1080.mp4
```

**macOS:**
```
/Applications/GoExport.app/Contents/Resources/assets/outro/wide/1920x1080.mp4
```

## Credits

- **Original GoAnimate Outro:** Created by Alex Director for the GoAnimate platform (2007-2011)
- **GoExport Integration:** Integrated into GoExport for Wrapper Offline
