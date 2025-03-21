import helpers
from modules.compatibility import Compatibility
from modules.controller import Controller
from modules.logger import logger
from rich.prompt import Confirm
from rich import print

def welcome():
    import art
    Art = art.text2art(helpers.get_config("APP_NAME"), font="tarty1")
    print(Art)
    print(f"[green]{helpers.get_config('APP_NAME')} [bold]v{helpers.get_config('APP_VERSION')}")

def disclaimer():
    print("[orange]Warning: [bold]This application will create and store logs on your system, they will never leave your system unless you choose to share them, in which case the logs may contain personally identifiable information such as system information, file paths, and other data. It is recommended that you exercise caution when sharing these logs.")

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

    # Welcome message
    welcome()

    while True:
        if not controller.setup():
            logger.fatal("Unable to complete setup")
            exit(1)
        
        if not controller.export():
            logger.fatal("Unable to export video")
            return False

        # Ask if user wants to continue
        print("[blue]Adding an additional video will allow you to merge multiple videos together. This is useful if you want to combine multiple videos into one or you've got a multipart series.")
        continue_prompt = Confirm.ask("Would you like to add an additional video?", default=False)
        logger.info(f"User chose to continue: {continue_prompt}")

        if not continue_prompt:
            break

    # Ask if user wants to include the outro
    if controller.auto_edit:
        confirm_outro = Confirm.ask("Would you like to include the outro for GoExport?", default=True)
        logger.info(f"User chose to include the outro: {confirm_outro}")

        if not controller.final(confirm_outro):
            logger.fatal("Unable to edit video")
            return False
        
        print(f"[green]Your video has been successfully exported! [blue bold]It is located at {controller.RECORDING_EDITED}")
    else:
        confirm_outro = Confirm.ask("Would you like to add the outro for GoExport to your project folder?", default=True)

        # Copy the outro to the project folder
        if confirm_outro and controller.widescreen:
            if not helpers.copy_file(helpers.get_path(None, helpers.get_config("OUTRO_WIDE")), helpers.get_path(controller.PROJECT_FOLDER)):
                logger.fatal("Failed to copy the outro to the project folder")
                return False
        if confirm_outro and not controller.widescreen:
            if not helpers.copy_file(helpers.get_path(None, helpers.get_config("OUTRO_STANDARD")), helpers.get_path(controller.PROJECT_FOLDER)):
                logger.fatal("Failed to copy the 4:3 outro to the project folder")
                return False

    if not controller.auto_edit:
        # Ask if user wants to open the folder
        open_folder = Confirm.ask("Would you like to open the folder containing the video?", default=True)
        logger.info(f"User chose to open the folder: {open_folder}")
        if open_folder:
            helpers.open_folder(controller.PROJECT_FOLDER)

    # Suggest a video editor
    if not controller.auto_edit:
        print("[blue]If you need a video editor, consider OpenShot Video Editor. It's a free and open-source option available for download [link=https://www.openshot.org/download/]here[/link]. Alternatively, you can use any video editor of your choice. [italic](Not sponsored by OpenShot)[/italic]")

    # Disclaimer
    disclaimer()

    # Sleep for a bit
    helpers.wait(5)

    return True

if __name__ == '__main__':
    if not main():
        logger.fatal("The application failed to finish")
        exit(1)