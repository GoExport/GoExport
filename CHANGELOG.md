# Changelog

## [2.0.0]

- Reworked GoExport into `record` and frame-by-frame `export` CLI commands with shared validation and platform-aware runtime configuration.
- Added newline-delimited JSON progress, completion, and error reporting for programmatic CLI use.
- Added the `doctor` command for checking the local GoExport runtime setup.
- Added Windows, Linux, and macOS recording and release builds, including packaged GoExport GUI companions.
- Added automated Chromium, ChromeDriver, Flash, and FFmpeg runtime dependency installation.
- Improved recording, audio alignment, FFmpeg processing, cleanup, and cross-platform stability.
