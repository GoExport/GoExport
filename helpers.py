import json
import string
import config
import shutil
import os
import sys
import pyttsx3
import platform
import psutil
import ctypes
import urllib
import pyautogui
import subprocess
import time
import requests
from rich import print
from modules.logger import logger
from datetime import datetime
import modules.parameters as parameters

# Global variables
parameters = parameters.Parameters()

# Function to grab the key and value of a parameter
def get_param(key: str):
    value = getattr(parameters, key, None)
    logger.debug(f"get_param() key={key} -> {value}")
    return value

# Save management functions
def save(key: str, value):
    """
    Save a value to a key in the data.json file
    :param key: The key to save the value under.
    :param value: The value to save.
    """
    logger.debug(f"save() called with key={key}, value={value}")
    # Load existing data or initialize as empty dict
    data_file_path = get_path(get_app_folder(), get_config("PATH_DATA_FILE")[0])
    if os.path.exists(data_file_path):
        with open(data_file_path, "r") as f:
            try:
                data = json.load(f)
                logger.debug(f"Loaded existing data.json: {data}")
            except json.JSONDecodeError:
                logger.debug(f"JSON decode error in {data_file_path}, initializing empty dict.")
                data = {}
    else:
        logger.debug(f"data.json not found at {data_file_path}, initializing empty dict.")
        data = {}
    data[key] = value
    with open(data_file_path, "w") as f:
        json.dump(data, f, indent=4)
        logger.debug(f"Saved data.json: {data}")

def load(key: str, default=False):
    """
    Load a value from a key in the data.json file
    :param key: The key to load the value from.
    :return: The value associated with the key, or None if not found.
    """
    logger.debug(f"load() called with key={key}")
    data_file_path = get_path(get_app_folder(), get_config("PATH_DATA_FILE")[0])
    if os.path.exists(data_file_path):
        with open(data_file_path, "r") as f:
            try:
                data = json.load(f)
                logger.debug(f"Loaded data.json: {data}")
                return data.get(key, None)
            except json.JSONDecodeError:
                logger.debug(f"JSON decode error in {data_file_path}, returning None.")
                return None
    return default

# Memory management functions
def remember(key: str, value):
    logger.debug(f"remember() called with key={key}, value={value}")
    setattr(remember, key, value)
    return value

def recall(key: str):
    logger.debug(f"recall() called with key={key}")
    return getattr(remember, key, None)

def forget(key: str):
    logger.debug(f"forget() called with key={key}")
    if hasattr(remember, key):
        delattr(remember, key)

# Rest of the helper functions
def os_is_windows():
    result = sys.platform.startswith("win")
    logger.debug(f"os_is_windows() -> {result}")
    return result

def os_is_linux():
    result = sys.platform.startswith("linux")
    logger.debug(f"os_is_linux() -> {result}")
    return result

def os_is_mac():
    result = sys.platform.startswith("darwin")
    logger.debug(f"os_is_mac() -> {result}")
    return result

def is_frozen():
    result = getattr(sys, 'frozen', False)
    logger.debug(f"is_frozen() -> {result}")
    return result

def is_admin():
    try:
        result = ctypes.windll.shell32.IsUserAnAdmin()
        logger.debug(f"is_admin() -> {result}")
        return result
    except AttributeError:
        logger.debug("is_admin() AttributeError: Not Windows or shell32 not available.")
        return False

def get_arch():
    result = platform.machine()
    logger.debug(f"get_arch() -> {result}")
    return result

# Get computer specifications
def get_computer_specs():
    specs = {
        "os": platform.system(),
        "os_version": platform.version(),
        "cpu": platform.processor(),
        "cores": psutil.cpu_count(logical=False),
        "threads": psutil.cpu_count(logical=True),
        "ram": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "disk": round(psutil.disk_usage("/").total / (1024 ** 3), 2),
    }
    logger.debug(f"get_computer_specs() -> {specs}")
    return specs

def move_mouse_offscreen():
    logger.debug("move_mouse_offscreen() called")
    pyautogui.FAILSAFE = False # All we're doing is moving the mouse offscreen
    width, height = pyautogui.size()
    logger.debug(f"Screen size: width={width}, height={height}")
    pyautogui.moveTo(width, height)

