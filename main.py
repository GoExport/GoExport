import config
import helpers
from modules import compatibility
from modules.compatibility import Compatibility
from modules.controller import Controller
from modules.logger import logger
from rich.prompt import Confirm
from rich import print

def welcome():
    from art import text2art
    Art = text2art(helpers.get_config("APP_NAME"), font="tarty1")
    print(Art)
    print("[yellow]If you are using Wrapper Offline, remember to start it before proceeding or it won't work!")

def goodbye():
    from art import text2art
    Art = text2art("Goodbye!", font="tarty1")
    print(Art)
    print("[green]Your video was exported!")

def main():
    # Initalize classes
    compatibility = Compatibility()
    controller = Controller()

    # Run inital compatibility check
    logger.info("Please wait while we verify dependencies")
    if not compatibility.test():
        logger.fatal("You did not pass the compatibility check")
        exit(1)
    logger.info("You passed the compatibility check")

    while True:
        if not controller.setup():
            logger.fatal("Unable to complete setup")
            exit(1)
        
        if not controller.export():
            logger.fatal("Unable to export video")
            return False

        # Ask if the user wants to preview the video
        preview_prompt = Confirm.ask("Would you like to preview the video?", default=False)

        if preview_prompt:
            controller.editor.preview()

        # Ask if user wants to continue
        print("[blue]Adding an additional video will allow you to merge multiple videos together. This is useful if you want to combine multiple videos into one or you've got a multipart series.")
        continue_prompt = Confirm.ask("Would you like to add an additional video?", default=False)

        if not continue_prompt:
            break

    # Ask if user wants to include the outro
    confirm_outro = Confirm.ask("Would you like to include the outro for GoExport?", default=True)

    if not controller.final(confirm_outro):
        logger.fatal("Unable to edit video")
        return False

    goodbye()

    if compatibility.vlc is None:
        print("[yellow]You don't appear to have VLC media player installed on your system. The encoded video was encoded successfully, but it may not work on the standard media player of your system. VLC media player is recommended for playback.")

    return True

if __name__ == '__main__':
    welcome()

    if not main():
        logger.fatal("The application failed to finish")
        exit(1)