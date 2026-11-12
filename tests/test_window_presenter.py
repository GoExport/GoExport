import sys
import unittest
from unittest.mock import Mock

from goexport.services.window_presenter import WindowPresenter, WindowState


class FakeNative:
    def __init__(self, handle=42, state=None):
        self.handle = handle
        self.initial = state or WindowState((0, 0, 1280, 720), False, False, False)
        self.alive = True
        self.calls = []

    def find_window(self, pids, title):
        self.calls.append(("find", pids, title))
        return self.handle

    def state(self, handle):
        return self.initial

    def present(self, handle, original):
        self.calls.append(("present", handle, original))

    def restore(self, handle, original):
        self.calls.append(("restore", handle, original))

    def exists(self, handle):
        return self.alive


class WindowPresenterTests(unittest.TestCase):
    def driver(self):
        driver = Mock(title="Just a moment...")
        driver.service.process.pid = None
        return driver

    def test_existing_window_is_raised_and_restored(self):
        minimized = WindowState((-32000, -32000, -31800, -31900), True, False, True)
        native = FakeNative(state=minimized)
        presenter = WindowPresenter(self.driver(), native=native)

        presenter.show()
        self.assertIsNone(presenter.poll())
        presenter.restore()

        self.assertEqual(
            [call[0] for call in native.calls], ["find", "present", "restore"]
        )
        self.assertIs(native.calls[2][2], minimized)
        self.assertIn("brought to the front", presenter.instructions)

    def test_restore_is_idempotent(self):
        native = FakeNative()
        presenter = WindowPresenter(self.driver(), native=native)
        presenter.show()
        presenter.restore()
        presenter.restore()
        self.assertEqual([c[0] for c in native.calls].count("restore"), 1)

    def test_closed_window_is_reported(self):
        native = FakeNative()
        presenter = WindowPresenter(self.driver(), native=native)
        presenter.show()
        native.alive = False
        self.assertEqual(presenter.poll(), "closed")
        presenter.restore()
        self.assertNotIn("restore", [c[0] for c in native.calls])

    def test_unidentified_window_still_allows_verification(self):
        native = FakeNative(handle=None)
        presenter = WindowPresenter(self.driver(), native=native)
        with self.assertLogs("goexport.services.window_presenter", "WARNING"):
            presenter.show()
        self.assertIsNone(presenter.poll())
        self.assertIn("taskbar", presenter.instructions)
        presenter.restore()

    def test_driver_is_never_used_to_resize_the_window(self):
        driver = self.driver()
        presenter = WindowPresenter(driver, native=FakeNative())
        presenter.show()
        presenter.restore()
        driver.set_window_rect.assert_not_called()
        driver.fullscreen_window.assert_not_called()
        driver.quit.assert_not_called()


@unittest.skipUnless(sys.platform == "win32", "Win32 window management")
class Win32WindowsTests(unittest.TestCase):
    def test_state_of_a_real_window_and_missing_handles(self):
        import ctypes

        from goexport.services.window_presenter import Win32Windows

        native = Win32Windows()
        console = ctypes.windll.kernel32.GetConsoleWindow()
        self.assertFalse(native.exists(0x7FFFFFF0))
        self.assertIsNone(native.find_window({0xFFFFFFF}, "nothing"))
        if console:
            state = native.state(console)
            self.assertEqual(len(state.rect), 4)


if __name__ == "__main__":
    unittest.main()