def generate_path():
    path = f"{datetime.now().strftime('%Y-%m-%d %H-%M-%S')}"
    logger.debug(f"generate_path() -> {path}")
    return path

def make_dir(path, reattempt: bool = False):
    original_path = path
    counter = 1
    while True:
        try:
            os.makedirs(path)
            logger.debug(f"Directory created: {path}")
            return True
        except FileExistsError:
            logger.warning(f"Directory {path} already exists.")
            logger.debug(f"make_dir() FileExistsError: path={path}, reattempt={reattempt}")
            if not reattempt:
                return False
            path = f"{original_path}_{counter}"
            counter += 1
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            logger.debug(f"make_dir() Exception: {e}")
            return False
    
def open_folder(path):
    """Open a folder in the file system and bring it to the foreground."""
    try:
        if os_is_windows():
            logger.debug(f"open_folder() using explorer for path={path}")
            subprocess.Popen(['explorer', path])
            return True
        elif os_is_linux():
            logger.debug(f"open_folder() using xdg-open for path={path}")
            subprocess.run(["xdg-open", path])
            return True
        else:
            logger.debug(f"open_folder() unsupported OS for path={path}")
            return False
    except Exception as e:
        logger.error(f"Failed to open folder {path}: {e}")
        logger.debug(f"open_folder() Exception: {e}")
        return False

def get_cwd():
    """Get the current working directory, using PyInstaller paths if applicable."""
    if is_frozen():
        logger.debug(f"get_cwd() using sys._MEIPASS: {sys._MEIPASS}")
        return sys._MEIPASS
    cwd = os.getcwd()
    logger.debug(f"get_cwd() using os.getcwd(): {cwd}")
    return cwd

def get_path(cwd: str | None = None, *parts):
    """Construct an absolute path, flattening any lists/tuples in parts."""
    if cwd is None:
        cwd = get_cwd()

    # Flatten lists/tuples in parts
    flattened_parts = []
    for part in parts:
        if isinstance(part, (list, tuple)):
            flattened_parts.extend(part)
        else:
            flattened_parts.append(part)

    result = os.path.join(cwd, *flattened_parts)
    logger.debug(f"get_path() cwd={cwd}, parts={flattened_parts} -> {result}")
    return result

def get_user_folder(folder: str):
    if os_is_windows():
        result = os.path.join(os.environ["USERPROFILE"], folder)
        logger.debug(f"get_user_folder() Windows: {result}")
        return result
    elif os_is_linux():
        result = os.path.join(os.path.expanduser("~"), folder)
        logger.debug(f"get_user_folder() Linux: {result}")
        return result
    else:
        logger.debug(f"get_user_folder() unsupported OS")
        return None

def get_app_folder():
    if is_frozen():
        result = os.path.dirname(sys.executable)
        logger.debug(f"get_app_folder() frozen: {result}")
        return result
    else:
        result = get_cwd()
        logger.debug(f"get_app_folder() not frozen: {result}")
        return result

def get_config(variable: str, default: str = None):
    result = getattr(config, variable, default)
    logger.debug(f"get_config() variable={variable}, default={default} -> {result}")
    return result

def get_resolution(index: int = 0):
    from screeninfo import get_monitors
    monitor = get_monitors()[index]
    logger.debug(f"get_resolution() index={index} -> width={monitor.width}, height={monitor.height}")
    return (monitor.width, monitor.height)

def search_path(name: str):
    """
    Wrapper for shutil.which to find the path of an executable by name in the system PATH.
    :param name: Name of the executable to find.
    :return: Full path to the executable if found, None otherwise.
    """
    result = shutil.which(name)
    logger.debug(f"search_path() name={name} -> {result}")
    return result

def copy_file(src, dst):
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    
    original_dst = dst
    counter = 1
    while True:
        try:
            shutil.copy(src, dst)
            logger.debug(f"copy_file() copied {src} to {dst}")
            return True
        except FileExistsError:
            name, ext = os.path.splitext(original_dst)
            dst = f"{name}_{counter}{ext}"
            logger.debug(f"copy_file() FileExistsError: new dst={dst}")
            counter += 1
        except Exception as e:
            logger.error(f"Failed to copy {src} to {dst}: {e}")
            logger.debug(f"copy_file() Exception: {e}")
            return False

