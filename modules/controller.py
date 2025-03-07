import helpers
from modules.editor import Editor
from modules.navigator import Interface
from modules.capture import Capture
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich import print
from modules.logger import logger

class Controller:
    def __init__(self):
        self.browser = Interface()
        self.editor = Editor()
        self.capture = Capture()

    # Set up
    def setup(self):
        # Set the LVM
        AVAILABLE_SERVICES = helpers.get_config("AVAILABLE_SERVICES")
        options = list(AVAILABLE_SERVICES.keys())

        # Set the LVM
        service = Prompt.ask("[bold red]Required:[/bold red] Please select your desired LVM", choices=options, default=options[0])
        service_data = AVAILABLE_SERVICES[service]

        # Set the resolution
        resolution = Prompt.ask("[bold red]Required:[/bold red] Please select your desired resolution", choices=list(helpers.get_config("AVAILABLE_SIZES").keys()), default="1280x720")
        self.width, self.height, self.widescreen = helpers.get_config("AVAILABLE_SIZES")[resolution]

        self.svr_name = service_data["name"]
        self.svr_domain = service_data.get("domain", [])
        self.svr_player = service_data.get("player", [])
        self.svr_api = service_data.get("api", [])
        self.svr_endpoints = service_data.get("endpoints", [])
        self.svr_required = service_data.get("requires", [])

        # Required: Owner Id
        if 'movieOwnerId' in self.svr_required:
            while True:
                self.ownerid = Prompt.ask("[bold red]Required:[/bold red] Please enter the owner ID")
                if self.ownerid:
                    break
                print("[bold red]Error:[/bold red] Owner ID cannot be empty. Please enter a valid owner ID.")
        else:
            self.ownerid = None

        # Required: Movie Id
        if 'movieId' in self.svr_required:
            while True:
                self.movieid = Prompt.ask("[bold red]Required:[/bold red] Please enter the movie ID")
                if self.movieid:
                    break
                print("[bold red]Error:[/bold red] Movie ID cannot be empty. Please enter a valid movie ID.")
        else:
            self.movieid = None

        # Get the video info
        self.svr_api = helpers.get_url(*self.svr_api, self.svr_endpoints["getMovieInfo"])
        self.video_info = helpers.post_request_to_dict(self.svr_api, {"movieId": self.movieid, "userId": self.ownerid})
        
        self.readable_filename = f"{helpers.to_filename_safe(self.video_info['movie_info']['title'])}"
        self.filename = f"{self.readable_filename}.mp4"

        self.RECORDING = helpers.get_path(None, helpers.get_config("DEFAULT_OUTPUT_FILENAME"), self.filename)
        self.RECORDING_EDITED = helpers.get_path(helpers.get_user_folder("Videos"), self.filename)

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
        self.prestart = self.capture.start_time_ms # get timestamp for when the ffmpeg started
        
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

        # Get timestamps from the browser for when the video started and ended
        timestamps = self.browser.get_timestamps()
        video_started, video_ended, video_started_offset, video_ended_offset = timestamps # unpack timestamps from the browser

        if not self.browser.close():
            logger.error("Couldn't stop the browser")
            return False
        
        starting = video_started + video_started_offset - self.prestart
        ending = video_ended + video_ended_offset - self.prestart

        self.start_from = helpers.ms_to_s(starting)
        self.end_at = helpers.ms_to_s(ending)

        # Get last clip id and add 1 to it from editor
        clip_id = len(self.editor.clips)

        # Trim the video first
        self.editor.add_clip(self.RECORDING, clip_id, self.width, self.height)
        self.editor.trim(clip_id, self.start_from, self.end_at)

        return True

    def final(self, outro=True):
        # Add the outro
        if self.widescreen and outro:
            self.editor.add_clip(helpers.get_path(None, helpers.get_config("OUTRO_WIDE")), len(self.editor.clips))
        elif not self.widescreen and outro:
            self.editor.add_clip(helpers.get_path(None, helpers.get_config("OUTRO_STANDARD")), len(self.editor.clips))

        self.editor.render(self.RECORDING_EDITED)
        return True