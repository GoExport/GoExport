import json
import string
import config
import shutil
import os
import sys
import platform
import psutil
import ctypes
import urllib
import subprocess
import time
import requests
import shlex
from rich import print
from typing import Any, Callable
from modules.logger import logger
from datetime import datetime
import modules.parameters as parameters

# Global variables - use singleton to avoid duplicate parameter prints
parameters = parameters.get_parameters()

# Function to grab the key and value of a parameter
def get_param(key: str):
    value = getattr(parameters, key, None)
    logger.debug(f"get_param() key={key} -> {value}")
    return value

# Function to set the value of a parameter
def set_param(key: str, value):
    setattr(parameters, key, value)
    logger.debug(f"set_param() key={key}, value={value}")

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
                return data.get(key, default)
            except json.JSONDecodeError:
                logger.info(f"JSON decode error in {data_file_path}, returning default value.")
                return default
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

def has_console():
    """Check whether the process has a console window attached or --console flag is set."""
    # If --console flag is set, always return True to force console mode
    if get_param("console"):
        return True
    
    if not is_frozen() and get_config("FORCE_WINDOW"):
        return False
    
    if os_is_windows():
        try:
            return bool(ctypes.windll.kernel32.GetConsoleWindow())
        except Exception:
            return False
    elif os_is_linux() or os_is_mac():
        # Check if any of stdin/stdout/stderr is a TTY
        return sys.stdin.isatty() or sys.stdout.isatty() or sys.stderr.isatty()
    else:
        return False

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
            create_logged_popen(['explorer', path], process_name="explorer", log_output=False)
            return True
        elif os_is_linux():
            logger.debug(f"open_folder() using Linux file manager for path={path}")
            
            # Try multiple file managers in order of preference
            file_managers = [
                "nautilus",      # GNOME Files
                "dolphin",       # KDE Dolphin
                "thunar",        # XFCE
                "pcmanfm",       # LXDE/LXQt
                "nemo",          # Cinnamon
                "caja",          # MATE
                "xdg-open"       # Fallback to xdg-open
            ]
            
            for fm in file_managers:
                try:
                    # Check if the file manager exists
                    create_logged_run(["which", fm], process_name="which", 
                                check=True, capture_output=True, timeout=5)
                    
                    # Try to open the folder
                    result = create_logged_run([fm, path], process_name=fm,
                                        capture_output=True, timeout=10, log_output=False)
                    
                    if result.returncode == 0:
                        logger.debug(f"Successfully opened folder with {fm}")
                        return True
                    else:
                        logger.debug(f"{fm} failed with return code {result.returncode}")
                        
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                    logger.debug(f"{fm} not available or failed: {e}")
                    continue
            
            # If all file managers fail, try a direct approach
            logger.warning("All file managers failed, trying fallback methods")
            return False
        else:
            logger.debug(f"open_folder() unsupported OS for path={path}")
            return False
    except Exception as e:
        logger.error(f"Failed to open folder {path}: {e}")
        logger.debug(f"open_folder() Exception: {e}")
        return False

def is_frozen():
    return getattr(sys, "frozen", False)

def get_app_folder():
    """Return the directory where the app's executable or main script resides."""
    if is_frozen():
        path = os.path.dirname(sys.executable)
        logger.debug(f"get_app_folder() [frozen]: {path}")
        return path
    else:
        # __file__ is the script location, independent of cwd
        path = os.path.dirname(os.path.abspath(__file__))
        logger.debug(f"get_app_folder() [not frozen]: {path}")
        return path

def get_cwd():
    if is_frozen():
        # In PyInstaller, sys._MEIPASS points to the temp folder containing bundled files
        path = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        logger.debug(f"get_cwd() [frozen]: {path}")
    else:
        path = os.getcwd()
        logger.debug(f"get_cwd() [not frozen]: {path}")
    return path

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

