import config
import os
import sys
import ctypes
import urllib3, urllib
import pyautogui
import subprocess
import time
import xmltodict
import requests
from modules.logger import logger
from datetime import datetime
from datetime import timedelta

def get_python_path():
    return sys.executable

def get_sep():
    return os.sep

def generate_path():
    return f"{datetime.now().strftime('%Y-%m-%d %H-%M-%S')}"

def get_cwd():
    """Get the current working directory, adjusted for PyInstaller."""
    if getattr(sys, 'frozen', False):  # Running as a PyInstaller EXE
        return sys._MEIPASS
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
    if os.name == "nt":
        return os.path.join(os.environ["USERPROFILE"], folder)
    elif os.name == "posix":
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

# (Super precise) Timestamp generator
def get_timestamp(msg: str = None):
    timestamp = time.time_ns() // 1_000_000
    print(f"Generated timestamp: {timestamp}" + (f" ({msg})" if msg else ""))
    return timestamp

# Convert milliseconds to seconds
def ms_to_s(ms):
    return ms / 1000

# Send a post request
def post_request(url: str, data: dict):
    response = requests.post(url, data=data)
    return response

# Convert XML to Dict
def xml_to_dict(xml):
    return xmltodict.parse(xml)

# Send a post request and convert the response to a dict
def post_request_to_dict(url: str, data: dict):
    response = post_request(url, data)
    return xml_to_dict(response.text)

# Convert string to filename safe string
def to_filename_safe(string):
    return "".join([c for c in string if c.isalpha() or c.isdigit() or c in [" ", "-", "_", "."]]).rstrip()