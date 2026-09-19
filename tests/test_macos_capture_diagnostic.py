"""Opt-in diagnostic for the real macOS PyScap backend.

This intentionally does not mock ``scap``.  Run it on macOS from the Python
environment containing lexian-pyscap to diagnose native capture failures.
"""

from __future__ import annotations

import importlib.metadata
import platform
import subprocess
import sys
import sysconfig
import traceback
import unittest

from goexport import config


def _describe(value):
    """Return useful, non-invasive identifying information for a PyScap target."""
    details = [f"type={type(value).__name__}", f"repr={value!r}"]
    for name in ("id", "title", "name", "kind", "width", "height", "x", "y"):
        try:
            if hasattr(value, name):
                details.append(f"{name}={getattr(value, name)!r}")
        except Exception:
            details.append(f"{name}=<unreadable>")
    return ", ".join(details)


@unittest.skipUnless(sys.platform == "darwin", "real PyScap diagnostic requires macOS")
class MacOSRealScapDiagnostic(unittest.TestCase):
    def _stage(self, name, operation):
        print(f"\n[scap diagnostic] stage: {name}", flush=True)
        try:
            return operation()
        except BaseException:
            print(f"[scap diagnostic] FAILED at stage: {name}", flush=True)
            traceback.print_exc()
            raise

    def test_real_macos_capture_backend(self):
        python_machine = platform.machine()
        machine = python_machine
        try:
            machine = subprocess.run(
                ["sysctl", "-in", "hw.machine"],
                check=False,
                capture_output=True,
                text=True,
            ).stdout.strip() or machine
        except OSError:
            pass
        rosetta = "unknown"
        if machine == "arm64" or python_machine == "x86_64":
            try:
                rosetta = subprocess.run(
                    ["sysctl", "-in", "sysctl.proc_translated"],
                    check=False,
                    capture_output=True,
                    text=True,
                ).stdout.strip() == "1"
            except OSError:
                rosetta = "unavailable"
        print("[scap diagnostic] macOS version:", platform.mac_ver()[0])
        print("[scap diagnostic] machine architecture:", machine)
        print(
            "[scap diagnostic] Python architecture:",
            f"{python_machine} ({sysconfig.get_platform()})",
        )
        print("[scap diagnostic] running under Rosetta 2:", rosetta)
        print("[scap diagnostic] Python version:", sys.version.replace("\n", " "))
        for distribution in ("lexian-pyscap", "pyscap", "scap"):
            try:
                print(
                    f"[scap diagnostic] {distribution} version:",
                    importlib.metadata.version(distribution),
                )
            except importlib.metadata.PackageNotFoundError:
                pass

        scap = self._stage("import real scap module", lambda: __import__("scap"))
        targets = self._stage("scap.targets()", scap.targets)
        targets = list(targets)
        print(f"[scap diagnostic] detected targets: {len(targets)}")
        for index, target in enumerate(targets):
            print(f"[scap diagnostic] target[{index}]: {_describe(target)}")
        if not targets:
            raise RuntimeError("scap.targets() returned no capture targets")

        capturer = None
        try:
            options = scap.CaptureOptions(
                fps=config.FPS,
                target=targets[0],
                crop_area=None,
                show_cursor=False,
                show_highlight=False,
                output_type="bgra",
                output_resolution="captured",
                captures_audio=True,
            )
            capturer = self._stage(
                "construct scap.Capturer", lambda: scap.Capturer(options)
            )
            self._stage("start capture", capturer.start)
            frames = []
            for index in range(3):
                frame = self._stage(f"read frame {index + 1}", capturer.next_frame)
                print(f"[scap diagnostic] frame[{index}]: {_describe(frame)}")
                frames.append(frame)
            video_frames = [
                frame for frame in frames if isinstance(frame, scap.VideoFrameInfo)
            ]
            if not video_frames:
                raise RuntimeError(
                    "capture returned no valid scap.VideoFrameInfo frame"
                )
            print("[scap diagnostic] valid video frame received: yes")
        finally:
            if capturer is not None:
                for method_name in ("stop", "release", "close"):
                    method = getattr(capturer, method_name, None)
                    if method is not None:
                        try:
                            print(f"[scap diagnostic] cleanup: {method_name}()")
                            method()
                        except BaseException:
                            traceback.print_exc()


if __name__ == "__main__":
    unittest.main(verbosity=2)