def move_file(src, dst):
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    
    original_dst = dst
    counter = 1
    while True:
        try:
            shutil.move(src, dst)
            logger.debug(f"move_file() moved {src} to {dst}")
            return True
        except FileExistsError:
            name, ext = os.path.splitext(original_dst)
            dst = f"{name}_{counter}{ext}"
            logger.debug(f"move_file() FileExistsError: new dst={dst}")
            counter += 1
        except Exception as e:
            logger.error(f"Failed to move {src} to {dst}: {e}")
            logger.debug(f"move_file() Exception: {e}")
            return False

def create_file(path):
    try:
        with open(path, "w"):
            pass
        logger.debug(f"create_file() created file at {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create file {path}: {e}")
        logger.debug(f"create_file() Exception: {e}")
        return False

def get_url(*parts):
    # Flatten lists/tuples in parts
    flattened_parts = []
    for part in parts:
        if isinstance(part, (list, tuple)):
            flattened_parts.extend(part)
        else:
            flattened_parts.append(part)

    # Join the parts, ensuring that the slashes are handled correctly
    url = ""
    for part in flattened_parts:
        if url:
            url = urllib.parse.urljoin(url + '/', part)
        else:
            url = part

    logger.debug(f"get_url() parts={flattened_parts} -> {url}")
    return url

def try_url(input, expected: int = 200, redirect: bool = False):
    try:
        response = requests.head(input, timeout=30, allow_redirects=redirect)
        logger.debug(f"{input} responded with {response.status_code}")
        return response.status_code == expected
    except requests.RequestException:
        logger.debug(f"try_url() RequestException for {input}")
        return False

def request_url(url: str, params: dict = None, method: str = "GET", timeout: int = 30):
    """
    Make a request to a URL with optional parameters and method.
    :param url: The URL to request.
    :param params: Optional dictionary of query parameters.
    :param method: HTTP method to use (GET or POST).
    :param timeout: Timeout for the request in seconds.
    :return: Response object from the request.
    """
    try:
        if method.upper() == "POST":
            logger.debug(f"request_url() POST url={url}, params={params}, timeout={timeout}")
            response = requests.post(url, data=params, timeout=timeout)
        else:
            logger.debug(f"request_url() GET url={url}, params={params}, timeout={timeout}")
            response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()  # Raise an error for bad responses
        logger.debug(f"request_url() response status={response.status_code}")
        return response
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        logger.debug(f"request_url() RequestException: {e}")
        return None

def try_path(input):
    result = os.path.exists(input)
    logger.debug(f"try_path() input={input} -> {result}")
    return result

def convert_to_file_url(local_path):
    # Replace backslashes with forward slashes
    local_path = local_path.replace("\\", "/")
    
    # Encode the path for URL compatibility
    encoded_path = urllib.parse.quote(local_path)
    
    # Prepend 'file://' to indicate it's a local file
    result = f"file:///{encoded_path}"
    logger.debug(f"convert_to_file_url() local_path={local_path} -> {result}")
    return result

def try_command(*input, return_output: bool = False):
    """
    Try to run a command in the shell and return the output or success status.
    If return_output is True, returns the command output as a string.
    :param input: Command and arguments to run.
    :param return_output: If True, returns the command output as a string.
    :return: True if command succeeded, False if it failed, or the output string if return_output is True.
    :raises subprocess.CalledProcessError: If the command fails and check=True is set.
    :raises Exception: For any other unexpected errors.
    """
    try:
        logger.debug(f"try_command() called with input={input}, return_output={return_output}")
        result = subprocess.run(args=input, shell=True, capture_output=True, text=True, check=True)
        logger.debug("Command succeeded: %s", result.stdout)
        return result.stdout.strip() if return_output else True
    except subprocess.CalledProcessError as e:
        logger.error("Error occurred: %s", e)
        logger.error("stderr: %s", e.stderr)  # Optional: Log stderr if needed
        logger.debug(f"try_command() CalledProcessError: returncode={e.returncode}, cmd={e.cmd}, output={e.output}, stderr={e.stderr}")
        return False
    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)
        logger.debug(f"try_command() Exception: {e}")
        return False

# Convert a list to a tuple
def flatten_list(input):
    result = tuple([str(i) for i in input])
    logger.debug(f"flatten_list() input={input} -> {result}")
    return result

