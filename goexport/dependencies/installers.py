"""Download and atomic installation helpers for managed runtime components."""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import tarfile
import uuid
import zipfile
from pathlib import Path

import httpx

from goexport.dependencies.models import Dependency, InstallContext


def download_file(url: str, destination: Path, context: InstallContext) -> None:
    context.progress(f"Downloading {destination.name}")
    with httpx.stream("GET", url, follow_redirects=True, timeout=None) as response:
        response.raise_for_status()
        with destination.open("wb") as output:
            for chunk in response.iter_bytes(1024 * 64):
                output.write(chunk)


def extract_archive(archive: Path, destination: Path) -> None:
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as source:
            source.extractall(destination)
    elif archive.suffixes[-2:] == [".tar", ".xz"]:
        with tarfile.open(archive) as source:
            source.extractall(destination, filter="data")
    else:
        raise RuntimeError(f"Unsupported archive: {archive.name}")


def find_file(parent: Path, filename: str) -> Path:
    for path in parent.rglob(filename):
        if path.is_file():
            return path
    raise FileNotFoundError(f"Unable to find '{filename}' in '{parent}'.")


def make_executable(path: Path) -> None:
    if os.name != "nt":
        path.chmod(path.stat().st_mode | 0o111)


def install_chromium(dependency: Dependency, context: InstallContext) -> None:
    url = dependency.metadata["url"]
    archive = context.work_dir / _archive_name(url, "chromium")
    download_file(url, archive, context)
    prepared = context.work_dir / "prepared-chromium"
    system = dependency.metadata["system"]

    if archive.suffix == ".dmg":
        prepared.mkdir()
        mount = _mount_dmg(archive)
        try:
            app = next(mount.glob("*.app"), None)
            if app is None:
                raise FileNotFoundError(
                    "Chromium application was not found in the DMG."
                )
            shutil.copytree(app, prepared / app.name)
        finally:
            _unmount_dmg(mount)
    else:
        extracted = context.work_dir / "chromium-extracted"
        extracted.mkdir()
        extract_archive(archive, extracted)
        executable = "chrome.exe" if system == "Windows" else "chrome"
        chrome = find_file(extracted, executable)
        shutil.copytree(chrome.parent, prepared)

    destination = Path(dependency.metadata["destination"])
    _verify_prepared(dependency, prepared, destination)
    _replace_directory(prepared, destination)


def install_chromedriver(dependency: Dependency, context: InstallContext) -> None:
    if dependency.metadata["system"] == "Linux":
        path = dependency.runtime_path
        if not path.is_file():
            raise RuntimeError("Bundled ChromeDriver was not restored with Chromium.")
        make_executable(path)
        return

    archive = context.work_dir / "chromedriver.zip"
    download_file(dependency.metadata["url"], archive, context)
    extracted = context.work_dir / "chromedriver-extracted"
    extracted.mkdir()
    extract_archive(archive, extracted)
    source = find_file(extracted, dependency.runtime_path.name)
    _replace_file(source, dependency.runtime_path)
    make_executable(dependency.runtime_path)


def install_ffmpeg(dependency: Dependency, context: InstallContext) -> None:
    url = dependency.metadata["url"]
    archive = context.work_dir / _archive_name(url, "ffmpeg")
    download_file(url, archive, context)
    extracted = context.work_dir / "ffmpeg-extracted"
    extracted.mkdir()
    extract_archive(archive, extracted)
    source = find_file(extracted, dependency.runtime_path.name)
    prepared = context.work_dir / "prepared-ffmpeg"
    (prepared / "bin").mkdir(parents=True)
    shutil.copy2(source, prepared / "bin" / source.name)
    make_executable(prepared / "bin" / source.name)
    _verify_prepared(dependency, prepared, dependency.runtime_path.parents[1])
    _replace_directory(prepared, dependency.runtime_path.parents[1])


def install_flash(dependency: Dependency, context: InstallContext) -> None:
    archive = context.work_dir / "pepper-flash.zip"
    download_file(dependency.metadata["url"], archive, context)
    extracted = context.work_dir / "flash-extracted"
    extracted.mkdir()
    extract_archive(archive, extracted)
    name = dependency.runtime_path.name
    source = next(extracted.rglob(name), None)
    if source is None:
        raise FileNotFoundError(f"Unable to find '{name}' in the Flash archive.")
    if source.is_dir():
        _replace_directory(source, dependency.runtime_path)
    else:
        _replace_file(source, dependency.runtime_path)


def _archive_name(url: str, stem: str) -> str:
    if url.endswith("/zip"):
        return stem + ".zip"
    name = Path(url).name
    return name if Path(name).suffix else stem + ".zip"


def _verify_prepared(dependency: Dependency, prepared: Path, destination: Path) -> None:
    for required in dependency.required_paths:
        relative = required.relative_to(destination)
        candidate = prepared / relative
        if not candidate.exists() or (
            candidate.is_file() and not candidate.stat().st_size
        ):
            raise RuntimeError(
                f"Downloaded {dependency.name} is incomplete: missing {relative}."
            )


def _replace_file(source: Path, destination: Path) -> None:
    if not source.is_file() or not source.stat().st_size:
        raise RuntimeError(f"Refusing to install an empty file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    pending = destination.with_name(destination.name + f".pending-{uuid.uuid4().hex}")
    shutil.copy2(source, pending)
    pending.replace(destination)


def _replace_directory(source: Path, destination: Path) -> None:
    if not source.is_dir() or not any(source.iterdir()):
        raise RuntimeError(f"Refusing to install an empty directory: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    pending = destination.with_name(destination.name + f".pending-{uuid.uuid4().hex}")
    backup = destination.with_name(destination.name + f".backup-{uuid.uuid4().hex}")
    shutil.move(str(source), str(pending))
    replaced = False
    try:
        if destination.exists():
            destination.replace(backup)
            replaced = True
        pending.replace(destination)
    except BaseException:
        if replaced and backup.exists() and not destination.exists():
            backup.replace(destination)
        raise
    finally:
        if pending.exists():
            shutil.rmtree(pending)
        if backup.exists():
            shutil.rmtree(backup)


def _mount_dmg(dmg: Path) -> Path:
    result = subprocess.run(
        ["hdiutil", "attach", str(dmg), "-plist", "-nobrowse"],
        capture_output=True,
        check=True,
    )
    plist = plistlib.loads(result.stdout)
    for entity in plist.get("system-entities", []):
        if mount_point := entity.get("mount-point"):
            return Path(mount_point)
    raise RuntimeError("Unable to determine DMG mount point.")


def _unmount_dmg(mount_point: Path) -> None:
    subprocess.run(["hdiutil", "detach", str(mount_point), "-quiet"], check=True)