def try_url(input, timeout: int = 5):
    """
    Check if a website is active and online.
    Returns (True, status_code) if the site is reachable (status code 200-399), (False, status_code or None) otherwise.
    Adds common headers: Accept, Accept-Language, Referer, Connection.
    """
    headers = {
        "User-Agent": "GoExportStatusChecker/1.0 (+http://goexport.lexian.dev/status.html)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }
    try:
        response = requests.get(input, timeout=timeout, headers=headers)
        logger.debug(f"try_url() {input} responded with {response.status_code}")
        if 200 <= response.status_code < 400:
            return True, response.status_code
        else:
            return False, response.status_code
    except requests.RequestException as e:
        logger.debug(f"try_url() RequestException for {input}: {e}")
        return False, None

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

def create_logged_popen(args, process_name=None, log_output=True, **kwargs):
    """
    Create a subprocess.Popen instance that logs all output to a separate file.
    
    :param args: Command and arguments to run (same as subprocess.Popen).
    :param process_name: Name for the log file. If None, derived from the command.
    :param log_output: Whether to log output to a file. If False, behaves like normal Popen.
    :param kwargs: Additional keyword arguments to pass to subprocess.Popen.
    :return: A subprocess.Popen instance with a logging thread attached.
    """
    import threading
    
    # Determine process name for log file
    if process_name is None:
        if isinstance(args, (list, tuple)) and len(args) > 0:
            process_name = os.path.basename(str(args[0])).replace('.exe', '').replace('.py', '')
        else:
            process_name = "process"
    
    process_name = to_filename_safe(process_name)
    
    # Create log directory following logger.py conventions
    app_dir = get_app_folder()
    log_dir = os.path.join(app_dir, "logs", time.strftime("%Y-%m-%d"))
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate timestamp and log filename
    timestamp = f"{time.strftime('%H-%M-%S')}-{int(time.time() * 1000) % 1000}"
    log_file = os.path.join(log_dir, f"{process_name}_{timestamp}.log")
    
    logger.debug(f"create_logged_popen() process_name={process_name}, log_file={log_file}")
    
    if not log_output:
        # If logging is disabled, create a normal Popen
        return subprocess.Popen(args, **kwargs)
    
    # Ensure stdout and stderr are captured if not explicitly set
    if 'stdout' not in kwargs:
        kwargs['stdout'] = subprocess.PIPE
    if 'stderr' not in kwargs:
        kwargs['stderr'] = subprocess.STDOUT
    if 'universal_newlines' not in kwargs:
        kwargs['universal_newlines'] = True
    if 'bufsize' not in kwargs:
        kwargs['bufsize'] = 1  # Line buffered
    
    # Create the process
    process = subprocess.Popen(args, **kwargs)
    
    # Create a thread to log output
    def log_output_thread():
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Process: {' '.join(str(a) for a in (args if isinstance(args, (list, tuple)) else [args]))}\n")
                f.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"PID: {process.pid}\n")
                f.write("-" * 80 + "\n\n")
                f.flush()
                
                if process.stdout:
                    for line in process.stdout:
                        f.write(line)
                        f.flush()
                
                f.write("\n" + "-" * 80 + "\n")
                f.write(f"Ended: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Return code: {process.returncode}\n")
        except Exception as e:
            logger.error(f"Error in logging thread for {process_name}: {e}")
    
    # Start the logging thread
    log_thread = threading.Thread(target=log_output_thread, daemon=True)
    log_thread.start()
    
    # Attach the thread to the process object for potential cleanup
    process._log_thread = log_thread
    process._log_file = log_file
    
    logger.info(f"Started logged process '{process_name}' (PID: {process.pid}), logging to: {log_file}")
    
    return process

