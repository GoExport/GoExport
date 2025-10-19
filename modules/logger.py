import config
import logging
import os
import sys
import time
import traceback
from modules import parameters
from rich.logging import RichHandler

# --- Utility functions ---

def _is_frozen():
    return getattr(sys, 'frozen', False)

def _get_app_folder():
    if _is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# --- Logging setup ---

APP_DIR = _get_app_folder()
LOG_DIR = os.path.join(APP_DIR, "logs", time.strftime("%Y-%m-%d"))
os.makedirs(LOG_DIR, exist_ok=True)

timestamp = f"{time.strftime('%H-%M-%S')}-{int(time.time() * 1000) % 1000}"
log_file = os.path.join(LOG_DIR, f"{timestamp}.log")

logging.basicConfig(
    level=logging.DEBUG if parameters.Parameters().verbose or config.DEBUG_MODE else logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(),
        logging.FileHandler(log_file, encoding="utf-8")
    ]
)

logger = logging.getLogger("rich_logger")

# --- Exception handling ---

def log_exception(exc_type, exc_value, exc_tb):
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.error(f"Exception occurred:\n{tb_str}")

    # Avoid import loops by loading helpers here if needed
    try:
        import helpers
        helpers.show_popup("Exception occurred", tb_str, 16)
    except Exception:
        logger.error("Failed to show popup or import helpers.", exc_info=True)

sys.excepthook = log_exception
