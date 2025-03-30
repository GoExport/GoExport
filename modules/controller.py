import helpers
from modules.editor import Editor
from modules.navigator import Interface
from modules.capture import Capture
from modules.parameters import Parameters
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich import print
from modules.logger import logger

class Controller:
    def __init__(self):
        self.browser = Interface()
        self.editor = Editor()
        self.capture = Capture()
        self.parameters = Parameters()
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

        # Set the resolution
        if self.resolution is None:
            if not self.parameters.no_input:
                self.resolution = Prompt.ask("[bold red]Required:[/bold red] Please select your desired resolution", choices=list(helpers.get_config("AVAILABLE_SIZES").keys()), default="1280x720")
            else:
                self.resolution = self.parameters.resolution
            if self.resolution not in helpers.get_config("AVAILABLE_SIZES"):
                raise ValueError(f"Invalid resolution: {self.resolution}")
            logger.info(f"User chose {self.resolution}")
            self.width, self.height, self.widescreen = helpers.get_config("AVAILABLE_SIZES")[self.resolution]

        self.svr_name = service_data["name"]
        self.svr_domain = service_data.get("domain", [])
        self.svr_player = service_data.get("player", [])
        self.svr_required = service_data.get("requires", [])

        # Asks if the user wants automated editing
        if self.auto_edit is None:
            if not self.parameters.no_input:
                self.auto_edit = Confirm.ask("Would you like to enable automated editing? (Auto editing is in beta and may not be perfect!)", default=True)
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
        self.RECORDING_EDITED = helpers.get_path(helpers.get_user_folder("Videos"), self.filename)
        if self.PROJECT_FOLDER is None:
            self.PROJECT_FOLDER = helpers.get_path(helpers.get_user_folder("Videos"), self.readable_filename)

        # Begin generating the URL
        if not self.generate():
            logger.error("Could not generate playback URL")
            return False

        return True

    def generate(self):
        """Generates the URL."""
        temp = helpers.get_url(self.svr_domain, self.svr_player)
        self.svr_url = temp.format(movie_id = self.movieid, owner_id = self.ownerid, width = self.width, height = self.height, wide = int(self.widescreen))
        print(f"Playback URL: {self.svr_url}")
        return True

    def export(self):
        if not self.browser.start():
            logger.error("Could not start webdriver")
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
            self.editor.add_clip(self.RECORDING, clip_id, self.width, self.height)
            
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
            if not helpers.make_dir(self.PROJECT_FOLDER):
                logger.error("Could not create the project folder")
                return False
            
            # Copy the recording to the project folder
            if not helpers.copy_file(self.RECORDING, self.PROJECT_FOLDER):
                logger.error("Could not copy the recording")
                return False
            
            return True

    def final(self, outro=True):
        # Add the outro
        # if self.widescreen and outro:
        #     self.editor.add_clip(helpers.get_path(helpers.get_app_folder(), helpers.get_config("OUTRO_WIDE")), len(self.editor.clips))
        # elif not self.widescreen and outro:
        #     self.editor.add_clip(helpers.get_path(helpers.get_app_folder(), helpers.get_config("OUTRO_STANDARD")), len(self.editor.clips))

        # Tell the user about the outro
        if outro:
            print(f"[bold yellow]WARNING:[/bold yellow] The outro will not be added to your video as it will break the output. You can either add it manually later, or completely disregard it, we apologize for the inconvenience.")

        # Render the video
        self.editor.render(self.RECORDING_EDITED)
        return True