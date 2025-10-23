"""
Test script to verify compiled UI files work correctly
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow
from gui import Ui_MainWindow_Main, Ui_MainWindow_Settings

def test_main_ui():
    """Test that Main UI loads correctly"""
    try:
        app = QApplication(sys.argv)
        window = QMainWindow()
        ui = Ui_MainWindow_Main()
        ui.setupUi(window)
        
        # Check that key widgets exist
        assert hasattr(ui, 'VideoId'), "VideoId widget missing"
        assert hasattr(ui, 'OwnerId'), "OwnerId widget missing"
        assert hasattr(ui, 'AspectRatio'), "AspectRatio widget missing"
        assert hasattr(ui, 'Resolution_2'), "Resolution_2 widget missing"
        assert hasattr(ui, 'Confirm'), "Confirm button missing"
        assert hasattr(ui, 'OutputFolder'), "OutputFolder button missing"
        assert hasattr(ui, 'Outro'), "Outro checkbox missing"
        assert hasattr(ui, 'serviceButtonsLayout'), "serviceButtonsLayout missing"
        assert hasattr(ui, 'CaptureLabel'), "CaptureLabel missing"
        assert hasattr(ui, 'Console'), "Console widget missing"
        
        print("✓ Main UI test passed - all widgets found")
        return True
    except Exception as e:
        print(f"✗ Main UI test failed: {e}")
        return False

def test_settings_ui():
    """Test that Settings UI loads correctly"""
    try:
        app = QApplication.instance() or QApplication(sys.argv)
        window = QMainWindow()
        ui = Ui_MainWindow_Settings()
        ui.setupUi(window)
        
        # Check that key widgets exist
        assert hasattr(ui, 'OBSAddr'), "OBSAddr widget missing"
        assert hasattr(ui, 'OBSPort'), "OBSPort widget missing"
        assert hasattr(ui, 'OBSPass'), "OBSPass widget missing"
        assert hasattr(ui, 'SaveButton'), "SaveButton missing"
        
        print("✓ Settings UI test passed - all widgets found")
        return True
    except Exception as e:
        print(f"✗ Settings UI test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing compiled UI files...")
    print("-" * 50)
    
    main_result = test_main_ui()
    settings_result = test_settings_ui()
    
    print("-" * 50)
    if main_result and settings_result:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
