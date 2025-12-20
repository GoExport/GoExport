# GoExport
import sys
import os
import helpers
from modules.compatibility import Compatibility
from modules.flow import Controller
from modules.logger import logger
from modules.update import Update
from modules.output import structured_output
from modules.exceptions import TimeoutError
from rich.prompt import Confirm
from rich import print
from PyQt6.QtWidgets import QApplication
from modules.window import Window

# Exit codes
EXIT_SUCCESS = 0
EXIT_FATAL_ERROR = 1
EXIT_TIMEOUT = 2

def welcome():
    import art
    Art = art.text2art(helpers.get_config("APP_NAME"), font="tarty1")
    print(Art)
    print(f"[green]{helpers.get_config('APP_NAME')} [bold]v{helpers.get_config('APP_VERSION')} {'[blue]BETA[/blue]' if helpers.get_config('APP_BETA') else ''}[/bold]")
    print(f"[yellow]Created by [link=https://lexian.dev][blue]LexianDEV[/blue][/link] and the outro was created by [link=https://www.youtube.com/@AlexDirector][blue]Alex Director[/blue][/link]")
    update_message()
    print(f"[blue][link=https://discord.gg/ejwJYtQDrS]Join the Official GoExport Discord server[/link][/blue]")

def update_message():
    new_version = update.check()
    if not new_version:
        return
    print(f"[green]New update available! [bold]v{new_version}")

def disclaimer():
    print("[orange]Warning: [bold]This application will create and store logs on your system, they will never leave your system unless you choose to share them, in which case the logs may contain personally identifiable information such as system information, file paths, and other data. It is recommended that you exercise caution when sharing these logs.")

def main():
    try:
        # Enable structured output if --no-input mode
        if helpers.get_param("no_input"):
            structured_output.enabled = True
            structured_output.started(message="GoExport started in server mode")

        # Run inital compatibility check
        logger.info("Please wait while we verify dependencies")
        structured_output.progress("Verifying dependencies", stage="compatibility")
        if not compatibility.test():
            logger.fatal("You did not pass the compatibility check")
            structured_output.error("Failed compatibility check")
            return False
        logger.info("You passed the compatibility check")

        # Welcome message
        welcome()

        # Check if no GUI is enabled
        if not helpers.has_console():
            # Set up Qt platform plugin debugging for Linux
            if helpers.os_is_linux():
                os.environ['QT_DEBUG_PLUGINS'] = '1'
                logger.info("Linux detected - Qt platform debugging enabled")
                
            try:
                app = QApplication(sys.argv)
                window = Window(controller, update)

                # Initalization
                window.show()

                app.exec()
                sys.exit(EXIT_SUCCESS)
            except Exception as e:
                logger.fatal(f"Failed to initialize GUI: {e}")
                print(f"[red bold]GUI initialization failed: {e}")
                print("[yellow]If you're on Linux using X11/XOrg, you may need to install Qt platform plugins:")
                print("[yellow]sudo apt-get install libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxkbcommon-x11-0 libxcb-cursor0")
                print("[yellow]Or try running with: QT_QPA_PLATFORM=wayland python main.py")
                return False

        structured_output.progress("Setting up export", stage="setup")
        while True:
            if not controller.setup():
                logger.fatal("Unable to complete setup")
                structured_output.error("Failed to complete setup")
                return False
            
            structured_output.progress("Exporting video", stage="export")
            if not controller.export():
                logger.fatal("Unable to export video")
                structured_output.error("Failed to export video")
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
                confirm_outro = helpers.get_param("use_outro")
            logger.info(f"User chose to include the outro: {confirm_outro}")

            structured_output.progress("Finalizing video", stage="finalize")
            if not controller.final(confirm_outro):
                logger.fatal("Unable to edit video")
                structured_output.error("Failed to finalize video")
                return False
            
            print(f"[green]Your video has been successfully exported! [blue bold]It is located at {controller.RECORDING_EDITED}")
            structured_output.completed(output_path=controller.RECORDING_EDITED)
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
            
            structured_output.completed(output_path=controller.PROJECT_FOLDER)

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
            if helpers.get_param("no_input"):
                open_folder = helpers.get_param("open_folder")
            else:
                open_folder = Confirm.ask("Would you like to open the folder containing the video?", default=True)
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
    except TimeoutError as e:
        # Handle timeout errors with proper structured output and exit code
        logger.error(f"Timeout: {e.message}")
        structured_output.skipped(reason=e.message, timeout_type=e.timeout_type)
        # Write human-readable explanation to STDERR (use builtin print, not rich print)
        import builtins
        builtins.print(f"Export skipped: {e.message}", file=sys.stderr)
        sys.exit(EXIT_TIMEOUT)
    except Exception as e:
        logger.fatal(f"Fatal error in main: {e}")
        structured_output.error(str(e))
        return False

if __name__ == '__main__':
    compatibility = Compatibility()
    controller = Controller()
    update = Update()
    try:
        if not main():
            logger.fatal("The application failed to finish")
            sys.exit(EXIT_FATAL_ERROR)
        sys.exit(EXIT_SUCCESS)
    except TimeoutError as e:
        # Handle timeout errors at the top level as well
        logger.error(f"Timeout: {e.message}")
        structured_output.skipped(reason=e.message, timeout_type=e.timeout_type)
        import builtins
        builtins.print(f"Export skipped: {e.message}", file=sys.stderr)
        sys.exit(EXIT_TIMEOUT)
    except Exception as e:
        logger.fatal(f"Unhandled exception: {e}")
        structured_output.error(str(e))
        sys.exit(EXIT_FATAL_ERROR)