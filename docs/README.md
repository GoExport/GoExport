# GoExport Documentation

Complete documentation for GoExport - automated video export tool for Flash-based video makers.

## Quick Start

New to GoExport? Start here:

1. **[Main README](../readme.md)** - Installation, dependencies, and basic usage
2. **[PARAMETERS.md](PARAMETERS.md)** - Command-line parameters and protocol URLs
3. **[OBS.md](../OBS.md)** - OBS Studio setup for capture

## Documentation Index

### Setup & Installation

| Document                                   | Description                                                 |
| ------------------------------------------ | ----------------------------------------------------------- |
| **[README.md](../readme.md)**              | Main documentation, installation guide, dependencies        |
| **[PROTOCOL_SETUP.md](PROTOCOL_SETUP.md)** | Setup `goexport://` protocol handler on Windows/Linux/macOS |
| **[LINUX_SETUP.md](LINUX_SETUP.md)**       | Linux-specific setup including PATH configuration           |
| **[OBS.md](../OBS.md)**                    | OBS Studio configuration for video capture                  |

### Configuration & Usage

| Document                                 | Description                                              |
| ---------------------------------------- | -------------------------------------------------------- |
| **[PARAMETERS.md](PARAMETERS.md)**       | Complete CLI parameter reference and protocol URL format |
| **[CONFIGURATION.md](CONFIGURATION.md)** | config.py settings, resolutions, aspect ratios, services |
| **[CAPTURE_MODES.md](CAPTURE_MODES.md)** | OBS vs Native capture modes, setup, and troubleshooting  |

### Advanced Topics

| Document                                                   | Description                                         |
| ---------------------------------------------------------- | --------------------------------------------------- |
| **[FFMPEG_OPERATIONS.md](FFMPEG_OPERATIONS.md)**           | Video processing pipeline, FFmpeg commands, editing |
| **[ADDING_NEW_SERVICES.md](ADDING_NEW_SERVICES.md)**       | How to add support for new video services           |
| **[DYNAMIC_SERVICES_GUIDE.md](DYNAMIC_SERVICES_GUIDE.md)** | Dynamic service loading in the UI                   |

### Troubleshooting & Development

| Document                                     | Description                                     |
| -------------------------------------------- | ----------------------------------------------- |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Comprehensive troubleshooting for all platforms |
| **[DEVELOPMENT.md](DEVELOPMENT.md)**         | Development setup, architecture, contributing   |

## Documentation by Topic

### Getting Started

**I'm installing GoExport for the first time:**

1. [README.md](../readme.md) - Installation & Dependencies
2. [OBS.md](../OBS.md) - OBS Setup (recommended)
3. [PARAMETERS.md](PARAMETERS.md) - Running your first export

**I'm on Linux:**

