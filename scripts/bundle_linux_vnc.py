#!/usr/bin/env python3
"""Bundle x11vnc and TigerVNC's viewer for the portable Linux release.

Run on the Linux build runner after installing the ``x11vnc`` and
``tigervnc-viewer`` packages. The result is ``bin/vnc``::

    bin/vnc/x11vnc
    bin/vnc/vncviewer
    bin/vnc/lib/            private shared libraries (LD_LIBRARY_PATH at runtime)
    bin/vnc/LICENSES/       Debian copyright files of every bundled package
    bin/vnc/SOURCES.txt     exact source packages and versions (GPL/LGPL)

Libraries that are part of every desktop Linux system, or that must match the
host (glibc, the X11 client and font libraries, GPU drivers), are not bundled;
the list follows the AppImage project's excludelist.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

LDD_LINE = re.compile(r"^\s*(?P<name>\S+)\s+=>\s+(?P<path>/\S+)\s+\(0x[0-9a-f]+\)")

EXCLUDED_LIBRARIES = {
    # glibc and the toolchain runtime that must come from the host.
    "ld-linux-x86-64.so.2",
    "libanl.so.1",
    "libBrokenLocale.so.1",
    "libc.so.6",
    "libdl.so.2",
    "libgcc_s.so.1",
    "libm.so.6",
    "libmvec.so.1",
    "libnsl.so.1",
    "libpthread.so.0",
    "libresolv.so.2",
    "librt.so.1",
    "libthread_db.so.1",
    "libutil.so.1",
    # Display, GPU, font and audio libraries tied to the host system.
    "libasound.so.2",
    "libdrm.so.2",
    "libEGL.so.1",
    "libexpat.so.1",
    "libfontconfig.so.1",
    "libfreetype.so.6",
    "libgbm.so.1",
    "libGL.so.1",
    "libglapi.so.0",
    "libGLdispatch.so.0",
    "libGLX.so.0",
    "libharfbuzz.so.0",
    "libICE.so.6",
    "libOpenGL.so.0",
    "libSM.so.6",
    "libX11-xcb.so.1",
    "libX11.so.6",
    "libxcb.so.1",
    # Libraries whose configuration lives on the host.
    "libcom_err.so.2",
    "libgpg-error.so.0",
    "libp11-kit.so.0",
    "libuuid.so.1",
    "libz.so.1",
}

TOOLS = {
    "x11vnc": ("x11vnc",),
    "vncviewer": ("xtigervncviewer", "vncviewer"),
}


def parse_ldd(output: str) -> dict[str, Path]:
    """Map each resolved shared library name to its path."""
    libraries = {}
    for line in output.splitlines():
        match = LDD_LINE.match(line)
        if match:
            libraries[match.group("name")] = Path(match.group("path"))
    return libraries


def should_bundle(name: str) -> bool:
    return name not in EXCLUDED_LIBRARIES and not name.startswith("libnss_")


def find_tool(names: tuple[str, ...]) -> Path:
    for name in names:
        if found := shutil.which(name):
            return Path(found).resolve()
    raise SystemExit(f"Could not find {' or '.join(names)}; install it first.")


def ldd(path: Path, library_dir: Path | None = None) -> str:
    env = dict(os.environ)
    if library_dir is not None:
        env["LD_LIBRARY_PATH"] = str(library_dir)
    result = subprocess.run(
        ["ldd", str(path)], capture_output=True, text=True, check=True, env=env
    )
    return result.stdout


def owning_package(path: Path) -> str:
    candidates = [path, path.resolve()]
    for candidate in tuple(candidates):
        text = str(candidate)
        if text.startswith("/usr/lib/"):
            candidates.append(Path(text[len("/usr") :]))
        elif text.startswith("/lib/"):
            candidates.append(Path("/usr" + text))
    for candidate in candidates:
        result = subprocess.run(
            ["dpkg", "-S", str(candidate)], capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.split(":", 1)[0].strip()
    raise SystemExit(f"Could not determine which package installed {path}.")


def package_details(package: str) -> tuple[str, str]:
    result = subprocess.run(
        ["dpkg-query", "-W", "-f=${source:Package}\t${Version}", package],
        capture_output=True,
        text=True,
        check=True,
    )
    source, version = result.stdout.split("\t")
    return source, version


def bundle(output: Path, collect_licenses: bool = True) -> None:
    if output.exists():
        shutil.rmtree(output)
    library_dir = output / "lib"
    library_dir.mkdir(parents=True)

    origins: list[Path] = []
    bundled_names: set[str] = set()
    for target, names in TOOLS.items():
        source = find_tool(names)
        shutil.copy2(source, output / target)
        (output / target).chmod(0o755)
        origins.append(source)
        for name, path in parse_ldd(ldd(source)).items():
            if should_bundle(name) and name not in bundled_names:
                shutil.copy2(path.resolve(), library_dir / name)
                bundled_names.add(name)
                origins.append(path)
        print(f"Bundled {target} from {source}")

    for target in TOOLS:
        unresolved = [
            line.strip()
            for line in ldd(output / target, library_dir).splitlines()
            if "not found" in line
        ]
        if unresolved:
            raise SystemExit(f"{target} has unresolved libraries: {unresolved}")
    print(f"Bundled {len(bundled_names)} private libraries:")
    for name in sorted(bundled_names):
        print(f"  {name}")
    size = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
    print(f"Bundle size: {size / 1_000_000:.1f} MB")

    if collect_licenses:
        write_licenses(output, origins)


def write_licenses(output: Path, origins: list[Path]) -> None:
    licenses = output / "LICENSES"
    licenses.mkdir()
    packages = sorted({owning_package(path) for path in origins})
    lines = [
        "GoExport bundles these unmodified Ubuntu binary packages in bin/vnc.",
        "Their complete corresponding source code is published with each",
        "GoExport Linux release (GoExport-linux-vnc-sources.tar.gz) and is",
        "available from the Ubuntu archive with: apt-get source <source>=<version>",
        "",
    ]
    sources = set()
    for package in packages:
        source, version = package_details(package)
        sources.add(f"{source}={version}")
        lines.append(f"{package}\t{version}\tsource: {source}")
        copyright_file = Path("/usr/share/doc") / package / "copyright"
        if not copyright_file.is_file():
            raise SystemExit(f"Missing copyright file for {package}")
        shutil.copy2(copyright_file, licenses / f"{package}.copyright")
    (output / "SOURCES.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "source-packages.txt").write_text(
        "\n".join(sorted(sources)) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    if sys.platform != "linux":
        raise SystemExit("VNC tools are only bundled for Linux releases.")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=ROOT_DIR / "bin" / "vnc")
    parser.add_argument(
        "--skip-licenses",
        action="store_true",
        help="Do not collect package licenses (local testing only).",
    )
    args = parser.parse_args(argv)
    bundle(args.output, collect_licenses=not args.skip_licenses)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
