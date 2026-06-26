#!/usr/bin/env python3
"""
Downloads the runtime dependencies required by GoExport.

Creates the following directory structure:

bin/
├── ffmpeg/
└── ungoogled-chromium/

Supported platforms:
- Windows
- Linux
- macOS
"""

from __future__ import annotations

import plistlib
import platform
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

from pathlib import Path

import httpx
import py7zr

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

console = Console()

# These URLs are intentionally pinned.
#
# GoExport targets the final Chromium release with PPAPI Flash support.
# Do not update these unless there is a compelling reason to do so.

DOWNLOADS = {
    "Windows": {
        "chromium":
            "https://github.com/tangalbert919/ungoogled-chromium-binaries/releases/download/87.0.4280.141-1/ungoogled-chromium_87.0.4280.141-1.1_windows-x64.zip",

        "ffmpeg":
            "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",

        "flash":
            "https://github.com/darktohka/clean-flash-builds/releases/download/v1.54/ChineseFlash-Patched-Win-34.0.0.376.7z",
    },

    "Linux": {
        "chromium":
            "https://github.com/LordTwix/ungoogled-chromium-binaries/releases/download/87.0.4280.141-1.1/ungoogled-chromium_87.0.4280.141-1.1_linux.tar.xz",

        "ffmpeg":
            "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz",

        "flash":
            "https://github.com/darktohka/clean-flash-builds/releases/download/v1.7/flash_player_patched_ppapi_linux.x86_64.tar.gz",
    },

    "Darwin": {
        "chromium":
            "https://github.com/kramred/ungoogled-chromium-macos/releases/download/87.0.4280.141-1.1/ungoogled-chromium_87.0.4280.141-1.1_macos.dmg",

        "ffmpeg":
            "https://evermeet.cx/ffmpeg/getrelease/zip",

        "flash":
            "https://github.com/darktohka/clean-flash-builds/releases/download/v1.53/ChineseFlash-PPAPI-PepperFlashPlayer.zip",
    },
}

ROOT_DIR = Path(__file__).resolve().parent.parent
BIN_DIR = ROOT_DIR / "bin"

SYSTEM = platform.system()

CHROMIUM_DIR = BIN_DIR / "ungoogled-chromium"
FFMPEG_DIR = BIN_DIR / "ffmpeg"

if SYSTEM not in DOWNLOADS:
    raise RuntimeError(f"Unsupported operating system: {SYSTEM}")

URLS = DOWNLOADS[SYSTEM]

def recreate_directory(path: Path) -> None:
    """Deletes and recreates a directory."""

    if path.exists():
        shutil.rmtree(path)

    path.mkdir(parents=True, exist_ok=True)

def find_file(parent: Path, filename: str) -> Path:
    """Recursively finds a file by name."""

    for path in parent.rglob(filename):
        if path.is_file():
            return path

    raise FileNotFoundError(
        f"Unable to find '{filename}' in '{parent}'"
    )

def download_file(url: str, destination: Path) -> None:
    """Downloads a file with a progress bar."""

    console.print(f"[cyan]Downloading[/cyan] {destination.name}")

    with httpx.stream(
        "GET",
        url,
        follow_redirects=True,
        timeout=None,
    ) as response:
        response.raise_for_status()

        total = int(response.headers.get("Content-Length", 0))

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:

            task = progress.add_task(
                destination.name,
                total=total,
            )

            with destination.open("wb") as file:
                for chunk in response.iter_bytes(1024 * 64):
                    file.write(chunk)
                    progress.update(
                        task,
                        advance=len(chunk),
                    )

    console.print("[green]✓ Download complete[/green]")

def extract_zip(
    archive: Path,
    destination: Path,
) -> None:
    console.print(f"[cyan]Extracting[/cyan] {archive.name}")

    with zipfile.ZipFile(archive) as zip_file:
        zip_file.extractall(destination)

def extract_7z(
    archive: Path,
    destination: Path,
) -> None:
    console.print(f"[cyan]Extracting[/cyan] {archive.name}")

    with py7zr.SevenZipFile(archive) as seven_zip:
        seven_zip.extractall(destination)

def extract_tar(
    archive: Path,
    destination: Path,
) -> None:
    console.print(f"[cyan]Extracting[/cyan] {archive.name}")

    with tarfile.open(archive) as tar:
        tar.extractall(destination)

def mount_dmg(dmg: Path) -> Path:
    """Mounts a macOS DMG and returns the mount point."""

    result = subprocess.run(
        [
            "hdiutil",
            "attach",
            str(dmg),
            "-plist",
            "-nobrowse",
        ],
        capture_output=True,
        check=True,
    )

    plist = plistlib.loads(result.stdout)

    for entity in plist.get("system-entities", []):
        mount_point = entity.get("mount-point")
        if mount_point:
            return Path(mount_point)

    raise RuntimeError(
        "Unable to determine DMG mount point."
    )

def unmount_dmg(
    mount_point: Path,
) -> None:
    subprocess.run(
        [
            "hdiutil",
            "detach",
            str(mount_point),
            "-quiet",
        ],
        check=True,
    )

def temporary_directory():
    return tempfile.TemporaryDirectory(
        prefix="goexport_",
    )

