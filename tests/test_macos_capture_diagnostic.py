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


def _frame_details(frame):
    details = [_describe(frame)]
    for name in ("width", "height", "format", "timestamp"):
        try:
            details.append(f"{name}={getattr(frame, name)!r}")
        except Exception:
            details.append(f"{name}=<unreadable>")
    try:
        details.append(f"data.shape={frame.data.shape!r}")
        details.append(f"data.size={frame.data.size!r}")
    except Exception:
        details.append("data=<unreadable>")
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
            check_screen_resolution=False,
            check_frame_resolution=False,
        )
        capturer = None
        try:
            driver = self._stage("start Chromium", browser.create_driver)
            self._stage("load Wrapper URL", lambda: driver.get(config.URL))
            self._stage("enter fullscreen", lambda: browser.enter_fullscreen(driver))
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

            def enumerate_targets():
                window_title = driver.title
                print(f"[scap diagnostic] Selenium window title: {window_title!r}")
                all_targets = list(scap.targets())
                print(
                    f"[scap diagnostic] targets visible during browser lookup: "
                    f"{len(all_targets)}"
                )
                for index, item in enumerate(all_targets):
                    print(f"[scap diagnostic] lookup target[{index}]: {_describe(item)}")
                matching = [
                    item
                    for item in all_targets
                    if getattr(item, "kind", None) == "window"
                    and (
                        getattr(item, "title", None) == window_title
                        or getattr(item, "title", "").startswith(
                            f"{window_title} - "
                        )
                    )
                ]
                print(
                    "[scap diagnostic] title-matching window targets:",
                    len(matching),
                )
                return all_targets

            self._stage(
                "enumerate PyScap targets", enumerate_targets
            )
            target = self._stage(
                "select Chromium capture target",
                lambda: browser.get_capture_target(driver),
            )
            crop_area = self._stage(
                "calculate crop area",
                lambda: browser.get_capture_crop_area(driver),
            )
            print(f"[scap diagnostic] production target: {_describe(target)}")
            print(f"[scap diagnostic] production crop area: {crop_area!r}")
            if target is None:
                targets = list(self._stage("scap.targets()", scap.targets))
                print(f"[scap diagnostic] detected targets: {len(targets)}")
                for index, item in enumerate(targets):
                    print(f"[scap diagnostic] target[{index}]: {_describe(item)}")

            options = self._stage(
                "construct scap.CaptureOptions",
                lambda: scap.CaptureOptions(
                    fps=config.FPS,
                    target=target,
                    crop_area=crop_area,
                    show_cursor=False,
                    show_highlight=False,
                    output_type="bgra",
                    output_resolution="captured",
                    captures_audio=True,
                ),
            )
            print(
                "[scap diagnostic] requested options: "
                f"fps={config.FPS}, target={_describe(target)}, "
                f"crop_area={crop_area!r}, show_cursor=False, "
                "show_highlight=False, output_type='bgra', "
                "output_resolution='captured', captures_audio=True, "
                "exclude_current_process_audio=False",
                flush=True,
            )
            capturer = self._stage(
                "construct scap.Capturer / SCStream",
                lambda: scap.Capturer(options),
            )
            effective_size = self._stage(
                "read effective capture dimensions", capturer.output_size
            )
            print(
                "[scap diagnostic] effective capture dimensions: "
                f"{effective_size[0]}x{effective_size[1]}",
                flush=True,
            )
            self.assertGreater(effective_size[0], 0)
            self.assertGreater(effective_size[1], 0)
            self._stage("start SCStream", capturer.start)
            deadline = time.monotonic() + 5.0
            video_frame = None
            frame_count = 0
            while frame_count < 300 and time.monotonic() < deadline:
                frame_count += 1
                frame = self._stage(
                    f"read frame {frame_count}", capturer.next_frame
                )
                print(
                    f"[scap diagnostic] frame[{frame_count}]: "
                    f"{_frame_details(frame)}",
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
            self.assertGreater(video_frame.width, 0)
            self.assertGreater(video_frame.height, 0)
            self.assertGreater(video_frame.data.size, 0)
            self.assertEqual(video_frame.data.shape[0], video_frame.height)
            self.assertEqual(video_frame.data.shape[1], video_frame.width)
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
