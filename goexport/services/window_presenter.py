"""Show the existing Selenium Chromium window for manual verification.

Used on Windows, and on Linux when Chromium runs on the user's own display
(for example with the OBS backend). The window belongs to the running
WebDriver session; it is only restored, moved on-screen and raised, and its
original minimized state, position and z-order are restored afterwards. Its
size is never changed, so capture regions computed later remain valid.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CHROMIUM_WINDOW_CLASS = "Chrome_WidgetWin_1"


def session_pids(driver) -> set[int] | None:
    """PIDs of this Selenium session (chromedriver and its descendants)."""
    process = getattr(getattr(driver, "service", None), "process", None)
    pid = getattr(process, "pid", None)
    if not isinstance(pid, int):
        return None
    import psutil

    try:
        root = psutil.Process(pid)
        return {pid, *(child.pid for child in root.children(recursive=True))}
    except psutil.Error:
        logger.debug("Could not inspect chromedriver process %s", pid)
        return None


@dataclass(frozen=True)
class WindowState:
    rect: tuple[int, int, int, int]
    minimized: bool
    topmost: bool
    offscreen: bool


class WindowPresenter:
    presentation = "window"

    def __init__(self, driver, native=None):
        self.driver = driver
        self.native = native
        if self.native is None and sys.platform == "win32":
            self.native = Win32Windows()
        self.handle: int | None = None
        self.original: WindowState | None = None
        self.instructions = "Complete the check in the Chromium window."

    def show(self) -> None:
        if self.native is None:
            logger.info("Complete the Cloudflare check in the Chromium window.")
            return
        pids = session_pids(self.driver)
        self.handle = self.native.find_window(pids, self._page_title())
        if self.handle is None:
            logger.warning(
                "Could not identify the Chromium window to bring it forward; "
                "switch to it from the taskbar."
            )
            self.instructions = (
                "Switch to GoExport's Chromium window from the taskbar and "
                "complete the check."
            )
            return
        self.original = self.native.state(self.handle)
        self.native.present(self.handle, self.original)
        self.instructions = (
            "Complete the check in the Chromium window GoExport brought to the front."
        )

    def poll(self) -> str | None:
        if (
            self.native is not None
            and self.handle is not None
            and not self.native.exists(self.handle)
        ):
            return "closed"
        return None

    def restore(self) -> None:
        if self.native is None or self.handle is None or self.original is None:
            return
        try:
            if self.native.exists(self.handle):
                self.native.restore(self.handle, self.original)
        except OSError:
            logger.warning("Could not restore the Chromium window.", exc_info=True)
        finally:
            self.original = None

    def _page_title(self) -> str:
        try:
            return str(self.driver.title or "")
        except Exception:
            return ""


class Win32Windows:
    """Minimal user32 window management through ctypes."""

    SW_RESTORE = 9
    SW_SHOWMINNOACTIVE = 7
    GW_OWNER = 4
    GWL_EXSTYLE = -20
    WS_EX_TOPMOST = 0x00000008
    MONITOR_DEFAULTTONULL = 0
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040
    FLASHW_ALL = 0x3
    FLASHW_TIMERNOFG = 0xC

    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("Win32 window management requires Windows.")
        import ctypes
        from ctypes import wintypes

        self._ctypes = ctypes
        self._wintypes = wintypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._enum_proc = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )
        signatures = {
            "EnumWindows": (wintypes.BOOL, [self._enum_proc, wintypes.LPARAM]),
            "GetWindowThreadProcessId": (
                wintypes.DWORD,
                [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)],
            ),
            "IsWindow": (wintypes.BOOL, [wintypes.HWND]),
            "IsWindowVisible": (wintypes.BOOL, [wintypes.HWND]),
            "IsIconic": (wintypes.BOOL, [wintypes.HWND]),
            "GetWindow": (wintypes.HWND, [wintypes.HWND, wintypes.UINT]),
            "GetClassNameW": (
                ctypes.c_int,
                [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int],
            ),
            "GetWindowTextW": (
                ctypes.c_int,
                [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int],
            ),
            "GetWindowRect": (
                wintypes.BOOL,
                [wintypes.HWND, ctypes.POINTER(wintypes.RECT)],
            ),
            "GetWindowLongW": (wintypes.LONG, [wintypes.HWND, ctypes.c_int]),
            "MonitorFromWindow": (wintypes.HMONITOR, [wintypes.HWND, wintypes.DWORD]),
            "ShowWindow": (wintypes.BOOL, [wintypes.HWND, ctypes.c_int]),
            "SetWindowPos": (
                wintypes.BOOL,
                [
                    wintypes.HWND,
                    wintypes.HWND,
                    ctypes.c_int,
                    ctypes.c_int,
                    ctypes.c_int,
                    ctypes.c_int,
                    wintypes.UINT,
                ],
            ),
            "SetForegroundWindow": (wintypes.BOOL, [wintypes.HWND]),
            "FlashWindowEx": (wintypes.BOOL, [ctypes.c_void_p]),
        }
        for name, (restype, argtypes) in signatures.items():
            function = getattr(user32, name)
            function.restype = restype
            function.argtypes = argtypes
        self.user32 = user32

    def find_window(self, pids: set[int] | None, page_title: str) -> int | None:
        """The visible top-level Chromium window owned by this session."""
        ctypes, wintypes = self._ctypes, self._wintypes
        user32 = self.user32
        candidates: list[tuple[int, str]] = []

        def visit(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd) or user32.GetWindow(
                hwnd, self.GW_OWNER
            ):
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pids is not None and pid.value not in pids:
                return True
            class_name = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_name, 256)
            if class_name.value != CHROMIUM_WINDOW_CLASS:
                return True
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title, 512)
            if title.value:
                candidates.append((int(hwnd), title.value))
            return True

        user32.EnumWindows(self._enum_proc(visit), 0)
        if pids is None:
            # Without the session's PIDs only an exact page title is trusted.
            candidates = [c for c in candidates if page_title and page_title in c[1]]
        for handle, title in candidates:
            if page_title and title.startswith(page_title):
                return handle
        return candidates[0][0] if candidates else None

    def exists(self, handle: int) -> bool:
        return bool(self.user32.IsWindow(handle))

    def state(self, handle: int) -> WindowState:
        rect = self._wintypes.RECT()
        if not self.user32.GetWindowRect(handle, self._ctypes.byref(rect)):
            raise self._ctypes.WinError(self._ctypes.get_last_error())
        exstyle = self.user32.GetWindowLongW(handle, self.GWL_EXSTYLE)
        return WindowState(
            rect=(rect.left, rect.top, rect.right, rect.bottom),
            minimized=bool(self.user32.IsIconic(handle)),
            topmost=bool(exstyle & self.WS_EX_TOPMOST),
            offscreen=not self.user32.MonitorFromWindow(
                handle, self.MONITOR_DEFAULTTONULL
            ),
        )

    def present(self, handle: int, original: WindowState) -> None:
        user32 = self.user32
        if original.minimized:
            user32.ShowWindow(handle, self.SW_RESTORE)
        if original.offscreen:
            user32.SetWindowPos(
                handle,
                None,
                0,
                0,
                0,
                0,
                self.SWP_NOSIZE | self.SWP_NOZORDER | self.SWP_SHOWWINDOW,
            )
        flags = self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_SHOWWINDOW
        if not original.topmost:
            # Raising through the topmost band is allowed for background
            # processes, unlike SetForegroundWindow, and is undone at once.
            user32.SetWindowPos(handle, self.HWND_TOPMOST, 0, 0, 0, 0, flags)
            user32.SetWindowPos(handle, self.HWND_NOTOPMOST, 0, 0, 0, 0, flags)
        if not user32.SetForegroundWindow(handle):
            self._flash(handle)

    def restore(self, handle: int, original: WindowState) -> None:
        if original.offscreen:
            left, top, _right, _bottom = original.rect
            self.user32.SetWindowPos(
                handle,
                None,
                left,
                top,
                0,
                0,
                self.SWP_NOSIZE | self.SWP_NOZORDER | self.SWP_NOACTIVATE,
            )
        if original.minimized:
            self.user32.ShowWindow(handle, self.SW_SHOWMINNOACTIVE)

    def _flash(self, handle: int) -> None:
        import ctypes
        from ctypes import wintypes

        class FLASHWINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.UINT),
                ("hwnd", wintypes.HWND),
                ("dwFlags", wintypes.DWORD),
                ("uCount", wintypes.UINT),
                ("dwTimeout", wintypes.DWORD),
            ]

        info = FLASHWINFO(
            ctypes.sizeof(FLASHWINFO),
            handle,
            self.FLASHW_ALL | self.FLASHW_TIMERNOFG,
            0,
            0,
        )
        self.user32.FlashWindowEx(ctypes.byref(info))
