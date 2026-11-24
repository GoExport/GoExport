# Changelog

## [2.0.0]

#### Note: MacOS isn't supported, the build is present but it doesn't work properly. If you want to contribute, help on the MacOS build is appreciated.

- Reworked GoExport into `record` and frame-by-frame `export` CLI commands with shared validation and platform-aware runtime configuration.
- Added newline-delimited JSON progress, completion, and error reporting for programmatic CLI use.
- Added the `doctor` command for checking the local GoExport runtime setup.
- Added Windows, Linux, and macOS recording and release builds, including packaged GoExport GUI companions.
- Added automated Chromium, ChromeDriver, Flash, and FFmpeg runtime dependency installation.
- Improved recording, audio alignment, FFmpeg processing, cleanup, and cross-platform stability.
- Added interactive Cloudflare verification: GoExport pauses when a challenge appears and lets you complete it in its own browser session (the Chromium window on Windows, a bundled VNC viewer on Linux), then resumes the export automatically.
- Added an optional, per-user `goexport://` URL protocol that needs no installer or administrator rights: `install protocol`, `uninstall protocol` and `status` manage it on Windows (HKCU registry) and Linux (XDG desktop entry), with an experimental macOS Launch Services applet for source runs. Registrations are owned and verified by GoExport, are never overwritten when another application owns the scheme, and are reported as stale if GoExport is moved.
- Added `goexport://record?movie_id=...` links, which are validated, shown for confirmation, and run through the normal `record` command. GoExport V1 links are not accepted and are explained instead.
- Added a Components page to the GUI (Advanced ▸ Manage components…) for installing, repairing and removing the URL protocol.
- Added the `[protocol] output_dir` setting for recordings started from links.
- Rewrote the README as an entry point and brought the wiki up to date, including a complete CLI reference.
- Added Anubis verification support for sites such as FlashThemes: GoExport waits for Anubis' proof-of-work check to finish in its own browser, only showing the browser if the check stalls, and explains when a site's check cannot run in Chromium 87.
