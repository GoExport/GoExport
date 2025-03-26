import shutil
import helpers
from modules.logger import logger

class Compatibility:
    def __init__(self):
        pass

    def test(self) -> bool:
        if helpers.is_frozen():
            # Check existence of "first_run" file
            if not helpers.try_path(helpers.get_path(helpers.get_app_folder(), "first_run")):
                # Check if running as admin
                if not helpers.is_admin():
                    logger.error("First time setup detected - please run as administrator!")
                    return False
                else:
                    # Register dll
                    if not helpers.try_command("regsvr32", "/s", helpers.get_path(helpers.get_app_folder(), helpers.get_config('PATH_LIBS_RECORD_64'))):
                        logger.error("Could not install required dependencies!")
                        return False
                    if not helpers.try_command("regsvr32", "/s", helpers.get_path(helpers.get_app_folder(), helpers.get_config('PATH_LIBS_RECORD_32'))):
                        logger.error("Could not install required dependencies!")
                        return False
                    if not helpers.try_command("regsvr32", "/s", helpers.get_path(helpers.get_app_folder(), helpers.get_config('PATH_LIBS_AUDIO_64'))):
                        logger.error("Could not install required dependencies!")
                        return False
                    if not helpers.try_command("regsvr32", "/s", helpers.get_path(helpers.get_app_folder(), helpers.get_config('PATH_LIBS_AUDIO_32'))):
                        logger.error("Could not install required dependencies!")
                        return False

                    # Create "first_run" file
                    helpers.create_file(helpers.get_path(helpers.get_app_folder(), "first_run"))

                    logger.info("First time setup complete!")

        # Skip compatibility test
        if helpers.get_config("SKIP_COMPAT"):
            return True
        
        # Check app
        logger.info(f"{helpers.get_config("APP_NAME")} v{helpers.get_config('APP_VERSION')}")

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
        for gpu in system_info['gpu']:
            logger.info(f"GPU: {gpu['name']}")
            logger.info(f"  VRAM: {gpu['vram_total']} GB")
            logger.info(f"  VRAM Used: {gpu['vram_used']} GB")
            logger.info(f"  VRAM Free: {gpu['vram_free']} GB")
            logger.info(f"  VRAM Utilization: {gpu['vram_util']}%")
        
        # Check if standalone
        logger.info(f"Executable: {helpers.is_frozen()}")

        # -- Required dependencies
        # Gather Flash
        flash = helpers.get_path("C:\\", helpers.get_config("PATH_FLASH"))

        # Check for Flash
        if not helpers.try_path(flash):
            logger.error(f"Failed to locate {flash}")
            return False
        
        # Gather FFMPEG, FFPROBE, and FFPLAY
        ffmpeg = helpers.get_path(None, helpers.get_config("PATH_FFMPEG"))
        ffprobe = helpers.get_path(None, helpers.get_config("PATH_FFPROBE"))
        ffplay = helpers.get_path(None, helpers.get_config("PATH_FFPLAY"))
        
        # Check for FFMPEG, FFPROBE, and FFPLAY
        if not helpers.try_path(ffmpeg):
            logger.error(f"Failed to locate {ffmpeg}")
            return False
        
        if not helpers.try_path(ffprobe):
            logger.error(f"Failed to locate {ffprobe}")
            return False
        
        if not helpers.try_path(ffplay):
            logger.error(f"Failed to locate {ffplay}")
            return False
        
        # Verify validity of FFMPEG, FFPROBE, and FFPLAY
        if not helpers.try_command(ffmpeg, '-h'):
            logger.error(f"Failed to validate {ffmpeg}")
            return False
        
        if not helpers.try_command(ffprobe, '-h'):
            logger.error(f"Failed to validate {ffprobe}")
            return False
        
        if not helpers.try_command(ffplay, '-h'):
            logger.error(f"Failed to validate {ffplay}")
            return False
        
        # Gather Chromium
        chromium = helpers.get_path(None, helpers.get_config("PATH_CHROMIUM"))

        # Check for Chromium
        if not helpers.try_path(chromium):
            logger.error(f"Failed to locate {chromium}")
            return False
        
        # Gather Chromedriver
        chromedriver = helpers.get_path(None, helpers.get_config("PATH_CHROMEDRIVER"))

        # Check for Chromedriver
        if not helpers.try_path(chromedriver):
            logger.error(f"Failed to locate {chromedriver}")
            return False
        
        # Verify validity of Chromedriver
        if not helpers.try_command(chromedriver, '-v'):
            logger.error(f"Failed to validate {chromedriver}")
            return False

        return True
    