#!/usr/bin/env python3
"""
GUI Test script to verify console functionality works in the actual GUI
"""

import sys
import os
from PyQt6.QtWidgets import QApplication

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from modules.logger import logger
from modules.flow import Controller
from modules.update import Update
from modules.window import Window

def main():
    app = QApplication(sys.argv)
    
    # Create a minimal controller and update for testing
    try:
        controller = Controller()
        update = Update()
        
        # Create the window
        window = Window(controller, update)
        window.show()
        
        # Test some log messages after the window is shown
        logger.info("GUI Console test started")
        logger.info("User chose 16:9")
        logger.warning("This is a warning message")
        logger.error("This is an error message")
        logger.info("Testing console widget functionality")
        logger.info("All tests completed successfully")
        
        # Keep the window open
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"Error running GUI test: {e}")
        return 1

if __name__ == "__main__":
    main()