def install_chromium(temp_dir: Path) -> None:
    """Downloads and installs Chromium."""

    console.rule("[bold cyan]Chromium")

    url = URLS["chromium"]
    archive = temp_dir / Path(url).name

    download_file(url, archive)

    recreate_directory(CHROMIUM_DIR)

    if archive.suffix == ".zip":
        extract_zip(archive, temp_dir)

    elif archive.suffixes[-2:] == [".tar", ".xz"]:
        extract_tar(archive, temp_dir)

    elif archive.suffix == ".dmg":
        mount = mount_dmg(archive)

        try:
            app = next(mount.glob("*.app"))

            shutil.copytree(
                app,
                CHROMIUM_DIR / app.name,
                dirs_exist_ok=True,
            )

        finally:
            unmount_dmg(mount)

        console.print("[green]✓ Chromium installed[/green]")
        return

    else:
        raise RuntimeError(
            f"Unsupported Chromium archive: {archive.name}"
        )

    if SYSTEM == "Windows":
        chrome = find_file(temp_dir, "chrome.exe")

    elif SYSTEM == "Linux":
        chrome = find_file(temp_dir, "chrome")

    else:
        raise RuntimeError(
            f"Unsupported operating system: {SYSTEM}"
        )

    shutil.copytree(
        chrome.parent,
        CHROMIUM_DIR,
        dirs_exist_ok=True,
    )

    console.print("[green]✓ Chromium installed[/green]")

def install_ffmpeg(temp_dir: Path) -> None:
    """Downloads and installs FFmpeg."""

    console.rule("[bold cyan]FFmpeg")

    url = URLS["ffmpeg"]

    if url.endswith(".zip") or url.endswith("/zip"):
        archive = temp_dir / "ffmpeg.zip"
    else:
        archive = temp_dir / "ffmpeg.tar.xz"

    download_file(url, archive)

    recreate_directory(FFMPEG_DIR)

    if archive.suffix == ".zip":
        extract_zip(archive, temp_dir)
    else:
        extract_tar(archive, temp_dir)

    executable = (
        "ffmpeg.exe"
        if SYSTEM == "Windows"
        else "ffmpeg"
    )

    ffmpeg = find_file(temp_dir, executable)

    bin_dir = FFMPEG_DIR / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(ffmpeg, bin_dir / ffmpeg.name)

    console.print("[green]✓ FFmpeg installed[/green]")

def install_flash(temp_dir: Path) -> None:
    """Downloads and installs Pepper Flash."""

    console.rule("[bold cyan]Pepper Flash")

    url = URLS["flash"]
    archive = temp_dir / Path(url).name

    download_file(url, archive)

    extensions = CHROMIUM_DIR / "extensions"
    extensions.mkdir(
        parents=True,
        exist_ok=True,
    )

    if archive.suffix == ".7z":
        extract_7z(archive, temp_dir)

        plugin = next(
            temp_dir.rglob("pepflashplayer.dll")
        )

        shutil.copy2(
            plugin,
            extensions / plugin.name,
        )

    elif archive.suffixes[-2:] == [".tar", ".gz"]:
        extract_tar(archive, temp_dir)

        plugin = next(
            temp_dir.rglob("libpepflashplayer.so")
        )

        shutil.copy2(
            plugin,
            extensions / plugin.name,
        )

    elif archive.suffix == ".zip":
        extract_zip(archive, temp_dir)

        plugin = next(
            temp_dir.rglob("*.plugin")
        )

        shutil.copytree(
            plugin,
            extensions / plugin.name,
            dirs_exist_ok=True,
        )

    else:
        raise RuntimeError(
            f"Unsupported Flash archive: {archive.name}"
        )

    console.print("[green]✓ Pepper Flash installed[/green]")

def verify_installation() -> None:
    """Verifies that all required runtime files exist."""

    console.rule("[bold cyan]Verifying Installation")

    if SYSTEM == "Windows":
        required = [
            CHROMIUM_DIR / "chrome.exe",
            CHROMIUM_DIR / "chromedriver.exe",
            CHROMIUM_DIR / "extensions" / "pepflashplayer.dll",
            FFMPEG_DIR / "bin" / "ffmpeg.exe",
        ]

    elif SYSTEM == "Linux":
        required = [
            CHROMIUM_DIR / "chrome",
            CHROMIUM_DIR / "chromedriver",
            CHROMIUM_DIR / "extensions" / "libpepflashplayer.so",
            FFMPEG_DIR / "bin" / "ffmpeg",
        ]

    elif SYSTEM == "Darwin":
        required = [
            CHROMIUM_DIR / "Chromium.app",
            CHROMIUM_DIR / "chromedriver",
            CHROMIUM_DIR / "extensions" / "PepperFlashPlayer.plugin",
            FFMPEG_DIR / "bin" / "ffmpeg",
        ]

    missing = [
        path
        for path in required
        if not path.exists()
    ]

    if missing:
        console.print("[red]Installation failed.[/red]\n")

        for path in missing:
            console.print(f"[red]Missing:[/red] {path}")

        raise SystemExit(1)

    console.print("[green]✓ Installation verified[/green]")

def main() -> int:
    console.rule("[bold green]GoExport Dependency Installer")

    with temporary_directory() as temp:
        temp_dir = Path(temp)

        install_chromium(temp_dir)
        install_ffmpeg(temp_dir)
        install_flash(temp_dir)

    verify_installation()

    console.print()
    console.print(
        "[bold green]All dependencies installed successfully![/bold green]"
    )

    return 0

if __name__ == "__main__":
    raise SystemExit(main())