def create_logged_run(args, process_name=None, log_output=True, **kwargs):
    """
    Run a subprocess command and log all output to a separate file.
    
    :param args: Command and arguments to run (same as subprocess.run).
    :param process_name: Name for the log file. If None, derived from the command.
    :param log_output: Whether to log output to a file. If False, behaves like normal run.
    :param kwargs: Additional keyword arguments to pass to subprocess.run.
    :return: A subprocess.CompletedProcess instance.
    """
    # Determine process name for log file
    if process_name is None:
        if isinstance(args, (list, tuple)) and len(args) > 0:
            process_name = os.path.basename(str(args[0])).replace('.exe', '').replace('.py', '')
        else:
            process_name = "process"
    
    process_name = to_filename_safe(process_name)
    
    # Create log directory following logger.py conventions
    app_dir = get_app_folder()
    log_dir = os.path.join(app_dir, "logs", time.strftime("%Y-%m-%d"))
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate timestamp and log filename
    timestamp = f"{time.strftime('%H-%M-%S')}-{int(time.time() * 1000) % 1000}"
    log_file = os.path.join(log_dir, f"{process_name}_{timestamp}.log")
    
    logger.debug(f"create_logged_run() process_name={process_name}, log_file={log_file}")
    
    if not log_output:
        # If logging is disabled, run normally
        return subprocess.run(args, **kwargs)
    
    # Ensure stdout and stderr are captured
    if 'capture_output' not in kwargs:
        if 'stdout' not in kwargs:
            kwargs['stdout'] = subprocess.PIPE
        if 'stderr' not in kwargs:
            kwargs['stderr'] = subprocess.PIPE
    
    if 'text' not in kwargs and 'universal_newlines' not in kwargs:
        kwargs['text'] = True
    
    # Run the process
    start_time = time.strftime('%Y-%m-%d %H:%M:%S')
    result = subprocess.run(args, **kwargs)
    end_time = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # Write output to log file
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Process: {' '.join(str(a) for a in (args if isinstance(args, (list, tuple)) else [args]))}\n")
            f.write(f"Started: {start_time}\n")
            f.write(f"Ended: {end_time}\n")
            f.write(f"Return code: {result.returncode}\n")
            f.write("-" * 80 + "\n\n")
            
            if result.stdout:
                f.write("STDOUT:\n")
                f.write(result.stdout)
                f.write("\n")
            
            if result.stderr:
                f.write("\nSTDERR:\n")
                f.write(result.stderr)
                f.write("\n")
            
            f.write("-" * 80 + "\n")
        
        logger.info(f"Logged process '{process_name}' output to: {log_file}")
    except Exception as e:
        logger.error(f"Error writing log file for {process_name}: {e}")
    
    return result

def run_and_detach(*input):
    """
    Run a command in the background and detach it from the terminal.
    """
    try:
        # Determine process name from input
        process_name = None
        if len(input) > 0:
            process_name = os.path.basename(str(input[0])).replace('.exe', '').replace('.py', '')
        
        create_logged_popen(args=input, process_name=process_name, log_output=False)
        logger.debug(f"Detached process started: {input}")
        return True
    except Exception as e:
        logger.error(f"Failed to start detached process: {e}")
        return False

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
        
        # Determine process name from input
        process_name = None
        if len(input) > 0:
            process_name = os.path.basename(str(input[0])).replace('.exe', '').replace('.py', '')
        
        result = create_logged_run(
            args=input, 
            process_name=process_name,
            capture_output=True, 
            check=True, 
            creationflags=subprocess.CREATE_NO_WINDOW if os_is_windows() else 0
        )
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

def is_running(path: str):
    """Check if a process is running by its executable path."""
    try:
        for proc in psutil.process_iter(attrs=["pid", "name", "exe"]):
            exe = proc.info.get("exe")
            if exe and os.path.normcase(os.path.abspath(exe)) == os.path.normcase(os.path.abspath(path)):
                logger.debug(f"is_running() found process: {proc.info}")
                return True
    except Exception as e:
        logger.error(f"Failed to check if process is running: {e}")
    return False

# Convert a list to a tuple
def flatten_list(input):
    result = tuple([str(i) for i in input])
    logger.debug(f"flatten_list() input={input} -> {result}")
    return result

def show_popup(title: str, message: str, type: int = 0):
    # Suppress the popup if no input is enabled
    if not get_param("no_input"):
        # If running in console mode, output to console instead
        if has_console():
            logger.info(f"{title}: {message}")
            return
        
        if os_is_windows():
            logger.debug(f"show_popup() Windows: title={title}, message={message}, type={type}")
            ctypes.windll.user32.MessageBoxW(None, message, title, type)
        elif os_is_linux():
            logger.debug(f"show_popup() Linux: title={title}, message={message}")
            result = create_logged_run(["zenity", "--info", "--title", title, "--text", message], 
                            process_name="zenity", log_output=False)
            # If zenity fails, fall back to console output
            if result.returncode != 0:
                logger.debug(f"show_popup() zenity failed (return code {result.returncode}), falling back to console")
                logger.info(f"{title}: {message}")
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

