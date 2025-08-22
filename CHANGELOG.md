# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Fixed GitHub workflow to include proper changelog in releases instead of auto-generated commit lists

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