# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.5] - 2025-12-30

### Fixed

- Added fix to prevent popup window when console is used or forced.

## [1.1.4] - 2025-12-29

### Added

- Added the ability to pick x11 display on linux to record on using the argument:
  - `--x11-display ":0"` : Replace `:0` with your desired x11 display.

## [1.1.3] - 2025-12-29

### Added

- Added the ability to forcefully enable console mode (useful for process spawning) you can use the argument:
  - `--console` : Forces console mode even if there is no TTY attached. **Warning:** May cause orphaned processes if not used carefully.

## [1.1.2] - 2025-12-25

Merry Christmas! This is a hotfix related to the --json flag added in 1.1.0

### Fixed

- Made it where --json flag also disables printing of non-unicode characters (ASCII, etc) to prevent charmap issues when parsing JSON output.

## [1.1.1] - 2025-12-21

### Fixed

- Fixed an issue where certain videos (ones with movement on the first scene) the recording would start before the movement was reset, this was causing an issue where the recording would start with a glitchy frame. This has been resolved by catching the error and instead adding a 0.1 seek instead of 0.0 seek when loading the video.

## [1.1.0] - 2025-12-20

### Added

- Added the ability to choose custom output filename and directory via command line the argument:
  - `--output-path "C:\Path\To\Dir\filename.mp4"`
- **Server environment optimizations:**
  - Added `--json` (`-j`) argument to enable structured, line-delimited JSON output to STDOUT suitable for real-time parsing
  - When `--json` is provided, STDERR is used for warnings, diagnostics, and error messages
  - `--json` can be used independently or alongside `--no-input` for flexible server integration
  - Added `--load-timeout` argument to limit time waiting for video to load (default: 30 minutes, 0 to disable)
  - Added `--video-timeout` argument to limit time waiting for video to finish after loading (default: 0/disabled)
- **Timeout behavior:**
  - If a timeout is reached, a final structured STDOUT event with `event: "skipped"` and a clear reason is emitted
  - Human-readable timeout explanation is written to STDERR
- **Exit codes:**
  - `0`: Success
  - `1`: Fatal/unhandled error
  - `2`: Skipped due to timeout

## [1.0.0] - 2025-12-08

This is the final release of GoExport beta. With this release, GoExport is now considered stable and ready for production use.

There are no changes in this release.

## [0.17.1] - 2025-11-09

### Fixed

- Fixed a bug where GoExport wouldn't convert certain properties from `goexport://` URLs properly, causing boolean values to return incorrect results.

## [0.17.0] - 2025-11-05

### Fixed

- Fixed an issue where on Native Capture (For Windows), the recording would freeze after a few seconds.

## [0.16.0] - 2025-10-09

This is a large update for both GUI and CLI versions, as well as GoExport for Linux. It fixes various bugs and improves compatibility.

Huge thanks to the following who helped debug, test, and provide feedback for this update:

- @Go!Makers
- @QuaixiAnimations
- @GoSkit2

**Important Announcement**

With the release of GoExport 0.16.0, we've drastically improved third party integration, which also includes first party addons and tools from us.

