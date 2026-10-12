# -*- mode: python ; coding: utf-8 -*-
import sys

from PyInstaller.utils.hooks import collect_submodules

# CaptureKit is pure Python + ctypes against OS libraries (no bundled
# binaries). It selects its platform backend with function-level imports, so
# collect this platform's backend modules explicitly. FFmpeg is GoExport's own
# bin/ffmpeg, passed to CaptureKit at runtime.
_other_backend = (
    'capturekit._backends.linux'
    if sys.platform == 'win32'
    else 'capturekit._backends.windows'
)
capturekit_modules = collect_submodules(
    'capturekit', filter=lambda name: not name.startswith(_other_backend)
)


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('version.txt', '.')],
    hiddenimports=[*capturekit_modules, 'numpy', 'psutil'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='GoExport',
    icon='resources/default.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
