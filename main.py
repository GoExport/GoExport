# GoExport
import sys
import helpers
from modules.compatibility import Compatibility
from modules.flow import Controller
from modules.logger import logger
from rich.prompt import Confirm
from rich import print
from PyQt6.QtWidgets import QApplication
from modules.window import Window

def welcome():
    import art
    Art = art.text2art(helpers.get_config("APP_NAME"), font="tarty1")
    print(Art)
    print(f"[green]{helpers.get_config('APP_NAME')} [bold]v{helpers.get_config('APP_VERSION')} {'[blue]BETA[/blue]' if helpers.get_config('APP_BETA') else ''}[/bold]")
    print(f"[yellow]Created by [link=https://lexian.dev][blue]LexianDEV[/blue][/link] and the outro was created by [link=https://www.youtube.com/@AlexDirector][blue]Alex Director[/blue][/link]")
    print(f"[blue][link=https://discord.gg/ejwJYtQDrS]Join the Official GoExport Discord server[/link][/blue]")

def disclaimer():
    print("[orange]Warning: [bold]This application will create and store logs on your system, they will never leave your system unless you choose to share them, in which case the logs may contain personally identifiable information such as system information, file paths, and other data. It is recommended that you exercise caution when sharing these logs.")

def main():
    # Initalize classes
    compatibility = Compatibility()
    controller = Controller()
    
    try:
        # Run inital compatibility check
        logger.info("Please wait while we verify dependencies")
        if not compatibility.test():
            logger.fatal("You did not pass the compatibility check")
            return False
        logger.info("You passed the compatibility check")

        # Welcome message
        welcome()

        # Check if no GUI is enabled
        if not helpers.get_param("no_gui"):
            app = QApplication(sys.argv)
            window = Window(controller)

            # Initalization
            window.show()

            app.exec()
            sys.exit(0)

        while True:
            if not controller.setup():
                logger.fatal("Unable to complete setup")
                return False
            
            if not controller.export():
                logger.fatal("Unable to export video")
                return False

            # Ask if user wants to continue
            print("[blue]Adding an additional video will allow you to merge multiple videos together. This is useful if you want to combine multiple videos into one or you've got a multipart series.")
            
            # If no input is enabled, skip this question and default to false
            if not helpers.get_param("no_input"):
                continue_prompt = Confirm.ask("Would you like to add an additional video?", default=False)
            else:
                continue_prompt = False
            logger.info(f"User chose to continue: {continue_prompt}")

            if not continue_prompt:
                break

        # Ask if user wants to include the outro
        if controller.auto_edit:
            if not helpers.get_param("no_input"):
                confirm_outro = Confirm.ask("Would you like to include the outro for GoExport?", default=True)
            else:
                confirm_outro = True
            logger.info(f"User chose to include the outro: {confirm_outro}")

            if not controller.final(confirm_outro):
                logger.fatal("Unable to edit video")
                return False
            
            print(f"[green]Your video has been successfully exported! [blue bold]It is located at {controller.RECORDING_EDITED}")
        else:
            if not helpers.get_param("no_input"):
                confirm_outro = Confirm.ask("Would you like to add the outro for GoExport to your project folder?", default=True)
            else:
                confirm_outro = True
            logger.info(f"User chose to include the outro: {confirm_outro}")

            # Copy the outro to the project folder
            if confirm_outro:
                try:
                    if not helpers.copy_file(helpers.get_path(None, helpers.get_config(f"OUTRO_WIDE_{controller.width}x{controller.height}")), helpers.get_path(controller.PROJECT_FOLDER)):
                        logger.fatal("Failed to copy the outro to the project folder")
                except Exception as e:
                    logger.fatal(f"Failed to copy the outro: {e}")

        if not controller.auto_edit:
            # Ask if user wants to open the folder
            if not helpers.get_param("no_input"):
                open_folder = Confirm.ask("Would you like to open the folder containing the video?", default=True)
            else:
                open_folder = False
            logger.info(f"User chose to open the folder: {open_folder}")
            if open_folder:
                helpers.open_folder(controller.PROJECT_FOLDER)
        else:
            # Ask if user wants to open the location of the video
            if not helpers.get_param("no_input"):
                open_folder = Confirm.ask("Would you like to open the folder containing the video?", default=True)
            else:
                open_folder = False
            logger.info(f"User chose to open the folder: {open_folder}")
            if open_folder:
                helpers.open_folder(controller.RECORDING_EDITED_PATH)
        
        # Suggest a video editor
        if not controller.auto_edit:
            print("[blue]If you need a video editor, consider OpenShot Video Editor. It's a free and open-source option available for download [link=https://www.openshot.org/download/]here[/link]. Alternatively, you can use any video editor of your choice. [italic](Not sponsored by OpenShot)[/italic]")

        # Disclaimer
        if not helpers.get_param("no_input"):
            disclaimer()

        # Sleep for a bit
        if not helpers.get_param("no_input"):
            helpers.wait(5)

        return True
    except Exception as e:
        logger.fatal(f"Fatal error in main: {e}")
        return False

if __name__ == '__main__':
    try:
        if not main():
            logger.fatal("The application failed to finish")
    except Exception as e:
        logger.fatal(f"Unhandled exception: {e}")