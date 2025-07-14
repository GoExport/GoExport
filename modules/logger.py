import helpers
import config
import logging
import os
import sys
import time
import traceback
from modules import parameters
from rich.logging import RichHandler

# Ensure the logs folder exists
os.makedirs(f"logs/{time.strftime('%Y-%m-%d')}", exist_ok=True)

# Configure logging
log_file = f"logs/{time.strftime('%Y-%m-%d')}/{time.strftime('%H-%M-%S')}-{int(time.time() * 1000) % 1000}.log"

# Set up logging to the terminal (RichHandler) and log file
logging.basicConfig(
    level=logging.DEBUG if parameters.Parameters().verbose or config.DEBUG_MODE else logging.INFO,
    format="%(message)s",  # Rich handles formatting itself
    datefmt="[%X]",
    handlers=[
        RichHandler(),  # Output to terminal
        logging.FileHandler(log_file)  # Output to log file
    ]
)

logger = logging.getLogger("rich_logger")

# Function to log tracebacks
def log_exception(exc_type, exc_value, exc_tb):
    # Create the traceback string
    tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    
    # Log the exception and traceback to both terminal and file
    logger.error(f"Exception occurred:\n{tb_str}")
    helpers.show_popup("Exception occurred", tb_str, 16)

# Set the custom exception hook to log uncaught exceptions
sys.excepthook = log_exception
