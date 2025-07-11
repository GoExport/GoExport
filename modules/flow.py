import helpers
from modules.editor import Editor
from modules.navigator import Interface
from modules.capture import Capture
from modules.parameters import Parameters
from modules.server import Server
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich import print
from modules.logger import logger

class Controller:
    def __init__(self):
        self.browser = Interface()
        self.editor = Editor()
        self.capture = Capture()
        self.parameters = Parameters()
        self.aspect_ratio = None
        self.resolution = None
        self.auto_edit = None
        self.PROJECT_FOLDER = None  

    # Set up
    def setup(self):
        # Set the LVM
        AVAILABLE_SERVICES = helpers.get_config("AVAILABLE_SERVICES")
        options = list(AVAILABLE_SERVICES.keys())

        # Set the LVM
        if not self.parameters.no_input:
            service = Prompt.ask("[bold red]Required:[/bold red] Please select your desired LVM", choices=options, default=options[0])
        else:
            service = self.parameters.service
        if service not in options:
            raise ValueError(f"Invalid service: {service}")
        logger.info(f"User chose {service}")
        service_data = AVAILABLE_SERVICES[service]

        # Set the aspect ratio
        if self.aspect_ratio is None:
            if not self.parameters.no_input:
                helpers.print_list(helpers.get_config("AVAILABLE_ASPECT_RATIOS"))
                self.aspect_ratio = Prompt.ask("[bold red]Required:[/bold red] Please select your desired aspect ratio", choices=helpers.get_config("AVAILABLE_ASPECT_RATIOS"), default=helpers.get_config("AVAILABLE_ASPECT_RATIOS")[-1], show_choices=False)
            else:
                self.aspect_ratio = self.parameters.aspect_ratio
            if self.aspect_ratio not in helpers.get_config("AVAILABLE_ASPECT_RATIOS"):
                raise ValueError(f"Invalid aspect ratio: {self.aspect_ratio}")
            logger.info(f"User chose {self.aspect_ratio}")

        # Set the resolution
        if self.resolution is None:
            if not self.parameters.no_input:
                helpers.print_list(list(helpers.get_config("AVAILABLE_SIZES")[self.aspect_ratio].keys()))
                self.resolution = Prompt.ask("[bold red]Required:[/bold red] Please select your desired resolution", choices=list(helpers.get_config("AVAILABLE_SIZES")[self.aspect_ratio].keys()), default=list(helpers.get_config("AVAILABLE_SIZES")[self.aspect_ratio].keys())[0], show_choices=False)
            else:
                self.resolution = self.parameters.resolution
            if self.resolution not in helpers.get_config("AVAILABLE_SIZES")[self.aspect_ratio]:
                raise ValueError(f"Invalid resolution: {self.resolution}")
            logger.info(f"User chose {self.resolution}")
            self.width, self.height, self.widescreen = helpers.get_config("AVAILABLE_SIZES")[self.aspect_ratio][self.resolution]
            if self.width > 1280 and self.height > 720:
                print("[bold yellow]Warning: The resolution you have selected is higher than 720p. This may cause issues with the recording. Please ensure your system can handle this resolution.")
            
        # Start the server
        self.server = Server()
        try:
            self.server.start()
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            return False

        self.svr_name = service_data["name"]
        self.svr_domain = service_data.get("domain", [])
        self.svr_player = service_data.get("player", [])
        self.svr_required = service_data.get("requires", [])

        if helpers.exceeds_monitor_resolution(self.width, self.height):
            helpers.show_popup(helpers.get_config("APP_NAME"), f"Your resolution is not large enough to contain this resolution or aspect ratio. Please downscale your video or change your screen orientation or resolution.", 16)
            return False
        
        # Asks if the user wants automated editing
        if self.auto_edit is None:
            if not self.parameters.no_input:
                self.auto_edit = Confirm.ask("Would you like to enable automated editing? (Auto editing is experimental but if you can test it and report back we'd appreciate it!)", default=True)
            else:
                self.auto_edit = self.parameters.auto_edit or True
            logger.info(f"User chose to enable auto editing: {self.auto_edit}")

        # Required: Owner Id
        if 'movieOwnerId' in self.svr_required:
            while True:
                if not self.parameters.no_input:
                    self.ownerid = IntPrompt.ask("[bold red]Required:[/bold red] Please enter the owner ID")
                else:
                    self.ownerid = self.parameters.owner_id
                logger.info(f"User entered owner ID: {self.ownerid}")
                if self.ownerid:
                    break
                print("[bold red]Error:[/bold red] Owner ID cannot be empty. Please enter a valid owner ID.")
        else:
            self.ownerid = None

        # Required: Movie Id
        if 'movieId' in self.svr_required:
            while True:
                if not self.parameters.no_input:
                    self.movieid = Prompt.ask("[bold red]Required:[/bold red] Please enter the movie ID")
                else:
                    self.movieid = self.parameters.movie_id
                logger.info(f"User entered movie ID: {self.movieid}")
                if self.movieid:
                    break
                print("[bold red]Error:[/bold red] Movie ID cannot be empty. Please enter a valid movie ID.")
        else:
            self.movieid = None

        self.readable_filename = helpers.generate_path()
        self.filename = f"{self.readable_filename}{helpers.get_config('DEFAULT_OUTPUT_EXTENSION')}"

        self.RECORDING = helpers.get_path(None, helpers.get_config("DEFAULT_OUTPUT_FILENAME"), self.filename)
        self.RECORDING_EDITED = helpers.get_path(helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_FOLDER_OUTPUT_FILENAME")), self.filename)
        self.RECORDING_EDITED_PATH = helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_FOLDER_OUTPUT_FILENAME"))
        if self.PROJECT_FOLDER is None:
            self.PROJECT_FOLDER = helpers.get_path(helpers.get_config("DEFAULT_FOLDER_OUTPUT_FILENAME"), self.readable_filename)

        # Begin generating the URL
        try:
            if not self.generate():
                logger.error("Could not generate playback URL")
                return False
        except Exception as e:
            logger.error(f"Error generating playback URL: {e}")
            return False

        return True

    def generate(self):
        """Generates the URL."""
        temp = helpers.get_url(self.svr_domain, self.svr_player)
        self.svr_url = temp.format(movie_id = self.movieid, owner_id = self.ownerid, width = self.width, height = self.height, wide = int(self.widescreen))
        print(f"Playback URL: {self.svr_url}")
        return True

    def export(self):
        try:
            if not self.browser.start():
                logger.error("Could not start webdriver")
                return False

            if not self.browser.warning(self.width, self.height):
                logger.error("Could not show warning")
                return False

            if not self.capture.start(self.RECORDING, self.width, self.height):
                logger.error("Could not start recording")
                return False
            self.prestart = self.capture.start_time  # Timestamp for when FFmpeg started (ms)
            self.prestart_delay = self.capture.startup_delay  # Ensure delay is accounted for (ms)

            print(f"Prestart: {self.prestart} | Delay: {self.prestart_delay}")
            helpers.move_mouse_offscreen()

            try:
                self.browser.driver.get(self.svr_url)
            except Exception as e:
                raise RuntimeError(f"Failed to load {self.svr_url}: {e}")

            if not self.browser.enable_flash():
                logger.error("Could not enable flash")
                return False

            if not self.browser.await_started():
                logger.error("Could not wait for start")
                return False

            if not self.browser.await_completed():
                logger.error("Could not wait for completion")
                return False

            if not self.capture.stop():
                logger.error("Could not stop the recording")
                return False
            self.postend = self.capture.end_time  # Timestamp for when FFmpeg ended (ms)
            self.postend_delay = self.capture.ended_delay  # Ensure delay is accounted for (ms)

            # Stop the server
            try:
                self.server.stop()
            except Exception as e:
                logger.error(f"Error stopping server: {e}")
                return False

            # Get timestamps from the browser for when the video started and ended
            timestamps = self.browser.get_timestamps()
            video_started, video_ended, video_length, video_start_offset, video_end_offset = timestamps

            if not self.browser.close():
                logger.error("Couldn't stop the browser")
                return False

            # Auto editing
            if self.auto_edit: # true
                # Get last clip ID and add 1 to it from editor
                clip_id = len(self.editor.clips)
                self.editor.add_clip(self.RECORDING, clip_id)
                
                # Calculate the starting and ending times for the clip
                started = self.prestart_delay + video_started + video_start_offset - self.prestart

                # Combine the calculated times
                starting = started

                self.start_from = helpers.ms_to_s(starting)
                self.end_at = self.editor.get_clip_length(clip_id)

                print(f"{self.start_from} : {self.end_at}")

                # Trim the video first
                self.editor.trim(clip_id, self.start_from, self.end_at)

                return True
            else: # false
                # Create the project folder
                try:
                    if not helpers.make_dir(self.PROJECT_FOLDER, reattempt=True):
                        logger.error("Could not create the project folder")
                        return False
                except Exception as e:
                    logger.error(f"Error creating project folder: {e}")
                    return False
                
                # Copy the recording to the project folder
                try:
                    if not helpers.copy_file(self.RECORDING, self.PROJECT_FOLDER):
                        logger.error("Could not copy the recording")
                        return False
                except Exception as e:
                    logger.error(f"Error copying recording: {e}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Error in export process: {e}")
            return False

    def final(self, outro=True):
        try:
            if self.aspect_ratio == "16:9" and outro:
                self.editor.add_clip(helpers.get_path(helpers.get_app_folder(), helpers.get_config(f"OUTRO_WIDE_{self.width}x{self.height}")), len(self.editor.clips))
            elif self.aspect_ratio == "9:16" and outro:
                self.editor.add_clip(helpers.get_path(helpers.get_app_folder(), helpers.get_config(f"OUTRO_TALL_{self.width}x{self.height}")), len(self.editor.clips))
            elif self.aspect_ratio == "4:3" and outro:
                self.editor.add_clip(helpers.get_path(helpers.get_app_folder(), helpers.get_config(f"OUTRO_STANDARD_{self.width}x{self.height}")), len(self.editor.clips))
            elif self.aspect_ratio == "14:9" and outro:
                self.editor.add_clip(helpers.get_path(helpers.get_app_folder(), helpers.get_config(f"OUTRO_WIDE_{self.width}x{self.height}")), len(self.editor.clips))
        except Exception as e:
            print(f"[bold yellow]Warning:[/bold yellow] Failed to add the outro: {e}")
        
        # Render the video
        self.editor.render(self.RECORDING_EDITED)
        return True