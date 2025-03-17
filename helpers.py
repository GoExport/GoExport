import shutil
import config
import os
import sys
import ctypes
import urllib3, urllib
import pyautogui
import subprocess
import time
import requests
from modules.logger import logger
from datetime import datetime
from datetime import timedelta

def os_is_windows():
    return sys.platform.startswith("win")

def os_is_linux():
    return sys.platform.startswith("linux")

def os_is_mac():
    return sys.platform.startswith("darwin")

def is_frozen():
    return getattr(sys, 'frozen', False)

def move_mouse_offscreen():
    width, height = pyautogui.size()
    pyautogui.moveTo(width, height)

def get_python_path():
    return sys.executable

def get_sep():
    return os.sep

def generate_path():
    return f"{datetime.now().strftime('%Y-%m-%d %H-%M-%S')}"

def make_dir(path):
    original_path = path
    counter = 1
    while True:
        try:
            os.makedirs(path)
            return True
        except FileExistsError:
            logger.warning(f"Directory {path} already exists.")
            path = f"{original_path}_{counter}"
            counter += 1
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False
    
def open_folder(path):
    """Open a folder in the file system and bring it to the foreground."""
    try:
        if os_is_windows():
            subprocess.Popen(['explorer', path])
            return True
        elif os_is_linux():
            subprocess.run(["xdg-open", path])
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Failed to open folder {path}: {e}")
        return False

def get_cwd():
    """Get the current working directory, adjusted for PyInstaller."""
    return os.getcwd()

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

    return os.path.join(cwd, *flattened_parts)

def get_user_folder(folder: str):
    if os_is_windows():
        return os.path.join(os.environ["USERPROFILE"], folder)
    elif os_is_linux():
        return os.path.join(os.path.expanduser("~"), folder)
    else:
        return None

def get_config(variable: str):
    return getattr(config, variable, None)

def get_resolution(index: int = 0):
    from screeninfo import get_monitors
    monitor = get_monitors()[index]
    return (monitor.width, monitor.height)

def compare_monitor_resolution(width, height):
    monitor_width, monitor_height = get_resolution()
    return width <= monitor_width and height <= monitor_height

def copy_file(src, dst):
    original_dst = dst
    counter = 1
    while True:
        try:
            shutil.copy(src, dst)
            return True
        except FileExistsError:
            name, ext = os.path.splitext(original_dst)
            dst = f"{name}_{counter}{ext}"
            counter += 1
        except Exception as e:
            logger.error(f"Failed to copy {src} to {dst}: {e}")
            return False

def move_file(src, dst):
    original_dst = dst
    counter = 1
    while True:
        try:
            shutil.move(src, dst)
            return True
        except FileExistsError:
            name, ext = os.path.splitext(original_dst)
            dst = f"{name}_{counter}{ext}"
            counter += 1
        except Exception as e:
            logger.error(f"Failed to move {src} to {dst}: {e}")
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

    return url

def try_url(input, expected: int = 200, redirect: bool = False):
    try:
        response = requests.head(input, timeout=30, allow_redirects=redirect)
        logger.debug(f"{input} responded with {response.status_code}")
        return response.status_code == expected
    except requests.RequestException:
        return False

def try_path(input):
    return os.path.exists(input)

def convert_to_file_url(local_path):
    # Replace backslashes with forward slashes
    local_path = local_path.replace("\\", "/")
    
    # Encode the path for URL compatibility
    encoded_path = urllib.parse.quote(local_path)
    
    # Prepend 'file://' to indicate it's a local file
    return f"file:///{encoded_path}"

def try_command(*input):
    try:
        result = subprocess.run(args=input, shell=True, capture_output=True, text=True, check=True)
        logger.debug("Command succeeded: %s", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error("Error occurred: %s", e)
        logger.error("stderr: %s", e.stderr)  # Optional: Log stderr if needed
        return False
    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)
        return False

# (Super precise) Timestamp generator in milliseconds unix time
def get_timestamp(msg: str = None):
    timestamp = time.time_ns() // 1_000_000
    logger.debug(f"Generated timestamp: {timestamp} ms" + (f" ({msg})" if msg else ""))
    return timestamp

# Convert milliseconds to seconds
def ms_to_s(ms):
    return ms / 1000

# Send a post request
def post_request(url: str, data: dict):
    response = requests.post(url, data=data)
    return response

# Convert string to filename safe string
def to_filename_safe(string):
    return "".join([c for c in string if c.isalpha() or c.isdigit() or c in [" ", "-", "_", "."]]).rstrip()