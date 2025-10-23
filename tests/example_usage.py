#!/usr/bin/env python3
"""
Example showing how to use the improved Controller methods in both GUI and CLI modes.
"""

from modules.flow import Controller
import helpers

def example_gui_usage():
    """Example of how a GUI would use the Controller methods"""
    controller = Controller()
    
    # GUI mode: Pass values directly from GUI controls
    try:
        # These would come from GUI dropdowns/inputs
        success = controller.set_aspect_ratio("16:9")
        if not success:
            print("Failed to set aspect ratio")
            return
            
        success = controller.set_resolution("1280x720")
        if not success:
            print("Failed to set resolution")
            return
            
        success = controller.set_lvm("wrapper")  # or whatever service
        if not success:
            print("Failed to set service")
            return
            
        success = controller.set_auto_edit(True)  # from GUI checkbox
        if not success:
            print("Failed to set auto edit")
            return
            
        # These would only be called if the service requires them
        if 'movieOwnerId' in controller.svr_required:
            success = controller.set_owner_id(12345)  # from GUI input field
            if not success:
                print("Failed to set owner ID")
                return
                
        if 'movieId' in controller.svr_required:
            success = controller.set_movie_id("abc123")  # from GUI input field
            if not success:
                print("Failed to set movie ID")
                return
                
        print("All settings configured successfully!")
        
    except ValueError as e:
        print(f"Invalid value provided: {e}")
    except Exception as e:
        print(f"Error: {e}")

def example_interactive_usage():
    """Example of how interactive mode works (when no values provided)"""
    controller = Controller()
    
    # Interactive mode: Let methods prompt the user
    try:
        # These will show lists and prompt for user input
        controller.set_aspect_ratio()  # Will show available options and prompt
        controller.set_resolution()    # Will show available options and prompt
        controller.set_lvm()          # Will show available options and prompt
        controller.set_auto_edit()    # Will ask yes/no question
        
        # These will only prompt if required by the selected service
        controller.set_owner_id()     # Will prompt if needed
        controller.set_movie_id()     # Will prompt if needed
        
        print("All settings configured successfully!")
        
    except ValueError as e:
        print(f"Invalid value: {e}")
    except Exception as e:
        print(f"Error: {e}")

def example_cli_usage():
    """Example of how CLI mode works (with --no-input flag)"""
    # This simulates having CLI parameters set
    # In real usage, these would come from command line arguments
    
    controller = Controller()
    
    # CLI mode: Values must be provided via parameters or it will fail
    try:
        # These use helpers.get_param() to get values from CLI args
        controller.set_aspect_ratio()  # Gets from --aspect-ratio
        controller.set_resolution()    # Gets from --resolution  
        controller.set_lvm()          # Gets from --service
        controller.set_auto_edit()    # Gets from --auto-edit or defaults to True
        controller.set_owner_id()     # Gets from --owner-id (fails if required but missing)
        controller.set_movie_id()     # Gets from --movie-id (fails if required but missing)
        
        print("All settings configured successfully!")
        
    except ValueError as e:
        print(f"Invalid value: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("This is just an example file showing usage patterns.")
    print("Choose which mode to test:")
    print("1. GUI mode (with predefined values)")
    print("2. Interactive mode (will prompt for input)")
    print("3. CLI mode (requires CLI parameters to be set)")