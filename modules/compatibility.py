from time import time
import helpers
from modules.logger import logger

class Compatibility:
    def __init__(self):
        pass

    def test(self) -> bool:
        # Skip compatibility test
        if helpers.get_config("SKIP_COMPAT"):
            return True
        
        # Create "output" folder
        helpers.make_dir(helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_FOLDER_OUTPUT_FILENAME")))
        
        # Check app
        logger.info(f"{helpers.get_config('APP_NAME')} v{helpers.get_config('APP_VERSION')}")

        # Check OS
        if helpers.os_is_windows():
            logger.info("OS: Windows")
        elif helpers.os_is_linux():
            logger.info("OS: Linux")
        else:
            logger.error("OS: Unsupported")
            return False
        
        # Get the architecture
        logger.info(f"Architecture: {helpers.get_arch()}")
        
        # Put the system information here
        system_info = helpers.get_computer_specs()
        logger.info("System Information:")
        logger.info(f"  OS: {system_info['os']} {system_info['os_version']}")
        logger.info(f"  CPU: {system_info['cpu']}")
        logger.info(f"  Cores: {system_info['cores']}")
        logger.info(f"  Threads: {system_info['threads']}")
        logger.info(f"  RAM: {system_info['ram']} GB")
        logger.info(f"  Disk: {system_info['disk']} GB")
        
        # Check if standalone
        logger.info(f"Executable: {helpers.is_frozen()}")

        # -- Required dependencies
        # Get the paths for FFMPEG, FFPROBE, and FFPLAY.
        if helpers.os_is_windows():
            ffmpeg = helpers.get_path(None, helpers.get_config("PATH_FFMPEG_WINDOWS"))
            ffprobe = helpers.get_path(None, helpers.get_config("PATH_FFPROBE_WINDOWS"))
            ffplay = helpers.get_path(None, helpers.get_config("PATH_FFPLAY_WINDOWS"))
        elif helpers.os_is_linux():
            ffmpeg = helpers.get_path(None, helpers.get_config("PATH_FFMPEG_LINUX"))
            ffprobe = helpers.get_path(None, helpers.get_config("PATH_FFPROBE_LINUX"))
            ffplay = helpers.get_path(None, helpers.get_config("PATH_FFPLAY_LINUX"))
        else:
            logger.error("Unsupported OS")
            return False
        
        try:
            # Verify that the paths are valid (ffmpeg, ffprobe, ffplay exists)
            if not helpers.try_path(ffmpeg):
                raise FileNotFoundError(f"Failed to locate {ffmpeg}")
            if not helpers.try_path(ffprobe):
                raise FileNotFoundError(f"Failed to locate {ffprobe}")
            if not helpers.try_path(ffplay):
                raise FileNotFoundError(f"Failed to locate {ffplay}")
        except Exception as e:
            logger.error(f"Dependency check failed: {e}")
            return False

        # Get the paths of Chromium and Chromedriver
        if helpers.os_is_windows():
            chromium = helpers.get_path(None, helpers.get_config("PATH_CHROMIUM_WINDOWS"))
            chromedriver = helpers.get_path(None, helpers.get_config("PATH_CHROMEDRIVER_WINDOWS"))
        elif helpers.os_is_linux():
            chromium = helpers.get_path(None, helpers.get_config("PATH_CHROMIUM_LINUX"))
            chromedriver = helpers.get_path(None, helpers.get_config("PATH_CHROMEDRIVER_LINUX"))
        else:
            logger.error("Unsupported OS")
            return False

        try:
            if not helpers.try_path(chromium):
                raise FileNotFoundError(f"Failed to locate {chromium}")
            if not helpers.try_path(chromedriver):
                raise FileNotFoundError(f"Failed to locate {chromedriver}")
        except Exception as e:
            logger.error(f"Dependency check failed: {e}")
            return False

        return True
