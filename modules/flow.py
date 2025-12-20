import os
import helpers
from modules.editor import Editor
from modules.navigator import Interface
from modules.capture import Capture
from modules.server import Server
from rich.prompt import Prompt, IntPrompt, Confirm
from rich import print
from modules.logger import logger

class Controller:
    def __init__(self):
        self.editor = Editor()
        self.capture = Capture()
        self.browser = Interface(obs=self.capture.is_obs)
        self.aspect_ratio = None
        self.resolution = None
        self.auto_edit = None
        self.legacy = False
        self.PROJECT_FOLDER = None  

    # Set up
    def setup(self):
        # Set the aspect ratio
        if not self.set_aspect_ratio():
            logger.error("Could not set aspect ratio")
            return False
        
        # Set the resolution
        if not self.set_resolution():
            logger.error("Could not set resolution")
            return False

        # Set the LVM
        if not self.set_lvm():
            logger.error("Could not set LVM")
            return False

        self.start_server()
        
        # Check if the server is reachable
        if not self.verify_server_reachable():
            return False

        # Set auto edit
        if not self.set_auto_edit():
            logger.error("Could not set auto edit")
            return False

        # Set the owner ID
        if not self.set_owner_id():
            logger.error("Could not set owner ID")
            return False

        # Set the movie ID
        if not self.set_movie_id():
            logger.error("Could not set movie ID")
            return False

        self.setpath()

        # Begin generating the URL
        try:
            if not self.generate():
                logger.error("Could not generate playback URL")
                return False
        except Exception as e:
            logger.error(f"Error generating playback URL: {e}")
            return False

        return True

    def start_server(self):
        # Start the server
        if self.host:
            self.server = Server()
            try:
                self.server.start()
            except Exception as e:
                logger.error(f"Error starting server: {e}")
                return False

    def stop_server(self):
        if self.host:
            try:
                self.server.stop()
            except Exception as e:
                logger.error(f"Error stopping server: {e}")
                return False

    def set_aspect_ratio(self, aspect_ratio: str|None = None):
        if not helpers.get_param("no_input"):
            # GUI/Interactive mode
            if aspect_ratio is not None:
                # GUI provided a value - validate it
                if aspect_ratio not in helpers.get_config("AVAILABLE_ASPECT_RATIOS"):
                    raise ValueError(f"Invalid aspect ratio: {aspect_ratio}")
                self.aspect_ratio = aspect_ratio
                helpers.save("aspect_ratio", self.aspect_ratio)
            else:
                # Interactive mode: show options and prompt
                helpers.print_list(helpers.get_config("AVAILABLE_ASPECT_RATIOS"))
                self.aspect_ratio = helpers.has_console() and Prompt.ask("[bold red]Required:[/bold red] Please select your desired aspect ratio", choices=helpers.get_config("AVAILABLE_ASPECT_RATIOS"), default=helpers.load("aspect_ratio", helpers.get_config("AVAILABLE_ASPECT_RATIOS")[-1]), show_choices=False)
                helpers.save("aspect_ratio", self.aspect_ratio)
        else:
            # CLI mode
            self.aspect_ratio = helpers.get_param("aspect_ratio")
            if self.aspect_ratio not in helpers.get_config("AVAILABLE_ASPECT_RATIOS"):
                raise ValueError(f"Invalid aspect ratio: {self.aspect_ratio}")
        
        logger.info(f"User chose {self.aspect_ratio}")
        return True

    def set_resolution(self, resolution: str|None = None):
        if not helpers.get_param("no_input"):
            # GUI/Interactive mode
            if resolution is not None:
                # GUI provided a value - validate it
                if resolution not in helpers.get_config("AVAILABLE_SIZES")[self.aspect_ratio]:
                    raise ValueError(f"Invalid resolution: {resolution}")
                self.resolution = resolution
                helpers.save("resolution", self.resolution)
            else:
                # Interactive mode: show options and prompt
                helpers.print_list(list(helpers.get_config("AVAILABLE_SIZES")[self.aspect_ratio].keys()))
                self.resolution = helpers.has_console() and Prompt.ask("[bold red]Required:[/bold red] Please select your desired resolution", choices=list(helpers.get_config("AVAILABLE_SIZES")[self.aspect_ratio].keys()), default=helpers.load("resolution", list(helpers.get_config("AVAILABLE_SIZES")[self.aspect_ratio].keys())[0]), show_choices=False)
                helpers.save("resolution", self.resolution)
        else:
            # CLI mode
            self.resolution = helpers.get_param("resolution")
            if self.resolution not in helpers.get_config("AVAILABLE_SIZES")[self.aspect_ratio]:
                raise ValueError(f"Invalid resolution: {self.resolution}")
        
        logger.info(f"User chose {self.resolution}")
        self.width, self.height, self.widescreen = helpers.get_config("AVAILABLE_SIZES")[self.aspect_ratio][self.resolution]
        if self.width > 1280 and self.height > 720:
            print("[bold yellow]Warning: The resolution you have selected is higher than 720p. This may cause issues with the recording. Please ensure your system can handle this resolution.")
        
        if helpers.exceeds_monitor_resolution(self.width, self.height):
            logger.error("The selected resolution exceeds your monitor's resolution. Please select a lower resolution.")
            return False
        
        return True

    def set_lvm(self, service: str|None = None):
        # Set the LVM
        AVAILABLE_SERVICES = helpers.get_config("AVAILABLE_SERVICES")
        options = list(AVAILABLE_SERVICES.keys())

        if not helpers.get_param("no_input"):
            # GUI/Interactive mode
            if service is not None:
                # GUI provided a value - validate it
                if service not in options:
                    raise ValueError(f"Invalid service: {service}")
                helpers.save("service", service)
            else:
                # Interactive mode: prompt user
                service = helpers.has_console() and Prompt.ask("[bold red]Required:[/bold red] Please select your desired LVM", choices=options, default=helpers.load("service", options[0]))
                helpers.save("service", service)
        else:
            # CLI mode
            service = helpers.get_param("service")
            if service not in options:
                raise ValueError(f"Invalid service: {service}")
        
        logger.info(f"User chose {service}")
        service_data = AVAILABLE_SERVICES[service]

        # Check if should host, template, window name, and after load scripts
        self.host = service_data.get("host", False)
        self.template = service_data.get("template", False)
        self.window = service_data.get("window", None)
        self.afterloadscripts = service_data.get("afterloadscripts", [])

        # Gather browser details and compile
        self.browserName = helpers.get_config("BROWSER_NAME")
        self.display_name = f"{self.window} - {self.browserName}"

        # Set legacy mode
        self.legacy = service_data.get("legacy", False)
        if self.legacy:
            logger.warning("Legacy mode is enabled: Stability is not guaranteed.")
        
        self.svr_name = service_data["name"]
        self.svr_domain = service_data.get("domain", [])
        self.svr_player = service_data.get("player", [])
        self.svr_required = service_data.get("requires", [])
        self.svr_hostable = service_data.get("hostable", False)

        return True

    def set_auto_edit(self, auto_edit: bool|None = None):
        # Asks if the user wants automated editing
        if self.auto_edit is None:
            if not helpers.get_param("no_input"):
                # GUI mode: use provided value or default to True
                if auto_edit is not None:
                    self.auto_edit = auto_edit
                else:
                    # Interactive mode: prompt user
                    self.auto_edit = helpers.has_console() and Confirm.ask("Would you like to enable automated editing?", default=True)
            else:
                # CLI mode: use parameter or default
                self.auto_edit = helpers.get_param("auto_edit") or True
            logger.info(f"User chose to enable auto editing: {self.auto_edit}")
        return True

    def set_owner_id(self, owner_id: int|None = None):
        # Required: Owner Id
        if 'movieOwnerId' in self.svr_required:
            if not helpers.get_param("no_input"):
                # GUI/Interactive mode
                if owner_id is not None:
                    # GUI provided a value
                    self.ownerid = owner_id
                    helpers.save("owner_id", self.ownerid)
                    logger.info(f"User set owner ID: {self.ownerid}")
                else:
                    # Interactive mode: prompt until valid
                    while True:
                        self.ownerid = helpers.has_console() and IntPrompt.ask("[bold red]Required:[/bold red] Please enter the owner ID", default=helpers.load("owner_id"))
                        if self.ownerid:
                            helpers.save("owner_id", self.ownerid)
                            logger.info(f"User entered owner ID: {self.ownerid}")
                            break
                        print("[bold red]Error:[/bold red] Owner ID cannot be empty. Please enter a valid owner ID.")
            else:
                # CLI mode
                self.ownerid = helpers.get_param("owner_id")
                if not self.ownerid:
                    logger.error("Owner ID is required but not provided in CLI mode")
                    return False
                logger.info(f"CLI owner ID: {self.ownerid}")
        else:
            self.ownerid = None
        return True

    def set_movie_id(self, movie_id: str|None = None):
        # Required: Movie Id
        if 'movieId' in self.svr_required:
            if not helpers.get_param("no_input"):
                # GUI/Interactive mode
                if movie_id is not None:
                    # GUI provided a value
                    self.movieid = movie_id
                    helpers.save("movie_id", self.movieid)
                    logger.info(f"User set movie ID: {self.movieid}")
                else:
                    # Interactive mode: prompt until valid
                    while True:
                        self.movieid = helpers.has_console() and Prompt.ask("[bold red]Required:[/bold red] Please enter the movie ID", default=helpers.load("movie_id"))
                        if self.movieid:
                            helpers.save("movie_id", self.movieid)
                            logger.info(f"User entered movie ID: {self.movieid}")
                            break
                        print("[bold red]Error:[/bold red] Movie ID cannot be empty. Please enter a valid movie ID.")
            else:
                # CLI mode
                self.movieid = helpers.get_param("movie_id")
                if not self.movieid:
                    logger.error("Movie ID is required but not provided in CLI mode")
                    return False
                logger.info(f"CLI movie ID: {self.movieid}")
        else:
            self.movieid = None
        return True

    def reset(self):
        self.editor.reset_clips()
        logger.info(f"Editor clips have been reset. {self.editor.clips}")

    def verify_server_reachable(self):
        logger.info(f"Checking if {self.svr_name} is reachable...")
        self.serverOnline, self.serverStatus = helpers.try_url(helpers.get_url(self.svr_domain))
        if not self.serverOnline:
            if self.svr_hostable:
                logger.error(f"Could not reach {self.svr_name} (status: {self.serverStatus}), please ensure it is running and try again.")
            else:
                logger.error(f"Could not reach {self.svr_name} (status: {self.serverStatus}), please check your internet connection and try again.")
            return False
        logger.info(f"{self.svr_name} is reachable (status: {self.serverStatus})")
        return True

    def setpath(self, path: str|None = None):
        self.readable_filename = helpers.generate_path()
        self.filename = f"{self.readable_filename}{helpers.get_config('DEFAULT_OUTPUT_EXTENSION')}"

        if path is None:
            self.RECORDING = helpers.get_path(None, helpers.get_config("DEFAULT_OUTPUT_FILENAME"), self.filename)
        else:
            self.RECORDING = path

        # Check if custom output path is provided via command-line parameter
        custom_output_path = helpers.get_param("output_path")
        
        if custom_output_path:
            # Convert to absolute path for consistency
            custom_output_path = os.path.abspath(custom_output_path)
            
            # Use custom output path for final rendered video
            if os.path.isdir(custom_output_path):
                # If it's an existing directory, append the filename
                self.RECORDING_EDITED = os.path.join(custom_output_path, self.filename)
                self.RECORDING_EDITED_PATH = custom_output_path
            elif custom_output_path.endswith(os.sep) or (not os.path.splitext(custom_output_path)[1]):
                # If path ends with separator or has no extension, treat as directory
                # Create directory if it doesn't exist
                os.makedirs(custom_output_path, exist_ok=True)
                self.RECORDING_EDITED = os.path.join(custom_output_path, self.filename)
                self.RECORDING_EDITED_PATH = custom_output_path
            else:
                # If it's a full file path, use it as-is
                self.RECORDING_EDITED = custom_output_path
                self.RECORDING_EDITED_PATH = os.path.dirname(custom_output_path)
                # Ensure the directory exists
                os.makedirs(self.RECORDING_EDITED_PATH, exist_ok=True)
        else:
            # Use default output path
            self.RECORDING_EDITED = helpers.get_path(helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_FOLDER_OUTPUT_FILENAME")), self.filename)
            self.RECORDING_EDITED_PATH = helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_FOLDER_OUTPUT_FILENAME"))
        
        if self.PROJECT_FOLDER is None:
            self.PROJECT_FOLDER = helpers.get_path(helpers.get_config("DEFAULT_FOLDER_OUTPUT_FILENAME"), self.readable_filename)

        logger.info(f"{self.RECORDING or None} {self.RECORDING_EDITED or None} {self.PROJECT_FOLDER or None}")

    def generate(self):
        """Generates the URL."""
        temp = helpers.get_url(self.svr_domain, self.svr_player)
        self.svr_url = self.format(temp)
        print(f"Playback URL: {self.svr_url}")
        return True

    def format(self, input: str) -> str:
        """Format the string, for example {movie_id} is parsed and replaced with the actual movie ID."""
        return input.format(
            movie_id=self.movieid,
            owner_id=self.ownerid,
            width=self.width,
            height=self.height,
            wide=int(self.widescreen)
        )

    def export(self):
        try:
            if not self.browser.start():
                logger.error("Could not start webdriver")
                return False

            if self.template:
                self.browser.inject_in_future('function obj_DoFSCommand(command, args) { switch (command) { case "start": startRecord = Date.now(); console.log("Video started " + startRecord); document.getElementById("obj").pause(); document.getElementById("obj").seek(0); break; case "stop": stopRecord = Date.now(); console.log("Video stopped " + stopRecord); break; } }')

            if not self.capture.is_obs:
                if not self.browser.warning(self.width, self.height):
                    logger.error("Could not show warning")
                    return False

            if self.legacy:
                if not self.capture.start(self.RECORDING, self.width, self.height, self.display_name):
                    logger.error("Could not start recording")
                    return False

            try:
                self.browser.driver.get(self.svr_url)
            except Exception as e:
                raise RuntimeError(f"Failed to load {self.svr_url}: {e}")

            # Check if the site has any data; if so, do nothing
            if self.browser.check_data(self.svr_url):
                offset = 1
            else:
                offset = 0

            if not self.browser.enable_flash(offset=offset):
                logger.error("Could not enable flash")
                return False

            for script in self.afterloadscripts:
                self.browser.inject_now(self.format(script))

            if not self.browser.await_started():
                logger.error("Could not wait for start")
                return False
            
            if not self.legacy:
                if not self.capture.start(self.RECORDING, self.width, self.height, self.display_name):
                    logger.error("Could not start recording")
                    return False
                else:
                    self.browser.play()
            
            self.prestart = self.capture.start_time  # Timestamp for when FFmpeg started (ms)
            self.prestart_delay = self.capture.startup_delay  # Ensure delay is accounted for (ms)
            logger.debug(f"Prestart: {self.prestart} | Delay: {self.prestart_delay}")

            if not self.browser.await_completed():
                logger.error("Could not wait for completion")
                return False

            if not self.capture.stop():
                logger.error("Could not stop the recording")
                return False
            self.postend = self.capture.end_time  # Timestamp for when FFmpeg ended (ms)
            self.postend_delay = self.capture.ended_delay  # Ensure delay is accounted for (ms)

            # Update paths
            self.setpath(self.capture.filename)

            # Stop the server
            self.stop_server()

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

                if self.legacy:
                    # Calculate the starting and ending times for the clip
                    if None in (self.prestart_delay, video_started, video_start_offset, self.prestart):
                        logger.error("One or more timestamp values are None. Cannot calculate start time.")
                        return False
                    started = (self.prestart_delay + (video_started + video_start_offset) - self.prestart)

                    # Combine the calculated times
                    starting = started
                    self.start_from = helpers.ms_to_s(starting)
                    self.end_at = self.editor.get_clip_length(clip_id)
                    logger.debug(f"{self.start_from} : {self.end_at}")

                    # Trim the video first
                    self.editor.trim(clip_id, self.start_from, self.end_at)

                # Return success
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
        
        # Handle file conflicts for custom output path
        output_path = self.RECORDING_EDITED
        if os.path.exists(output_path):
            # File already exists, append number suffix
            base_name, ext = os.path.splitext(output_path)
            counter = 1
            while os.path.exists(f"{base_name}_{counter}{ext}"):
                counter += 1
            output_path = f"{base_name}_{counter}{ext}"
            logger.info(f"Output file already exists, using: {output_path}")
            self.RECORDING_EDITED = output_path
        
        # Render the video
        self.editor.render(self.RECORDING_EDITED, target_width=self.width, target_height=self.height, reencode=outro)
        return True