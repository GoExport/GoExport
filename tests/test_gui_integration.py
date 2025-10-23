#!/usr/bin/env python3
"""
Test script to demonstrate the improved GUI integration with Controller methods.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import helpers
from modules.flow import Controller
from modules.logger import logger

def test_gui_integration():
    """Test how GUI should integrate with the improved Controller methods"""
    
    print("Testing GUI integration with improved Controller methods...")
    controller = Controller()
    
    # Test 1: Valid inputs (success case)
    print("\n=== Test 1: Valid inputs ===")
    try:
        success = controller.set_aspect_ratio("16:9")
        print(f"Set aspect ratio '16:9': {success}")
        
        success = controller.set_resolution("720p")
        print(f"Set resolution '720p': {success}")
        
        success = controller.set_auto_edit(True)
        print(f"Set auto edit to True: {success}")
        
    except ValueError as e:
        print(f"Validation error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    # Test 2: Invalid inputs (error case)
    print("\n=== Test 2: Invalid inputs ===")
    try:
        success = controller.set_aspect_ratio("invalid_ratio")
        print(f"Set invalid aspect ratio: {success}")
    except ValueError as e:
        print(f"Expected validation error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    # Test 3: Empty/None inputs (should not crash)
    print("\n=== Test 3: Empty/None inputs ===")
    try:
        success = controller.set_movie_id(None)
        print(f"Set movie ID to None: {success}")
        
        success = controller.set_movie_id("")
        print(f"Set movie ID to empty string: {success}")
        
        success = controller.set_owner_id(None)
        print(f"Set owner ID to None: {success}")
        
        success = controller.set_owner_id(0)
        print(f"Set owner ID to 0: {success}")
        
    except Exception as e:
        print(f"Error with empty inputs: {e}")
    
    # Test 4: Service that requires IDs
    print("\n=== Test 4: Service requiring IDs ===")
    try:
        # First set a service that requires movieId and movieOwnerId
        # Note: This assumes there's a service in config that requires these
        available_services = helpers.get_config("AVAILABLE_SERVICES")
        service_with_requirements = None
        
        for service_id, service_data in available_services.items():
            if service_data.get("requires", []):
                service_with_requirements = service_id
                break
        
        if service_with_requirements:
            success = controller.set_lvm(service_with_requirements)
            print(f"Set service '{service_with_requirements}': {success}")
            print(f"Service requirements: {controller.svr_required}")
            
            # Test setting required IDs
            if 'movieId' in controller.svr_required:
                success = controller.set_movie_id("test123")
                print(f"Set movie ID 'test123': {success}")
            
            if 'movieOwnerId' in controller.svr_required:
                success = controller.set_owner_id(12345)
                print(f"Set owner ID 12345: {success}")
        else:
            print("No services with requirements found in config")
            
    except Exception as e:
        print(f"Error testing service requirements: {e}")

def demonstrate_proper_gui_usage():
    """Show the proper way to use these methods in GUI event handlers"""
    
    print("\n" + "="*60)
    print("PROPER GUI USAGE PATTERNS:")
    print("="*60)
    
    print("""
# Instead of this (old way):
def on_movie_id_changed(self):
    text = self.ui.VideoId.text().strip()
    self.controller.set_movie_id(text)  # No error checking!

# Do this (new way):
def on_movie_id_changed(self):
    text = self.ui.VideoId.text().strip()
    if text:  # Only try to set if there's actual text
        try:
            if not self.controller.set_movie_id(text):
                QMessageBox.critical(self, "Error", "Failed to set movie ID")
                return
            logger.info(f"Movie ID set to: {text}")
        except ValueError as e:
            QMessageBox.critical(self, "Error", str(e))
            logger.error(f"Invalid movie ID: {e}")

# For validation before export:
def verify_inputs(self):
    # Check if movieId is required
    if 'movieId' in self.controller.svr_required:
        movie_id = self.ui.VideoId.text().strip()
        if not movie_id:
            QMessageBox.critical(self, "Error", "Movie ID is required")
            return False
        try:
            if not self.controller.set_movie_id(movie_id):
                QMessageBox.critical(self, "Error", "Failed to set movie ID")
                return False
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Invalid movie ID: {e}")
            return False
    return True
""")

if __name__ == "__main__":
    test_gui_integration()
    demonstrate_proper_gui_usage()