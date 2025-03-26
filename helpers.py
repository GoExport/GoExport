import shutil
import config
import os
import sys
import platform
import logging
import GPUtil
import psutil
import ctypes
import urllib3, urllib
import pyautogui
import subprocess
import time
import requests
from modules.logger import logger
from datetime import datetime
from datetime import timedelta
from pygrabber.dshow_graph import FilterGraph

def remember(key: str, value):
    setattr(remember, key, value)

def recall(key: str):
    return getattr(remember, key, None)

def forget(key: str):
    if hasattr(remember, key):
        delattr(remember, key)

def os_is_windows():
    return sys.platform.startswith("win")

def os_is_linux():
    return sys.platform.startswith("linux")

def os_is_mac():
    return sys.platform.startswith("darwin")

def is_frozen():
    return getattr(sys, 'frozen', False)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except AttributeError:
        return False

def get_arch():
    return platform.machine()

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
        "gpu": get_gpu_info(),
    }
    return specs

def get_gpu_info():
    gpus = GPUtil.getGPUs()
    gpu_info = []
    for gpu in gpus:
        gpu_info.append({
            "name": gpu.name,
            "vram_total": round(gpu.memoryTotal / 1024, 2),  # Convert MB to GB
            "vram_used": round(gpu.memoryUsed / 1024, 2),    # Convert MB to GB
            "vram_free": round(gpu.memoryFree / 1024, 2),    # Convert MB to GB
            "vram_util": round(gpu.memoryUtil * 100),        # Convert to percentage and round up
        })
    return gpu_info

def move_mouse_offscreen():
    pyautogui.FAILSAFE = False # All we're doing is moving the mouse offscreen
    width, height = pyautogui.size()
    pyautogui.moveTo(width, height)

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
    """Get the current working directory, using PyInstaller paths if applicable."""
    if is_frozen():
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
    if os_is_windows():
        return os.path.join(os.environ["USERPROFILE"], folder)
    elif os_is_linux():
        return os.path.join(os.path.expanduser("~"), folder)
    else:
        return None

def get_app_folder():
    if is_frozen():
        return os.path.dirname(sys.executable)
    else:
        return get_cwd()

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
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    
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
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    
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

def create_file(path):
    try:
        with open(path, "w"):
            pass
        return True
    except Exception as e:
        logger.error(f"Failed to create file {path}: {e}")
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

def list_directshow_devices():
    graph = FilterGraph()
    devices = graph.get_input_devices()
    audio_devices = graph.get_audio_devices()
    return devices, audio_devices

def find_directshow_device(device_name: str, is_audio: bool = False):
    graph = FilterGraph()
    if is_audio:
        devices = graph.get_audio_devices()
    else:
        devices = graph.get_input_devices()

    for idx, device in enumerate(devices):
        if device_name.lower() in device.lower():  # Case-insensitive search
            return idx, device

    return False

# (Super precise) Timestamp generator in milliseconds unix time
def get_timestamp(msg: str = None):
    timestamp = time.time_ns() // 1_000_000
    logger.debug(f"Generated timestamp: {timestamp} ms" + (f" ({msg})" if msg else ""))
    return timestamp

# Wait for a certain amount of time
def wait(seconds: float):
    time.sleep(seconds)

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

# Check if a DLL is loadable
def is_dll_loadable(dll_path):
    try:
        ctypes.WinDLL(dll_path)
        return True  # DLL loaded successfully
    except OSError:
        return False  # DLL not found or not registered