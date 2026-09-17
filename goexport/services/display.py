"""Linux X display ownership for browser and screen-capture sessions."""

from __future__ import annotations

import os

from pyvirtualdisplay import Display

from goexport import config


class LinuxDisplay:
    """Own the Xvfb display selected for one GoExport browser session.

    PyVirtualDisplay chooses the display number.  Keeping that value here makes
    the display used by Chromium and the X11 capture backend explicit instead
    of relying on whichever DISPLAY happened to be inherited by the process.
    """

    def __init__(self, size: tuple[int, int], color_depth: int = 24):
        self.size = size
        self.color_depth = color_depth
        self._display: Display | None = None
        self.inherited_display = os.environ.get("DISPLAY")
        self.display: str | None = None

    @property
    def active(self) -> bool:
        return self._display is not None

    @property
    def capture_display(self) -> str | None:
        """The display to use for this session's Chromium and X11 capture."""
        return self.display if self.active else os.environ.get("DISPLAY")

    def start(self) -> str:
        if config.SYSTEM != "Linux":
            raise RuntimeError(
                "A Linux virtual display was requested on a non-Linux system."
            )

        display = Display(visible=False, size=self.size, color_depth=self.color_depth)
        display.start()
        self._display = display
        self.display = display.new_display_var
        # Do this explicitly as well as through PyVirtualDisplay so every
        # in-process consumer (including native PyScap initialization) has the
        # display owned by this session as its source of truth.
        os.environ["DISPLAY"] = self.display
        return self.display

    def stop(self) -> None:
        if self._display is not None:
            self._display.stop()
            self._display = None
            self.display = None
