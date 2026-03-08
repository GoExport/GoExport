#!/usr/bin/env python3
"""
Tests for the expanded Compatibility class (startup diagnostics and dependency verification).
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import helpers
from modules.compatibility import Compatibility


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_temp_file(size: int = 1024) -> str:
    """Create a temporary non-empty file and return its path."""
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, "wb") as f:
        f.write(b"x" * size)
    return path


def _make_empty_temp_file() -> str:
    """Create a temporary zero-byte file and return its path."""
    fd, path = tempfile.mkstemp()
    os.close(fd)
    return path


# ---------------------------------------------------------------------------
# _check_file_integrity
# ---------------------------------------------------------------------------

def test_file_integrity_ok():
    """A non-empty file should pass integrity check."""
    path = _make_temp_file(512)
    try:
        compat = Compatibility()
        result = compat._check_file_integrity(path)
        assert result is True, "Non-empty file should pass integrity check"
        print("✓ test_file_integrity_ok passed")
        return True
    except AssertionError as e:
        print(f"✗ test_file_integrity_ok failed: {e}")
        return False
    finally:
        os.unlink(path)


def test_file_integrity_empty():
    """An empty (zero-byte) file should fail integrity check."""
    path = _make_empty_temp_file()
    try:
        compat = Compatibility()
        result = compat._check_file_integrity(path)
        assert result is False, "Empty file should fail integrity check"
        print("✓ test_file_integrity_empty passed")
        return True
    except AssertionError as e:
        print(f"✗ test_file_integrity_empty failed: {e}")
        return False
    finally:
        os.unlink(path)


def test_file_integrity_missing():
    """A non-existent path should fail integrity check."""
    compat = Compatibility()
    result = compat._check_file_integrity("/nonexistent/path/file.exe")
    try:
        assert result is False, "Missing file should fail integrity check"
        print("✓ test_file_integrity_missing passed")
        return True
    except AssertionError as e:
        print(f"✗ test_file_integrity_missing failed: {e}")
        return False


# ---------------------------------------------------------------------------
# generate_diagnostic_report
# ---------------------------------------------------------------------------

def test_generate_diagnostic_report_structure():
    """Diagnostic report should contain expected sections."""
    compat = Compatibility()
    compat.issues = ["Test issue 1", "Test issue 2"]

    with tempfile.TemporaryDirectory() as tmpdir:
        # Patch app folder so the report is written to a temp dir
        original_get_app_folder = helpers.get_app_folder
        helpers.get_app_folder = lambda: tmpdir

        try:
            report_path = compat.generate_diagnostic_report()

            assert report_path is not None, "generate_diagnostic_report() should return a path"
            assert os.path.exists(report_path), f"Report file should exist at {report_path}"

            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()

            app_name = helpers.get_config("APP_NAME")
            assert app_name in content, "Report should contain app name"
            assert "System Information" in content, "Report should contain system information section"
            assert "Issues Found" in content, "Report should contain issues section"
            assert "Test issue 1" in content, "Report should list first issue"
            assert "Test issue 2" in content, "Report should list second issue"
            assert "Support" in content, "Report should contain support section"
            assert "discord.gg" in content, "Report should include support Discord link"

            print("✓ test_generate_diagnostic_report_structure passed")
            return True
        except AssertionError as e:
            print(f"✗ test_generate_diagnostic_report_structure failed: {e}")
            return False
        finally:
            helpers.get_app_folder = original_get_app_folder


def test_generate_diagnostic_report_no_issues():
    """Diagnostic report with no issues should say 'none'."""
    compat = Compatibility()
    compat.issues = []

    with tempfile.TemporaryDirectory() as tmpdir:
        original_get_app_folder = helpers.get_app_folder
        helpers.get_app_folder = lambda: tmpdir

        try:
            report_path = compat.generate_diagnostic_report()
            assert report_path is not None

            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()

            assert "(none)" in content, "Report should say '(none)' when no issues are found"
            print("✓ test_generate_diagnostic_report_no_issues passed")
            return True
        except AssertionError as e:
            print(f"✗ test_generate_diagnostic_report_no_issues failed: {e}")
            return False
        finally:
            helpers.get_app_folder = original_get_app_folder


# ---------------------------------------------------------------------------
# issues list management
# ---------------------------------------------------------------------------

def test_issues_reset_between_tests():
    """Each call to test() should reset the issues list before running checks."""
    import config
    original = config.SKIP_COMPAT

    compat = Compatibility()
    # Simulate a stale issue from a previous run
    compat.issues = ["stale issue from previous run"]

    # Call test() with SKIP_COMPAT so it returns immediately without side-effects
    config.SKIP_COMPAT = True
    try:
        compat.test()
        # With SKIP_COMPAT the method returns early BEFORE resetting, so issues remain.
        # The real reset happens at the top of test() before checks run.
        # Verify by running without SKIP_COMPAT using patched deps that pass instantly:
        config.SKIP_COMPAT = False
        compat.issues = ["stale issue from previous run"]

        # Temporarily make test() skip all real checks by enabling SKIP_COMPAT in mid-flight
        # We test the reset logic directly: the very first statement in test() after the
        # SKIP_COMPAT guard is `self.issues = []`.
        # Patch the _log_system_info to raise so we can see issues was already reset.
        original_log = compat._log_system_info
        def _patched_log():
            assert compat.issues == [], "issues list must be reset before _log_system_info runs"
            raise StopIteration("sentinel")
        compat._log_system_info = _patched_log

        try:
            config.SKIP_COMPAT = False
            compat.test()
        except StopIteration as e:
            assert str(e) == "sentinel", "Expected sentinel StopIteration"

        compat._log_system_info = original_log
        print("✓ test_issues_reset_between_tests passed")
        return True
    except AssertionError as e:
        print(f"✗ test_issues_reset_between_tests failed: {e}")
        return False
    finally:
        config.SKIP_COMPAT = original


# ---------------------------------------------------------------------------
# skip compatibility flag
# ---------------------------------------------------------------------------

def test_skip_compat():
    """When SKIP_COMPAT is True the test should return True immediately."""
    import config
    original = config.SKIP_COMPAT
    config.SKIP_COMPAT = True

    try:
        compat = Compatibility()
        result = compat.test()
        assert result is True, "test() should return True when SKIP_COMPAT is set"
        print("✓ test_skip_compat passed")
        return True
    except AssertionError as e:
        print(f"✗ test_skip_compat failed: {e}")
        return False
    finally:
        config.SKIP_COMPAT = original


# ---------------------------------------------------------------------------
# Windows-specific checks (skipped on Linux)
# ---------------------------------------------------------------------------

def test_check_vcredist_returns_bool():
    """_check_vcredist should return a boolean on any platform."""
    compat = Compatibility()
    result = compat._check_vcredist()
    try:
        assert isinstance(result, bool), "_check_vcredist() must return bool"
        print("✓ test_check_vcredist_returns_bool passed")
        return True
    except AssertionError as e:
        print(f"✗ test_check_vcredist_returns_bool failed: {e}")
        return False


def test_install_vcredist_missing_file():
    """_install_vcredist should return False when the installer file is absent."""
    import config
    original = config.PATH_VCREDIST_WINDOWS
    config.PATH_VCREDIST_WINDOWS = ["nonexistent_redist", "vcredist_x64.exe"]

    try:
        compat = Compatibility()
        result = compat._install_vcredist()
        assert result is False, "_install_vcredist() should return False when installer is missing"
        print("✓ test_install_vcredist_missing_file passed")
        return True
    except AssertionError as e:
        print(f"✗ test_install_vcredist_missing_file failed: {e}")
        return False
    finally:
        config.PATH_VCREDIST_WINDOWS = original


def test_install_directshow_missing_dlls():
    """_install_directshow_drivers should return False when DLL files are missing."""
    import config
    original_screen = config.PATH_LIBS_SCREEN_CAPTURE_WINDOWS
    original_audio = config.PATH_LIBS_AUDIO_SNIFFER_WINDOWS
    config.PATH_LIBS_SCREEN_CAPTURE_WINDOWS = ["nonexistent_libs", "screen-capture-recorder-x64.dll"]
    config.PATH_LIBS_AUDIO_SNIFFER_WINDOWS = ["nonexistent_libs", "audio_sniffer-x64.dll"]

    try:
        compat = Compatibility()
        result = compat._install_directshow_drivers()
        assert result is False, "_install_directshow_drivers() should return False when DLLs are missing"
        print("✓ test_install_directshow_missing_dlls passed")
        return True
    except AssertionError as e:
        print(f"✗ test_install_directshow_missing_dlls failed: {e}")
        return False
    finally:
        config.PATH_LIBS_SCREEN_CAPTURE_WINDOWS = original_screen
        config.PATH_LIBS_AUDIO_SNIFFER_WINDOWS = original_audio


def test_check_directshow_missing_dlls():
    """_check_directshow_drivers should return False when DLL files are missing."""
    import config
    original_screen = config.PATH_LIBS_SCREEN_CAPTURE_WINDOWS
    original_audio = config.PATH_LIBS_AUDIO_SNIFFER_WINDOWS
    config.PATH_LIBS_SCREEN_CAPTURE_WINDOWS = ["nonexistent_libs", "screen-capture-recorder-x64.dll"]
    config.PATH_LIBS_AUDIO_SNIFFER_WINDOWS = ["nonexistent_libs", "audio_sniffer-x64.dll"]

    try:
        compat = Compatibility()
        result = compat._check_directshow_drivers()
        assert result is False, "_check_directshow_drivers() should return False when DLLs are missing"
        print("✓ test_check_directshow_missing_dlls passed")
        return True
    except AssertionError as e:
        print(f"✗ test_check_directshow_missing_dlls failed: {e}")
        return False
    finally:
        config.PATH_LIBS_SCREEN_CAPTURE_WINDOWS = original_screen
        config.PATH_LIBS_AUDIO_SNIFFER_WINDOWS = original_audio


# ---------------------------------------------------------------------------
# Flash plugin check
# ---------------------------------------------------------------------------

def test_check_flash_plugin_missing():
    """_check_flash_plugin should return False and record an issue when plugin is absent."""
    import config
    if helpers.os_is_windows():
        original = config.PATH_FLASH_WINDOWS
        config.PATH_FLASH_WINDOWS = ["nonexistent_deps", "pepflashplayer.dll"]
    else:
        original = config.PATH_FLASH_LINUX
        config.PATH_FLASH_LINUX = ["nonexistent_deps", "libpepflashplayer.so"]

    try:
        compat = Compatibility()
        result = compat._check_flash_plugin()
        assert result is False, "_check_flash_plugin() should return False when plugin is missing"
        assert len(compat.issues) > 0, "An issue should be recorded when the flash plugin is missing"
        print("✓ test_check_flash_plugin_missing passed")
        return True
    except AssertionError as e:
        print(f"✗ test_check_flash_plugin_missing failed: {e}")
        return False
    finally:
        if helpers.os_is_windows():
            config.PATH_FLASH_WINDOWS = original
        else:
            config.PATH_FLASH_LINUX = original


def test_check_flash_plugin_present():
    """_check_flash_plugin should return True for a valid non-empty plugin file."""
    plugin_path = _make_temp_file(1024)
    import config
    if helpers.os_is_windows():
        original = config.PATH_FLASH_WINDOWS
        config.PATH_FLASH_WINDOWS = [plugin_path]
    else:
        original = config.PATH_FLASH_LINUX
        config.PATH_FLASH_LINUX = [plugin_path]

    # Patch get_path so the single-element list resolves to the temp file
    original_get_path = helpers.get_path
    helpers.get_path = lambda base, *parts: plugin_path

    try:
        compat = Compatibility()
        result = compat._check_flash_plugin()
        assert result is True, "_check_flash_plugin() should return True for a valid plugin file"
        print("✓ test_check_flash_plugin_present passed")
        return True
    except AssertionError as e:
        print(f"✗ test_check_flash_plugin_present failed: {e}")
        return False
    finally:
        os.unlink(plugin_path)
        helpers.get_path = original_get_path
        if helpers.os_is_windows():
            config.PATH_FLASH_WINDOWS = original
        else:
            config.PATH_FLASH_LINUX = original


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running compatibility tests...")
    print("-" * 60)

    tests = [
        test_file_integrity_ok,
        test_file_integrity_empty,
        test_file_integrity_missing,
        test_generate_diagnostic_report_structure,
        test_generate_diagnostic_report_no_issues,
        test_issues_reset_between_tests,
        test_skip_compat,
        test_check_vcredist_returns_bool,
        test_install_vcredist_missing_file,
        test_install_directshow_missing_dlls,
        test_check_directshow_missing_dlls,
        test_check_flash_plugin_missing,
        test_check_flash_plugin_present,
    ]

    passed = sum(1 for t in tests if t())
    total = len(tests)

    print("-" * 60)
    if passed == total:
        print(f"✓ All {total} tests passed!")
        sys.exit(0)
    else:
        print(f"✗ {total - passed}/{total} tests failed")
        sys.exit(1)
