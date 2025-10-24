<p align="center">
  <img src="assets/logo.svg" alt="Logo">
</p>

Welcome to GoExport, with this tool, you can export your videos for Wrapper Offline.

![Static Badge](https://img.shields.io/badge/status-development-orange?cacheBuster=true)
![GitHub Repo stars](https://img.shields.io/github/stars/GoExport/GoExport?cacheBuster=true)
[![.github/workflows/release_and_build.yml](https://github.com/GoExport/GoExport/actions/workflows/release_and_build.yml/badge.svg)](https://github.com/GoExport/GoExport/actions/workflows/release_and_build.yml)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/5f3d2b64b62c4d129c8d0c3ba2e8c5cd)](https://app.codacy.com/gh/GoExport/GoExport/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/GoExport/GoExport/total?cacheBuster=true)
![GitHub License](https://img.shields.io/github/license/GoExport/GoExport?cacheBuster=true)
![GitHub Release](https://img.shields.io/github/v/release/GoExport/GoExport?include_prereleases&cacheBuster=true)
[![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/ejwJYtQDrS)

# ✅ Supported

The following is a list of **known supported LVMs**:

- Wrapper: Offline
- FlashThemes

# 📜 License

This project is licensed under the **GNU General Public License v3.0**. For more details, refer to the [LICENSE](LICENSE) file.

# 👤 Credits

- Project created and maintained by [**Lexian-droid**](https://github.com/Lexian-droid).
- Outro created by [**Alex Director**](https://www.youtube.com/@AlexDirector)

# ❓ Support and FAQ

<details>
  <summary><strong>What LVM is supported?</strong></summary>

The following is a list of **known supported LVMs**:

- Wrapper: Offline (aka "Local")
- FlashThemes (aka "FT")

</details>

<details>
  <summary><strong>My video is laggy!</strong></summary>

Assuming you have a decent computer, this is simply an issue with Flash and is normal and not related to GoExport. The original GoAnimate exporter was also laggy.

</details>

<details>
  <summary><strong>How do I use GoExport?</strong></summary>

Simply watch the [**official video tutorial**](https://youtu.be/Cen69Mp5T4E) on how to use GoExport. It will guide you through the process of exporting your videos.

</details>

<details>
  <summary><strong>How do I get my Video ID or User ID?</strong></summary>

Simply watch the [**guide video**](https://youtu.be/YpbHqPGz4co) on how to get your Video ID or User ID. It will guide you through the process of finding your IDs or user ids.

</details>

<details>
  <summary><strong>GUI won't load on Linux (XOrg/X11)</strong></summary>

If the GUI works on Wayland but not on XOrg/X11 (common on Linux Mint and VMware), you're missing Qt platform plugins. See the [Linux GUI Troubleshooting Guide](docs/LINUX_GUI_TROUBLESHOOTING.md) for the solution.

**Quick fix for Ubuntu/Debian/Mint:**

```bash
sudo apt-get install libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxkbcommon-x11-0 libxcb-cursor0
```

</details>

If you have any questions or still need support, feel free to reach out to us on our [Discord server](https://discord.gg/ejwJYtQDrS).

# 📂 Installation

In order to **install GoExport** you'll need to go to the [latest release](https://github.com/GoExport/GoExport/releases/latest) and download the one that relates to your computer.

You may need to also install the dependencies, which can be found in the [Dependencies](https://github.com/GoExport/GoExport?tab=readme-ov-file#%EF%B8%8F-dependencies) section. (**Only "Not Included" dependencies need to be manually installed**)

## ⚠️ Dependencies

The project may require that you have installed some dependencies to get started, this is required for GoExport to function properly.

- [cleanflash](https://web.archive.org/web/20241221081401/https://cdn.cleanflash.org/CleanFlash_34.0.0.308_Installer.exe): CleanFlash 34 on the internet archive. (**Included in ungoogled-chromium**)
- [OBS](https://obsproject.com/): Open Broadcaster Software. (**Not Included, Optional but recommended**) (See [OBS.md](OBS.md))
- [screen-capture-recorder-to-video-windows-free](https://github.com/rdp/screen-capture-recorder-to-video-windows-free/releases/latest): This will capture the display. (**Included**)
- [virtual-audio-capture-grabber-device](https://github.com/rdp/virtual-audio-capture-grabber-device): This will capture the audio. (**Included**)
- [Microsoft Visual C++ Redistributable (x64)](https://www.microsoft.com/en-us/download/details.aspx?id=26999): Required for audio capture. (**Included**).
  > This project uses the Microsoft Visual C++ Redistributable, which is licensed under the Microsoft Software License Terms. The redistributable is included in the project and is required for audio capture functionality.
- [FFMPEG (GPLv3)](https://github.com/BtbN/FFmpeg-Builds): To record the screen (**Included**)
  > This project uses FFmpeg, which can be licensed under the LGPLv2.1, LGPLv3, or GPL. Make sure to check the license before using it. The FFmpeg binaries are included in the project and are licensed under the GPLv3.
- [ungoogled chromium (v87)](https://ungoogled-software.github.io/ungoogled-chromium-binaries/releases/windows/64bit/87.0.4280.141-1): To play the content (**Included**)
  > This project uses ungoogled-chromium, which is licensed under the BSD, MIT, and LGPL licenses. The source code for ungoogled-chromium is available at [ungoogled-chromium GitHub repository](https://github.com/ungoogled-software/ungoogled-chromium).
- [Chromedriver (Apache License 2.0)](https://chromedriver.chromium.org/downloads): To interface with ungoogled-chromium (**Included**).
  > This project uses Chromedriver, which is licensed under the Apache License 2.0.