def wait_for(expected: Any, func: Callable[[], Any], reason: str = None, loop_speed: float = 0.1, timeout: float | None = None) -> Any | None:
    """
    Wait until func() returns `expected`, polling periodically.
    
    :param expected: The value to wait for.
    :param func: A no-argument function returning the current value.
    :param reason: Optional reason for waiting (for logging).
    :param loop_speed: How often to poll (seconds).
    :param timeout: Max time to wait (None for infinite).
    :return: The value if matched, or None if timed out.
    """
    start_time = time.time()

    while True:
        value = func()
        if value == expected:
            return value
        if timeout is not None and (time.time() - start_time) >= timeout:
            logger.warning(f"wait_for() timed out after {timeout} seconds" + (f" (reason: {reason})" if reason else ""))
            return None
        time.sleep(loop_speed)

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
def exceeds_monitor_resolution(width, height, monitor_index: int = 0):
    monitor_width, monitor_height = get_resolution(monitor_index)
    logger.debug(f"exceeds_monitor_resolution() width={width}, height={height}, monitor_index={monitor_index}, monitor_width={monitor_width}, monitor_height={monitor_height}")
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

def encode_video(input_path: str, output_path: str, width: int = None, height: int = None, crf: int = 23, preset: str = "medium"):
    """
    Encode a video file using FFmpeg with optimal settings for quality and compatibility.
    This function is designed to be called after raw video capture to produce the final output.
    
    :param input_path: Path to the input video file (raw capture).
    :param output_path: Path to the output video file (encoded).
    :param width: Optional width for cropping/scaling. If None, uses input dimensions.
    :param height: Optional height for cropping/scaling. If None, uses input dimensions.
    :param crf: Constant Rate Factor for quality (0-51, lower is better, 23 is default).
    :param preset: Encoding preset (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow).
    :return: True if encoding succeeded, False otherwise.
    """
    try:
        logger.info(f"Starting video encoding: {input_path} -> {output_path}")
        
        # Check for command override first
        ffmpeg_encode_override = get_param("ffmpeg_encode_override")
        
        if ffmpeg_encode_override:
            # User provided a complete override command
            logger.info("Using FFmpeg encode override command")
            # Parse the override string into a list, replacing placeholders if present
            command = shlex.split(ffmpeg_encode_override)
            # Replace {input} and {output} placeholders with actual paths
            command = [arg.replace("{input}", input_path).replace("{output}", output_path) for arg in command]
        else:
            # Build FFmpeg command
            if os_is_windows():
                ffmpeg_path = get_path(get_app_folder(), get_config("PATH_FFMPEG_WINDOWS"))
            elif os_is_linux():
                ffmpeg_path = get_path(get_app_folder(), get_config("PATH_FFMPEG_LINUX"))
            else:
                logger.error("Unsupported OS for video encoding")
                return False
            
            command = [
                ffmpeg_path, "-y",
                "-i", input_path,
            ]
            
            # Add video filters if dimensions are specified
            if width and height:
                command.extend(["-vf", f"crop={width}:{height}:0:0,format=yuv420p"])
            else:
                command.extend(["-vf", "format=yuv420p"])
            
            # Add encoding parameters
            command.extend([
                "-c:v", "libx264",
                "-preset", preset,
                "-crf", str(crf),
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",
            ])
            
            # Add custom arguments if provided
            ffmpeg_encode_args = get_param("ffmpeg_encode_args")
            if ffmpeg_encode_args:
                logger.info(f"Adding custom encode FFmpeg arguments: {ffmpeg_encode_args}")
                custom_args = shlex.split(ffmpeg_encode_args)
                command.extend(custom_args)
            
            # Add output file at the end
            command.append(output_path)
        
        logger.debug(f"encode_video() command: {' '.join(command)}")
        
        # Run encoding process
        result = create_logged_run(
            command,
            process_name="ffmpeg_encode",
            cwd=get_cwd(),
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os_is_windows() else 0,
        )
        
        if result.returncode == 0:
            logger.info(f"Video encoding completed successfully: {output_path}")
            return True
        else:
            logger.error(f"Video encoding failed with return code {result.returncode}")
            logger.error(f"FFmpeg stderr: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error encoding video: {e}")
        return False

# Output a list of items to the console
def print_list(items, message: str = "to select"):
    if not isinstance(items, list):
        raise ValueError("Input must be a list.")
    logger.debug(f"print_list() items={items}, message={message}")
    for index, item in enumerate(items, start=1):
        print(f"[bold blue]Option #{index}:[/bold blue] type \"{item}\"" + (f" ({message})" if message else ""))

# Checks if the application has an update available
def has_update():
    logger.info("Checking for updates...")
    logger.debug("has_update() always returns False (stub)")
    return False