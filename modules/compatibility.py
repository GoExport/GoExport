import shutil
import helpers
from modules.logger import logger

class Compatibility:
    def __init__(self):
        pass

    def test(self) -> bool:
        # Skip compatibility test
        if helpers.get_config("SKIP_COMPAT"):
            return True
        
        # -- Non-required dependencies
        # Check if VLC media player using which
        if shutil.which("vlc") is None:
            logger.warning("VLC media player not found (Needed for Video Playback)")
            self.vlc = False

        # -- Required dependencies
        # Gather FFMPEG, FFPROBE, and FFPLAY
        ffmpeg = helpers.get_path(None, helpers.get_config("PATH_FFMPEG"))
        ffprobe = helpers.get_path(None, helpers.get_config("PATH_FFPROBE"))
        ffplay = helpers.get_path(None, helpers.get_config("PATH_FFPLAY"))
        
        # Check for FFMPEG, FFPROBE, and FFPLAY
        if not helpers.try_path(ffmpeg):
            return False
        
        if not helpers.try_path(ffprobe):
            return False
        
        if not helpers.try_path(ffplay):
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
            return False
        
        # Gather Chromedriver
        chromedriver = helpers.get_path(None, helpers.get_config("PATH_CHROMEDRIVER"))

        # Check for Chromedriver
        if not helpers.try_path(chromedriver):
            return False
        
        # Verify validity of Chromedriver
        if not helpers.try_command(chromedriver, '-v'):
            logger.error(f"Failed to validate {chromedriver}")
            return False

        return True
    