We're excited to announce that with the release of GoExport v0.16.0, we've introduced a new Wrapper: Offline modification; called "GoExport Mod." You can find it [here](https://github.com/GoExport/GoExport-Mod)

In the future, we also plan to release a chrome extension, which will also integrate with GoExport seamlessly.

### Added

- Added a GUI for Windows and Linux.
- Separated GUI and interactive terminal modes to separate executables for better user experience. `GoExport_CLI.exe` is the command line version, while `GoExport.exe` is the GUI version.
- Added 2K - 8K 16:9 resolutions (2560x1440, 3840x2160, 5120x2880, 7680x4320).
- Added auto update detection and notification for both GUI and CLI versions.
- Added Native Capture for Linux using `ffmpeg` (which is already included) as an alternative to using OBS for screen capturing.
- Added a protocol in the Windows installer to allow opening and executing GoExport from a web browser (for example, type `goexport://?...` in the address bar of your browser to open GoExport with specific parameters) and it'll automatically launch GoExport CLI. This allows for easier integration with third-party tools and websites. **Note: Ensure you have GoExport installed for this to work. If using Linux, you'll have to manually define the protocol handler.**
- Added a variety of documentation files in the repository /docs folder.
- Added a checkbox in the GUI to allow users to choose whether to install documentation files during installation.

### Fixed

- Fixed an issue where GoExport would downscale your video to 720p even if you selected a higher resolution. Credits: [@QuaixiAnimations](https://www.youtube.com/@QuaixiAnimations) and [@GoSkit2](https://www.youtube.com/@GoSkit2)
- Fixed an issue where GoExport would require `Glibc 2.38` on Linux, now requires `Glibc 2.35` instead for improved compatibility. Credits: [@Go!Makers](https://www.youtube.com/@goskit2)
- Added support for more file managers on Linux including Dolphin, Nautilus, Thunar, and PCManFM. Credits: [@Go!Makers](https://www.youtube.com/@goskit2)
- Fixed an issue where GoExport on Linux would not open the browser in Kiosk mode. (Fullscreen)

## [0.15.4] - 2025-09-28

### Added

- Added GoExport to path on Windows during installation, allowing you to run GoExport from any command prompt or terminal without needing to navigate to its installation directory.

### Changed

- GoExport no longer packages the dependencies within the executable. This is to reduce the size of the executable and to minimize load time. The dependencies will remain in the `dependencies` folder in the GoExport installation directory.

## [0.15.3] - 2025-09-06

### Fixed

- Fixed an issue where FlashThemes would respond with a 403 error when trying to check if the website is online.

## [0.15.2] - 2025-09-05

### Fixed

- Added delay to OBS setup to ensure it doesn't crash OBS on slower computers.
- Fixed an issue where default inputs didn't auto populate when no data was in the data.json file.
- Renamed "Local" service to "Wrapper Offline" - You still type "Local" when accessing Wrapper Offline.
- Added a check to ensure the selected service is online, this will hopefully prevent issues where the user selects a service that is offline (for example, Wrapper Offline is not opened).
- Fixed an issue where GoExport didn't report that the selected resolution was too high for the monitor resolution properly.

## [0.15.1] - 2025-09-01

### Fixed

- Fixed an issue where if OBS wasn't installed, GoExport would cease to function.

## [0.15.0] - 2025-09-01

### Added

- Added support for FlashThemes

## [0.14.4] - 2025-08-31

### Fixed

- Fixed an issue where GoExport couldn't automatically detect the correct browser on Linux when capturing with OBS.

### Added

- Added "Local (beta)" service which is a beta version of Local which experiments using Wrapper Offline's own video player, which resolves the watermark issue, but the caveat is that Wrapper Offline requires modification.

## [0.14.3] - 2025-08-31

GoExport's companion app, GoExport Outro Maker, has received an update as well, which is used in conjunction with this update. If you use GOM (GoExport Outro Maker), make sure to update it to the latest version to ensure compatibility.

### Fixed

- Fixed resolution for 14:9 aspect ratio, video now correctly renders in that aspect ratio at any choice of resolution.

## [0.14.2] - 2025-08-30

### Fixed

- Fixed an issue where video clips wouldn't render properly.

## [0.14.1] - 2025-08-29

### Fixed

- Fixed dependencies missing error

## [0.14.0] - 2025-08-27

### Added

- Support for Ubuntu/Debian

### Fixed

- Fixed the version number

## [0.13.1] - 2025-08-27

### Fixed

- Fixed Adobe Flash not working

## [0.13.0] - 2025-08-26

### Changes

- Adobe Flash Player (CleanFlash) is no longer required.

## [0.12.4] - 2025-08-25

### Fixed

- Fixed an issue where OBS recordings wouldn't save in the right location (causing unnecessary bloat)

## [0.12.3] - 2025-08-25

### Fixed

- Fixed an issue where OBS resolution wouldn't change
- Mouse is no longer repositioned off screen regardless of recording method (Because both methods don't capture the mouse)

## [0.12.2] - 2025-08-25

### Fixed

- Fixed OBS.md to contain correct flags

### Added

- Added memory (When you run GoExport, it will remember what you picked so that it can be quickly replicated.)
- Your OBS settings will also be saved to disk when you use an OBS related command line flag.
- Redid the splash screen to appear more modern and fancy.
- Added OBS flag that will prevent OBS from making changes to your settings (This does not mean it won't create a profile and switch to it, this is also an advance feature, and should only be used if you know what you're doing. You'd want to use it if you want to customize GoExport in OBS, but this is not recommended.)

### Changed

- Changed the way command line arguments are parsed to improve efficiency.
- Splash screen now tells you if GoExport is using OBS or not.

## [0.12.1] - 2025/08/24

### Fixed

- Prevent hanging of the webserver

## [0.12.0] - 2025-08-23

### Added

- Support for OBS Studio integration (See OBS.md for details)
- Comprehensive CHANGELOG.md file with structured release notes for all versions

### Changed

- Fixed GitHub workflow to include proper changelog in releases instead of auto-generated commit lists
- Modified workflow to extract relevant changelog sections for each tagged release
- Enhanced release notes with detailed feature descriptions, bug fixes, and dependency information

### Fixed

- Issue where automated releases only showed basic commit history links instead of detailed release notes

## [0.11.0] - 2025-08-22

### Added

- Implement legacy mode handling
- Enhanced server logging functionality

### Changed

- Improved overall system compatibility

## [0.10.1] - 2025-07-16

### Fixed

- Various bug fixes and stability improvements

## [0.10.0] - 2025-07-15

### Added

- New features and functionality improvements

### Changed

- Enhanced user experience and performance optimizations

## [0.9.0] - 2025-07-08

### Added

- Improved rendering quality for better video output
- New outro created by [Alex Director](https://www.youtube.com/@AlexDirector)

### Changed

- Replaced the old outro with Alex Director's rendition

### Removed

- Removed mentions of prior outro creator
- Removed old outro system

### Dependencies

- Adobe Flash Player (We recommend [CleanFlash](https://web.archive.org/web/20241221081401/https://cdn.cleanflash.org/CleanFlash_34.0.0.308_Installer.exe))
- Microsoft Visual C++ Redistributable [[x86]](https://aka.ms/vs/17/release/vc_redist.x86.exe) or [[x64]](https://aka.ms/vs/17/release/vc_redist.x64.exe)

## [0.7.1] - 2025-05-18

### Fixed

- Fixed version numbers

## [0.7.0] - 2025-05-16

### Added

- Automatic installation process using Inno Setup
- DLL files are now automatically registered upon installation

### Changed

- Setup process was removed (no longer needed to run GoExport as admin)
- Software now requires automatic installation before use

### Removed

- Manual setup process requirement

## [0.6.1] - 2025-05-10

### Changed

- Updated references of AidenAnimate2K25 to YoiAnimate

## [0.6.0] - 2025-05-10

### Added

- Output directory now created within application folder in "output" directory

### Changed

- Refactored codebase for better maintainability
- Output directory location moved to application folder

## [0.5.1] - 2025-04-08

### Added

- Aspect ratio selection
- Support for vertical aspect ratio (for Shorts or TikToks)
- Re-enabled outro videos for 4:3 and 16:9 aspect ratios

### Changed

- Revamped resolution selection
- Outro videos now work with all resolutions

### Fixed

- Fixed issue where video would freeze if it was too long
- Fixed outro glitch issues for certain resolutions

## [0.5.0] - 2025-03-30

### Changed

- Removed outro from auto editor (still accessible via manual editing)

### Fixed

- Fixed encoding issues that caused audio and import problems

## [0.4.2] - 2025-03-26

### Added

- FFMPEG output now appears in logs for better debugging

## [0.4.1] - 2025-03-24

### Added

- Specific checks for screen recording device and audio recording device

## [0.4.0] - 2025-03-22

### Added

- Built-in dependencies to mitigate screen capture issues
- Flash dependency check to ensure user has Flash installed
- More verbose logging with user inputs for better debugging
- Display of video location after completion

### Changed

- Data folder removed, temporary videos now go to temp folder
- App now unpacks dependencies on startup (may take longer to load)
- Logs are created after program starts
- App remains idle for 5 seconds for better user experience

### Removed

- ASCII art "Goodbye" message for better readability

## [0.3.1] - 2025-03-18

### Fixed

- Fixed issue involving enabling Adobe Flash Player

## [0.3.0] - 2025-03-18

### Added

- Version number and app name display
- Computer specifications logging for easier debugging
- Privacy disclaimer for logged specifications
- Better cleanup after completion

### Changed

- Readjusted auto editing for better usability
- Slowed down Chromium when enabling Flash for consistency
- Mouse moved off screen during recording (bottom right)

### Fixed

- Fixed out-of-sync issue on long videos

## [0.2.0] - 2025-03-14

### Added

- Initial release with core functionality

## [0.1.0] - 2025-03-13

### Added

- Initial project release
- Basic video export functionality for Wrapper Offline and FlashThemes

### Dependencies

- screen-capture-recorder-to-video-windows-free
- Adobe Flash Player

---

## Dependencies Information

### Current Dependencies

- Adobe Flash Player (We recommend [CleanFlash](https://web.archive.org/web/20241221081401/https://cdn.cleanflash.org/CleanFlash_34.0.0.308_Installer.exe))
- Microsoft Visual C++ Redistributable [[x86]](https://aka.ms/vs/17/release/vc_redist.x86.exe) or [[x64]](https://aka.ms/vs/17/release/vc_redist.x64.exe)

**Note:** Both x86 and x64 redistributables are not needed - choose based on your system architecture.

### Historical Dependencies

- screen-capture-recorder-to-video-windows-free (required for versions 0.4.2 and earlier)