def show_popup(title: str, message: str, type: int = 0):
    # Suppress the popup if no input is enabled
    if not parameters.get_param("no_input"):
        if os_is_windows():
            logger.debug(f"show_popup() Windows: title={title}, message={message}, type={type}")
            ctypes.windll.user32.MessageBoxW(None, message, title, type)
        elif os_is_linux():
            logger.debug(f"show_popup() Linux: title={title}, message={message}")
            subprocess.run(["zenity", "--info", "--title", title, "--text", message])
        else:
            logger.debug(f"show_popup() unsupported OS: title={title}, message={message}")
            logger.error("Unsupported OS")

# (Super precise) Timestamp generator in milliseconds unix time
def get_timestamp(msg: str = None):
    timestamp = time.time_ns() // 1_000_000
    logger.debug(f"Generated timestamp: {timestamp} ms" + (f" ({msg})" if msg else ""))
    return timestamp

# Wait for a certain amount of time
def wait(seconds: float, reason: str = None):
    logger.debug(f"wait() sleeping for {seconds} seconds" + (f" (reason: {reason})" if reason else ""))
    time.sleep(seconds)

def wait_for(expected: any, input: any, func: callable, reason: str = None, loop_speed: float = 0, timeout: float|None = None):
    """
    Waits until the function 'func' returns a value equal to 'expected'.
    Keeps calling 'func' and sleeping until the value matches.
    :param expected: The value to wait for.
    :param input: The initial value to compare.
    :param func: The function to call to get the new value.
    :param reason: Optional reason for waiting (for logging).
    :param loop_speed: How fast to poll the function (in seconds).
    :param timeout: Maximum time to wait in seconds (None for infinite).
    """
    start_time = time.time()
    while input != expected:
        if timeout is not None and (time.time() - start_time) >= timeout:
            logger.warning(f"wait_for() timed out after {timeout} seconds" + (f" (reason: {reason})" if reason else ""))
            return None
        wait(loop_speed, reason)
        input = func()
    return input

# Convert milliseconds to seconds
def ms_to_s(ms):
    result = ms / 1000
    logger.debug(f"ms_to_s() ms={ms} -> {result}")
    return result

# Send a post request
def post_request(url: str, data: dict):
    logger.debug(f"post_request() url={url}, data={data}")
    response = requests.post(url, data=data)
    logger.debug(f"post_request() response status={response.status_code}")
    return response

# Check if a resolution exceeds the monitor resolution
def exceeds_monitor_resolution(width, height):
    monitor_width, monitor_height = get_resolution()
    logger.debug(f"exceeds_monitor_resolution() width={width}, height={height}, monitor_width={monitor_width}, monitor_height={monitor_height}")
    if width > monitor_width or height > monitor_height:
        logger.debug("Resolution exceeds monitor size.")
        return True
    logger.debug("Resolution does not exceed monitor size.")
    return False

# Convert string to filename safe string
def to_filename_safe(string):
    result = "".join([c for c in string if c.isalpha() or c.isdigit() or c in [" ", "-", "_", "."]]).rstrip()
    logger.debug(f"to_filename_safe() string={string} -> {result}")
    return result

# Check if a DLL is loadable
def is_dll_loadable(dll_path):
    try:
        ctypes.WinDLL(dll_path)
        logger.debug(f"is_dll_loadable() DLL loaded successfully: {dll_path}")
        return True  # DLL loaded successfully
    except OSError:
        logger.debug(f"is_dll_loadable() DLL not loadable: {dll_path}")
        return False  # DLL not found or not registered

# Output a list of items to the console
def print_list(items, message: str = "to select"):
    if not isinstance(items, list):
        raise ValueError("Input must be a list.")
    logger.debug(f"print_list() items={items}, message={message}")
    for index, item in enumerate(items, start=1):
        print(f"[bold blue]Option #{index}:[/bold blue] type \"{item}\"" + (f" ({message})" if message else ""))

# Text to speech
def say(text: str):
    """Convert text to speech at normal speed."""
    logger.debug(f"say() called with text={text}")
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

# Checks if the application has an update available
def has_update():
    logger.info("Checking for updates...")
    logger.debug("has_update() always returns False (stub)")
    return False