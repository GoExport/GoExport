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
import time
import traceback
import unittest

from goexport import config
from goexport.services.browser import BrowserService
from goexport.services.capture import create_capturer


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
        browser = BrowserService(
            config.CHROME_PATH,
            config.CHROMEDRIVER_PATH,
            config.FLASH_PLUGIN_PATH,
            config.FLASH_PLUGIN_VERSION,
            config.WIDTH,
            config.HEIGHT,
        )
        capturer = None
        try:
            driver = self._stage("start Chromium", browser.create_driver)
            self._stage("load Wrapper URL", lambda: driver.get(config.URL))
            self._stage("enter fullscreen", lambda: browser.enter_fullscreen(driver))
            self._stage(
                "validate screen resolution",
                lambda: browser.validate_screen_resolution(driver),
            )
            self._stage("validate browser viewport", browser.assert_full_resolution)
            self._stage("enable Flash", lambda: browser.enable_flash(driver))
            self._stage(
                "load GoExport template",
                lambda: browser.inject_dom(
                    driver,
                    config.TEMPLATE_HTML_PATH,
                    {
                        "WINDOW_TITLE": "GoExport macOS Capture Diagnostic",
                        "PLAYER_WIDTH": config.WIDTH,
                        "PLAYER_HEIGHT": config.HEIGHT,
                        "PLAYER_SWF_URL": config.SWF_URL,
                        "IS_WIDE": int(config.IS_WIDE),
                        "API_SERVER": config.API_URL,
                        "STORE_PATH": config.STORE_PATH,
                        "CLIENT_THEME_PATH": config.CLIENT_THEME_PATH,
                        "MOVIE_ID": "capture-diagnostic",
                        "USER_ID": "capture-diagnostic",
                    },
                ),
            )
            if not self._stage("check scap support", scap.is_supported):
                raise RuntimeError("scap reports that this platform is unsupported")
            if not self._stage("check Screen Recording permission", scap.has_permission):
                permitted = self._stage(
                    "request Screen Recording permission", scap.request_permission
                )
                if not permitted:
                    raise PermissionError("Screen Recording permission was denied")

            target = self._stage(
                "find GoExport browser capture target",
                lambda: browser.get_capture_target(driver),
            )
            crop_area = self._stage(
                "calculate production capture crop",
                lambda: browser.get_capture_crop_area(driver),
            )
            print(f"[scap diagnostic] production target: {_describe(target)}")
            print(f"[scap diagnostic] production crop area: {crop_area!r}")
            if target is None:
                targets = list(self._stage("scap.targets()", scap.targets))
                print(f"[scap diagnostic] detected targets: {len(targets)}")
                for index, item in enumerate(targets):
                    print(f"[scap diagnostic] target[{index}]: {_describe(item)}")

            capturer = self._stage(
                "construct production scap.Capturer",
                lambda: create_capturer(target, crop_area, browser.capture_display),
            )
            self._stage("start capture", capturer.start)
            deadline = time.monotonic() + 5.0
            video_frame = None
            frame_count = 0
            while frame_count < 300 and time.monotonic() < deadline:
                frame_count += 1
                frame = self._stage(
                    f"read frame {frame_count}", capturer.next_frame
                )
                print(
                    f"[scap diagnostic] frame[{frame_count}]: {_describe(frame)}",
                    flush=True,
                )
                if isinstance(frame, scap.VideoFrameInfo):
                    video_frame = frame
                    break
            if video_frame is None:
                raise RuntimeError(
                    "capture started successfully, but no "
                    "scap.VideoFrameInfo was received within 5 seconds "
                    f"({frame_count} frames read)"
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
            try:
                print("[scap diagnostic] cleanup: close Chromium")
                browser.close()
            except BaseException:
                traceback.print_exc()


if __name__ == "__main__":
    unittest.main(verbosity=2)