1. [LINUX_SETUP.md](LINUX_SETUP.md) - Complete Linux setup guide
2. [PROTOCOL_SETUP.md](PROTOCOL_SETUP.md#linux-setup) - Protocol handler setup

### Configuration

**I want to understand command-line parameters:**

- [PARAMETERS.md](PARAMETERS.md) - All parameters with examples

**I want to configure services or resolutions:**

- [CONFIGURATION.md](CONFIGURATION.md) - Complete config.py reference

**I want to set up protocol URLs (goexport://):**

- [PROTOCOL_SETUP.md](PROTOCOL_SETUP.md) - Complete setup guide
- [PARAMETERS.md](PARAMETERS.md#protocol-url-format) - Protocol syntax

### Capture & Recording

**I want to choose between OBS and Native capture:**

- [CAPTURE_MODES.md](CAPTURE_MODES.md) - Comparison and setup

**I'm having capture issues:**

- [CAPTURE_MODES.md](CAPTURE_MODES.md#troubleshooting) - Capture troubleshooting
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md#capture-issues) - Common capture problems

**I want to configure OBS:**

- [OBS.md](../OBS.md) - Complete OBS setup guide
- [CAPTURE_MODES.md](CAPTURE_MODES.md#obs-capture-mode) - OBS mode details

### Video Processing

**I want to understand how video editing works:**

- [FFMPEG_OPERATIONS.md](FFMPEG_OPERATIONS.md) - Complete FFmpeg operations guide

**I'm having rendering issues:**

- [FFMPEG_OPERATIONS.md](FFMPEG_OPERATIONS.md#troubleshooting) - Video processing troubleshooting
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md#export--rendering-issues) - Export problems

### Customization

**I want to add a new video service:**

- [ADDING_NEW_SERVICES.md](ADDING_NEW_SERVICES.md) - Step-by-step guide
- [CONFIGURATION.md](CONFIGURATION.md#service-configuration) - Service config reference

**I want to add custom resolutions:**

- [CONFIGURATION.md](CONFIGURATION.md#adding-custom-resolutions) - Resolution setup

**I want to understand the codebase:**

- [DEVELOPMENT.md](DEVELOPMENT.md) - Architecture and code structure

### Troubleshooting

**Something isn't working:**

1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Start here
2. Check specific module docs for detailed troubleshooting

**Platform-specific issues:**

- Windows: [TROUBLESHOOTING.md](TROUBLESHOOTING.md#windows)
- Linux: [LINUX_SETUP.md](LINUX_SETUP.md#gui-troubleshooting) + [TROUBLESHOOTING.md](TROUBLESHOOTING.md#linux)
- macOS: [TROUBLESHOOTING.md](TROUBLESHOOTING.md#macos)

### Contributing

**I want to contribute to GoExport:**

1. [DEVELOPMENT.md](DEVELOPMENT.md) - Development setup and guidelines
2. [DEVELOPMENT.md](DEVELOPMENT.md#contributing-guidelines) - How to contribute

## Common Tasks

### Export a Video

```bash
# Basic export
GoExport.exe --service local --movie-id m-123 --resolution 1080p --aspect-ratio 16:9

# Automated export with outro
GoExport.exe --no-input --service local --movie-id m-456 --resolution 720p --use-outro --open-file

# Protocol URL
goexport://local?video_id=m-789&resolution=1080p&aspect_ratio=16:9&no_input=true
```

See: [PARAMETERS.md](PARAMETERS.md#usage-examples)

### Configure OBS Capture

1. Install OBS Studio
2. Enable WebSocket server (Tools → WebSocket Server Settings)
3. Run GoExport with OBS parameters:

```bash
GoExport.exe --obs-websocket-address localhost --obs-websocket-port 4455 --obs-websocket-password "yourpass"
```

See: [OBS.md](../OBS.md) + [CAPTURE_MODES.md](CAPTURE_MODES.md#obs-capture-mode)

### Add a New Service

1. Edit `config.py`
2. Add service to `AVAILABLE_SERVICES`:

```python
"my_service": {
    "name": "My Service Name",
    "requires": {"movieId"},
    "domain": ["https://myservice.com"],
    "player": ["https://myservice.com/player", "?id={movie_id}"],
    "window": "My Service Player"
}
```

3. Restart GoExport

See: [ADDING_NEW_SERVICES.md](ADDING_NEW_SERVICES.md)

### Set Up Protocol Handler (Linux)

```bash
# Create desktop entry
cat > ~/.local/share/applications/goexport-protocol.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=GoExport Protocol Handler
Exec=/opt/GoExport/GoExport --protocol %u
StartupNotify=false
MimeType=x-scheme-handler/goexport;
NoDisplay=true
Terminal=false
EOF

# Register
update-desktop-database ~/.local/share/applications/
xdg-mime default goexport-protocol.desktop x-scheme-handler/goexport
```

See: [PROTOCOL_SETUP.md](PROTOCOL_SETUP.md#linux-setup)

## FAQ

### What's the difference between OBS and Native capture?

**OBS Mode:**

- Works on all platforms
- Better quality and performance
- Requires OBS Studio installation

**Native Mode:**

- Windows only
- No external dependencies
- Fallback option

See: [CAPTURE_MODES.md](CAPTURE_MODES.md#comparison)

### How do I add support for a new video service?

Edit `config.py` and add your service to `AVAILABLE_SERVICES`. See [ADDING_NEW_SERVICES.md](ADDING_NEW_SERVICES.md) for complete guide.

### Where are exported videos saved?

Default location: `output/` folder in GoExport installation directory.

### Can I automate exports?

Yes, use `--no-input` mode with all required parameters:

```bash
GoExport.exe --no-input --service local --movie-id m-123 --resolution 1080p --aspect-ratio 16:9
```

See: [PARAMETERS.md](PARAMETERS.md#-ni---no-input)

### What video formats are supported?

GoExport exports to MP4 (H.264 video, AAC audio) by default. See [FFMPEG_OPERATIONS.md](FFMPEG_OPERATIONS.md) for format details.

## Getting Help

### Documentation Search

Use your browser's find function (Ctrl+F / Cmd+F) to search within documents.

### Community Support

- **Discord:** https://discord.gg/ejwJYtQDrS
- **GitHub Issues:** https://github.com/GoExport/GoExport/issues
- **GitHub Discussions:** https://github.com/GoExport/GoExport/discussions

### Reporting Bugs

Include:

1. GoExport version (`--version`)
2. Operating system
3. Capture mode (OBS or Native)
4. Full error message
5. Relevant log excerpt
6. Steps to reproduce

See: [TROUBLESHOOTING.md](TROUBLESHOOTING.md#reporting-issues)

## Document Maintenance

These documents are maintained alongside the codebase. When contributing:

- Update relevant documentation with code changes
- Add examples for new features
- Keep configuration references in sync with `config.py`

See: [DEVELOPMENT.md](DEVELOPMENT.md#documentation)

## License

All documentation is licensed under GPL v3.0, same as the GoExport project.

See: [LICENSE](../LICENSE)

---

**Last Updated:** 2025-10-29  
**GoExport Version:** 0.16.0  
**Maintainer:** [Lexian-droid](https://github.com/Lexian-droid)
