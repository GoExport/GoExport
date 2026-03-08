from __future__ import annotations

import os
import subprocess
from datetime import datetime
import helpers
from modules.logger import logger

class Compatibility:
    def __init__(self):
        self.issues = []

    def test(self) -> bool:
        """Run full compatibility check. Returns True if all checks pass."""
        if helpers.get_config("SKIP_COMPAT"):
            return True

        self.issues = []

        # Create "output" folder
        helpers.make_dir(helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_FOLDER_OUTPUT_FILENAME")))

        # Log system information
        self._log_system_info()

        # Unsupported OS check
        if not helpers.os_is_windows() and not helpers.os_is_linux():
            self.issues.append("Unsupported operating system. GoExport requires Windows or Linux.")
            return False

        all_passed = True

        # Check required binary dependencies (FFmpeg, Chromium, Chromedriver)
        if not self._check_binary_dependencies():
            all_passed = False

        # Check Flash plugin
        if not self._check_flash_plugin():
            all_passed = False

        # Windows-specific checks
        if helpers.os_is_windows():
            # VC++ Redistributable
            if not self._check_vcredist():
                logger.warning("VC++ Redistributable not detected, attempting automatic installation...")
                if self._install_vcredist():
                    logger.info("VC++ Redistributable installed successfully")
                else:
                    self.issues.append(
                        "VC++ Redistributable (x64) is not installed and automatic installation failed. "
                        "Please install it manually from the 'redist' folder or download it from Microsoft's website."
                    )
                    all_passed = False

            # DirectShow drivers (skip when OBS is required since native capture won't be used)
            if not helpers.get_param("obs_required"):
                if not self._check_directshow_drivers():
                    logger.warning("DirectShow drivers not detected, attempting automatic registration...")
                    if self._install_directshow_drivers():
                        logger.info("DirectShow drivers registered, re-verifying...")
                        if not self._check_directshow_drivers():
                            self.issues.append(
                                "DirectShow drivers were registered but devices are still not visible. "
                                "Please restart your computer or run GoExport as Administrator."
                            )
                            all_passed = False
                    else:
                        self.issues.append(
                            "DirectShow drivers (screen-capture-recorder, audio-sniffer) could not be registered. "
                            "Please run GoExport as Administrator, or use OBS Studio as the capture method instead."
                        )
                        all_passed = False

        return all_passed

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def _log_system_info(self):
        """Log application and system information."""
        logger.info(f"{helpers.get_config('APP_NAME')} v{helpers.get_config('APP_VERSION')}")

        if helpers.os_is_windows():
            logger.info("OS: Windows")
        elif helpers.os_is_linux():
            logger.info("OS: Linux")
        else:
            logger.error("OS: Unsupported")

        logger.info(f"Architecture: {helpers.get_arch()}")

        system_info = helpers.get_computer_specs()
        logger.info("System Information:")
        logger.info(f"  OS: {system_info['os']} {system_info['os_version']}")
        logger.info(f"  CPU: {system_info['cpu']}")
        logger.info(f"  Cores: {system_info['cores']}")
        logger.info(f"  Threads: {system_info['threads']}")
        logger.info(f"  RAM: {system_info['ram']} GB")
        logger.info(f"  Disk: {system_info['disk']} GB")
        logger.info(f"Executable: {helpers.is_frozen()}")

    # ------------------------------------------------------------------
    # Dependency checks
    # ------------------------------------------------------------------

    def _check_binary_dependencies(self) -> bool:
        """Check that FFmpeg, Chromium, and Chromedriver exist and are non-empty."""
        if helpers.os_is_windows():
            paths = {
                "FFmpeg":      helpers.get_config("PATH_FFMPEG_WINDOWS"),
                "FFprobe":     helpers.get_config("PATH_FFPROBE_WINDOWS"),
                "FFplay":      helpers.get_config("PATH_FFPLAY_WINDOWS"),
                "Chromium":    helpers.get_config("PATH_CHROMIUM_WINDOWS"),
                "Chromedriver": helpers.get_config("PATH_CHROMEDRIVER_WINDOWS"),
            }
        elif helpers.os_is_linux():
            paths = {
                "FFmpeg":      helpers.get_config("PATH_FFMPEG_LINUX"),
                "FFprobe":     helpers.get_config("PATH_FFPROBE_LINUX"),
                "FFplay":      helpers.get_config("PATH_FFPLAY_LINUX"),
                "Chromium":    helpers.get_config("PATH_CHROMIUM_LINUX"),
                "Chromedriver": helpers.get_config("PATH_CHROMEDRIVER_LINUX"),
            }
        else:
            logger.error("Unsupported OS")
            return False

        all_ok = True
        for name, path_config in paths.items():
            full_path = helpers.get_path(helpers.get_app_folder(), path_config)
            if not helpers.try_path(full_path):
                logger.error(f"Dependency check failed: {name} not found at {full_path}")
                self.issues.append(f"{name} not found at: {full_path}")
                all_ok = False
            elif not self._check_file_integrity(full_path):
                logger.error(f"Dependency check failed: {name} appears to be empty or corrupt at {full_path}")
                self.issues.append(f"{name} appears to be empty or corrupt at: {full_path}")
                all_ok = False
            else:
                logger.info(f"Dependency OK: {name}")

        return all_ok

    def _check_flash_plugin(self) -> bool:
        """Check that the PepperFlash plugin exists and has a non-zero size."""
        if helpers.os_is_windows():
            flash_path = helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_FLASH_WINDOWS"))
        elif helpers.os_is_linux():
            flash_path = helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_FLASH_LINUX"))
        else:
            return True

        if not helpers.try_path(flash_path):
            logger.error(f"Flash plugin not found at {flash_path}")
            logger.error("Please ensure the Flash plugin (PepperFlash) is present in the dependencies directory.")
            self.issues.append(
                f"Flash plugin not found at: {flash_path}. "
                "Please re-download GoExport or manually place the Flash plugin in the correct location."
            )
            return False

        if not self._check_file_integrity(flash_path):
            logger.error(f"Flash plugin appears to be empty or corrupt at {flash_path}")
            self.issues.append(
                f"Flash plugin appears to be empty or corrupt at: {flash_path}. "
                "Please re-download GoExport."
            )
            return False

        logger.info(f"Flash plugin OK: {flash_path}")
        return True

    # ------------------------------------------------------------------
    # Windows: VC++ Redistributable
    # ------------------------------------------------------------------

    def _check_vcredist(self) -> bool:
        """Check if VC++ Redistributable 2015-2022 (x64) is installed (Windows only)."""
        try:
            import winreg
        except ImportError:
            return True  # Not Windows

        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"),
        ]

        for hive, key_path in registry_keys:
            try:
                key = winreg.OpenKey(hive, key_path)
                installed, _ = winreg.QueryValueEx(key, "Installed")
                winreg.CloseKey(key)
                if installed:
                    logger.info("VC++ Redistributable (x64) is installed")
                    return True
            except (FileNotFoundError, OSError):
                continue

        logger.warning("VC++ Redistributable (x64) is not installed")
        return False

    def _install_vcredist(self) -> bool:
        """Attempt to install VC++ Redistributable silently (Windows only)."""
        vcredist_path = helpers.get_path(
            helpers.get_app_folder(),
            helpers.get_config("PATH_VCREDIST_WINDOWS")
        )

        if not helpers.try_path(vcredist_path):
            logger.error(f"VC++ Redistributable installer not found at {vcredist_path}")
            return False

        logger.info(f"Running VC++ Redistributable installer: {vcredist_path}")
        try:
            result = subprocess.run(
                [vcredist_path, "/install", "/quiet", "/norestart"],
                timeout=120,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if helpers.os_is_windows() else 0
            )
            # 0 = success, 3010 = success but restart required
            if result.returncode in (0, 3010):
                logger.info("VC++ Redistributable installed successfully (a restart may be required)")
                return True
            else:
                logger.error(f"VC++ Redistributable installation failed with exit code {result.returncode}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("VC++ Redistributable installation timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to run VC++ Redistributable installer: {e}")
            return False

    # ------------------------------------------------------------------
    # Windows: DirectShow drivers
    # ------------------------------------------------------------------

    def _check_directshow_drivers(self) -> bool:
        """Check if the DirectShow capture drivers are registered and visible to FFmpeg (Windows only)."""
        screen_capture_dll = helpers.get_path(
            helpers.get_app_folder(),
            helpers.get_config("PATH_LIBS_SCREEN_CAPTURE_WINDOWS")
        )
        audio_sniffer_dll = helpers.get_path(
            helpers.get_app_folder(),
            helpers.get_config("PATH_LIBS_AUDIO_SNIFFER_WINDOWS")
        )

        # Check DLL files exist
        if not helpers.try_path(screen_capture_dll):
            logger.error(f"screen-capture-recorder DLL not found: {screen_capture_dll}")
            return False

        if not helpers.try_path(audio_sniffer_dll):
            logger.error(f"audio-sniffer DLL not found: {audio_sniffer_dll}")
            return False

        # Check that the DLLs can be loaded (also validates that VC++ runtime is present)
        if not helpers.is_dll_loadable(screen_capture_dll):
            logger.warning(f"screen-capture-recorder DLL cannot be loaded: {screen_capture_dll}")
            return False

        if not helpers.is_dll_loadable(audio_sniffer_dll):
            logger.warning(f"audio-sniffer DLL cannot be loaded: {audio_sniffer_dll}")
            return False

        # Use FFmpeg to verify that the devices appear in the DirectShow device list
        ffmpeg_path = helpers.get_path(
            helpers.get_app_folder(),
            helpers.get_config("PATH_FFMPEG_WINDOWS")
        )

        if not helpers.try_path(ffmpeg_path):
            logger.warning("FFmpeg not found, skipping DirectShow device list verification")
            return True

        try:
            result = subprocess.run(
                [ffmpeg_path, "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if helpers.os_is_windows() else 0
            )
            # FFmpeg exits non-zero for this command; device list is in stderr
            output = (result.stdout + result.stderr).lower()

            screen_found = "screen-capture-recorder" in output
            audio_found = "virtual-audio-capturer" in output

            if screen_found and audio_found:
                logger.info("DirectShow drivers OK: screen-capture-recorder and virtual-audio-capturer are registered")
            else:
                if not screen_found:
                    logger.warning("screen-capture-recorder not found in DirectShow device list")
                if not audio_found:
                    logger.warning("virtual-audio-capturer not found in DirectShow device list")

            return screen_found and audio_found

        except subprocess.TimeoutExpired:
            logger.warning("DirectShow device check timed out")
            return False
        except Exception as e:
            logger.warning(f"Could not verify DirectShow devices via FFmpeg: {e}")
            return True  # Assume OK if the verification itself fails unexpectedly

    def _install_directshow_drivers(self) -> bool:
        """Register DirectShow DLLs using regsvr32 (Windows only)."""
        screen_capture_dll = helpers.get_path(
            helpers.get_app_folder(),
            helpers.get_config("PATH_LIBS_SCREEN_CAPTURE_WINDOWS")
        )
        audio_sniffer_dll = helpers.get_path(
            helpers.get_app_folder(),
            helpers.get_config("PATH_LIBS_AUDIO_SNIFFER_WINDOWS")
        )

        all_ok = True
        for name, dll_path in [
            ("screen-capture-recorder", screen_capture_dll),
            ("audio-sniffer", audio_sniffer_dll),
        ]:
            if not helpers.try_path(dll_path):
                logger.error(f"Cannot register {name}: file not found at {dll_path}")
                all_ok = False
                continue

            logger.info(f"Registering {name}: {dll_path}")
            try:
                result = subprocess.run(
                    ["regsvr32", "/s", dll_path],
                    capture_output=True,
                    timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if helpers.os_is_windows() else 0
                )
                if result.returncode == 0:
                    logger.info(f"{name} registered successfully")
                else:
                    logger.error(f"Failed to register {name} (exit code {result.returncode})")
                    if not helpers.is_admin():
                        logger.error(
                            "Note: Administrator privileges are required to register DirectShow drivers. "
                            "Please run GoExport as Administrator."
                        )
                    all_ok = False
            except subprocess.TimeoutExpired:
                logger.error(f"Registration of {name} timed out")
                all_ok = False
            except Exception as e:
                logger.error(f"Failed to register {name}: {e}")
                all_ok = False

        return all_ok

    # ------------------------------------------------------------------
    # File integrity
    # ------------------------------------------------------------------

    def _check_file_integrity(self, path: str) -> bool:
        """Return True if the file exists and has a non-zero size."""
        try:
            size = os.path.getsize(path)
            if size == 0:
                logger.warning(f"File is empty (possible corrupt download): {path}")
                return False
            return True
        except OSError as e:
            logger.error(f"Could not check file integrity for {path}: {e}")
            return False

    # ------------------------------------------------------------------
    # Diagnostic report
    # ------------------------------------------------------------------

    def generate_diagnostic_report(self) -> str | None:
        """Generate and save a diagnostic report. Returns the file path, or None on error."""
        system_info = helpers.get_computer_specs()

        lines = [
            f"=== {helpers.get_config('APP_NAME')} Diagnostic Report ===",
            f"App Version: {helpers.get_config('APP_VERSION')}",
            f"Generated:   {datetime.now().isoformat()}",
            "",
            "--- System Information ---",
            f"OS:              {system_info['os']} {system_info['os_version']}",
            f"Architecture:    {helpers.get_arch()}",
            f"CPU:             {system_info['cpu']}",
            f"Cores/Threads:   {system_info['cores']}/{system_info['threads']}",
            f"RAM:             {system_info['ram']} GB",
            f"Disk:            {system_info['disk']} GB",
            f"Standalone exe:  {helpers.is_frozen()}",
            "",
            "--- Issues Found ---",
        ]

        if self.issues:
            for issue in self.issues:
                lines.append(f"  * {issue}")
        else:
            lines.append("  (none)")

        lines += [
            "",
            "--- Log File ---",
        ]

        try:
            from modules.logger import log_file as current_log_file
            lines.append(f"  {current_log_file}")
        except Exception:
            lines.append("  (log file path unavailable)")

        lines += [
            "",
            "--- Support ---",
            "Please share this file and the log file listed above when seeking support.",
            "You can find support at: https://discord.gg/ejwJYtQDrS",
        ]

        report = "\n".join(lines)

        report_path = helpers.get_path(helpers.get_app_folder(), "diagnostic_report.txt")
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info(f"Diagnostic report saved to: {report_path}")
            return report_path
        except Exception as e:
            logger.error(f"Failed to save diagnostic report: {e}")
            return None

