"""Authoritative definitions for GoExport-managed runtime dependencies."""

from __future__ import annotations

from pathlib import Path

from goexport import config
from goexport.dependencies.installers import (
    install_chromedriver,
    install_chromium,
    install_ffmpeg,
    install_flash,
)
from goexport.dependencies.models import Dependency

DOWNLOADS = {
    "Windows": {
        "chromium": "https://github.com/tangalbert919/ungoogled-chromium-binaries/releases/download/87.0.4280.141-1/ungoogled-chromium_87.0.4280.141-1.1_windows-x64.zip",
        "chromedriver": "https://chromedriver.storage.googleapis.com/87.0.4280.88/chromedriver_win32.zip",
        "ffmpeg": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
        "flash": "https://github.com/GoExport/goexport-flash-player/releases/latest/download/pepflashplayer.zip",
    },
    "Linux": {
        "chromium": "https://github.com/LordTwix/ungoogled-chromium-binaries/releases/download/87.0.4280.141-1.1/ungoogled-chromium_87.0.4280.141-1.1_linux.tar.xz",
        "ffmpeg": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz",
        "flash": "https://github.com/GoExport/goexport-flash-player/releases/latest/download/libpepflashplayer.zip",
    },
    "Darwin": {
        "chromium": "https://github.com/kramred/ungoogled-chromium-macos/releases/download/87.0.4280.141-1.1/ungoogled-chromium_87.0.4280.141-1.1_macos.dmg",
        "chromedriver": "https://chromedriver.storage.googleapis.com/87.0.4280.88/chromedriver_mac64.zip",
        "ffmpeg": "https://evermeet.cx/ffmpeg/getrelease/zip",
        "flash": "https://github.com/GoExport/goexport-flash-player/releases/latest/download/PepperFlashPlayer.plugin.zip",
    },
}


def dependency_registry(
    system: str = config.SYSTEM,
    chromium_dir: Path = config.CHROMIUM_DIR,
    ffmpeg_dir: Path = config.FFMPEG_DIR,
) -> dict[str, Dependency]:
    if system not in DOWNLOADS:
        raise RuntimeError(f"Unsupported operating system: {system}")
    urls = DOWNLOADS[system]
    if system == "Windows":
        chrome = chromium_dir / "chrome.exe"
        chromium_support = (chromium_dir / "chrome.dll", chromium_dir / "icudtl.dat")
        driver = chromium_dir / "chromedriver.exe"
        flash = chromium_dir / "extensions" / "pepflashplayer.dll"
        ffmpeg = ffmpeg_dir / "bin" / "ffmpeg.exe"
    elif system == "Linux":
        chrome = chromium_dir / "chrome"
        chromium_support = (
            chromium_dir / "icudtl.dat",
            chromium_dir / "resources.pak",
        )
        driver = chromium_dir / "chromedriver"
        flash = chromium_dir / "extensions" / "libpepflashplayer.so"
        ffmpeg = ffmpeg_dir / "bin" / "ffmpeg"
    else:
        chrome = chromium_dir / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
        chromium_support = (
            chromium_dir / "Chromium.app" / "Contents" / "Info.plist",
            chromium_dir / "Chromium.app" / "Contents" / "Frameworks",
        )
        driver = chromium_dir / "chromedriver"
        flash = chromium_dir / "extensions" / "PepperFlashPlayer.plugin"
        ffmpeg = ffmpeg_dir / "bin" / "ffmpeg"

    return {
        "chromium": Dependency(
            id="chromium",
            name="Chromium",
            required_paths=(chrome, *chromium_support),
            install=install_chromium,
            runtime_argument="chrome_path",
            runtime_path=chrome,
            invalidates=("chromedriver", "pepper_flash"),
            metadata={
                "url": urls["chromium"],
                "system": system,
                "destination": str(chromium_dir),
            },
        ),
        "chromedriver": Dependency(
            id="chromedriver",
            name="ChromeDriver",
            required_paths=(driver,),
            install=install_chromedriver,
            runtime_argument="chromedriver_path",
            runtime_path=driver,
            install_after=("chromium",),
            repair_with="chromium" if system == "Linux" else None,
            metadata={"url": urls.get("chromedriver", ""), "system": system},
        ),
        "pepper_flash": Dependency(
            id="pepper_flash",
            name="Pepper Flash",
            required_paths=(flash,),
            install=install_flash,
            runtime_argument="flash_plugin_path",
            runtime_path=flash,
            install_after=("chromium",),
            metadata={"url": urls["flash"], "system": system},
        ),
        "ffmpeg": Dependency(
            id="ffmpeg",
            name="FFmpeg",
            required_paths=(ffmpeg,),
            install=install_ffmpeg,
            runtime_argument="ffmpeg_path",
            runtime_path=ffmpeg,
            metadata={"url": urls["ffmpeg"], "system": system},
        ),
    }
