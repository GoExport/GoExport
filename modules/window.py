# Import pyqt6 modules
import os
import logging
from PyQt6.QtWidgets import QMainWindow, QApplication, QMessageBox, QRadioButton, QButtonGroup
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QObject, pyqtSignal
import sys
import helpers
from modules.logger import logger
from modules.flow import Controller
from modules.capture import Capture
from modules.update import Update

# Import compiled UI files
from gui import Ui_MainWindow_Main, Ui_MainWindow_Settings

class ConsoleHandler(logging.Handler, QObject):
    """Custom logging handler that emits signals for GUI console updates
    
    This handler captures log messages and formats them in a clean way for display
    in the GUI console widget. It removes the Rich terminal formatting and file
    location information, showing only "LEVEL message" format.
    
    The handler emits a Qt signal when a log message is received, which is connected
    to the update_console method to update the GUI in a thread-safe manner.
    """
    log_signal = pyqtSignal(str)
    
    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        # Set a simple formatter for console output
        formatter = logging.Formatter('%(levelname)s %(message)s')
        self.setFormatter(formatter)
    
    def emit(self, record):
        """Clean up log message and emit signal for GUI update"""
        try:
            # Get the formatted message using our custom formatter
            msg = self.format(record)
            
            if msg:
                self.log_signal.emit(msg)
        except Exception:
            pass  # Avoid infinite loop if logging fails

class Settings(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow_Settings()
        self.ui.setupUi(self)
        self.setWindowTitle(f"{helpers.get_config('APP_NAME')} Settings (v{helpers.get_config('APP_VERSION')})")
        self.setWindowIcon(QIcon(helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_ASSETS_FILENAME"), "icon.png")))
        self.ui.OBSAddr.setText(helpers.load("obs_websocket_address", helpers.get_config("OBS_SERVER_HOST")))
        self.ui.OBSPort.setValue(helpers.load("obs_websocket_port", helpers.get_config("OBS_SERVER_PORT")))
        self.ui.OBSPass.setText(helpers.load("obs_websocket_password", helpers.get_config("OBS_SERVER_PASSWORD")))
        self.ui.SaveButton.clicked.connect(self.save_settings)
    
    def save_settings(self):
        helpers.save("obs_websocket_address", self.ui.OBSAddr.text().strip())
        helpers.save("obs_websocket_port", self.ui.OBSPort.value())
        helpers.save("obs_websocket_password", self.ui.OBSPass.text())
        logger.info("Settings saved")
        QMessageBox.information(self, "Settings", "Settings have been saved. Please restart the application for changes to take effect.")
        self.close()

class Window(QMainWindow):
    def __init__(self, controller: Controller, update: Update):
        super().__init__()
        self.ui = Ui_MainWindow_Main()
        self.ui.setupUi(self)
        self.setWindowTitle(f"{helpers.get_config('APP_NAME')} (v{helpers.get_config('APP_VERSION')})")
        self.setWindowIcon(QIcon(helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_ASSETS_FILENAME"), "icon.png")))
        self.sizes = helpers.get_config("AVAILABLE_SIZES")
        self.controller = controller
        self._update = update
        
        # Setup console logging
        self.setup_console_logging()
        
        # Service radio buttons setup
        self.service_buttons = {}
        self.service_button_group = QButtonGroup(self)
        self.setup_service_buttons()

        # Reload all variables
        self.reload_variables()

        self.ui.AspectRatio.currentTextChanged.connect(self.update_resolutions)
        self.ui.Resolution_2.currentTextChanged.connect(self.on_resolution_selected)
        self.ui.VideoId.editingFinished.connect(self.on_movie_id_changed)
        self.ui.OwnerId.editingFinished.connect(self.on_owner_id_changed)
        self.on_movie_id_changed()
        self.on_owner_id_changed()

        self.ui.Confirm.clicked.connect(self.kickstart)
        self.ui.OutputFolder.clicked.connect(lambda: helpers.open_folder(self.controller.RECORDING_EDITED_PATH))
        self.ui.actionSettings_2.triggered.connect(self.open_settings)
        self.ui.actionExit.triggered.connect(self.close)
        self.ui.Outro.stateChanged.connect(self.on_outro_changed)

        if controller.capture.is_obs:
            self.ui.CaptureLabel.setText("Capture Method: OBS")
        else:
            self.ui.CaptureLabel.setText("Capture Method: Native")
        
        if self._update.current_update:
            QMessageBox.information(self, "Update available!", f"{helpers.get_config('APP_NAME')} has an update available! v{self._update.current_update}")

    def setup_console_logging(self):
        """Setup console logging handler to display logs in the GUI console widget
        
        This creates a custom logging handler that captures log messages and displays
        them in the Console QPlainTextEdit widget. The handler uses a simple formatter
        that shows "LEVEL message" format instead of the Rich terminal formatting.
        """
        self.console_handler = ConsoleHandler()
        self.console_handler.log_signal.connect(self.update_console)
        
        # Add the handler to the logger
        logger.addHandler(self.console_handler)
        
        # Clear any existing content in console
        self.ui.Console.clear()
        logger.info("Console logging initialized")

    def update_console(self, message):
        """Update the console widget with a new log message"""
        try:
            self.ui.Console.appendPlainText(message)
            # Auto-scroll to bottom
            scrollbar = self.ui.Console.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            # Avoid infinite loop by not using logger here
            print(f"Error updating console: {e}")

    def closeEvent(self, event):
        """Handle window close event to clean up console handler"""
        try:
            if hasattr(self, 'console_handler'):
                logger.removeHandler(self.console_handler)
        except Exception:
            pass
        super().closeEvent(event)

    def restart(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def setup_service_buttons(self):
        """Dynamically create radio buttons for each service in AVAILABLE_SERVICES"""
        available_services = helpers.get_config("AVAILABLE_SERVICES")
        layout = self.ui.serviceButtonsLayout
        
        # Create a radio button for each service
        first_button = True
        for service_id, service_data in available_services.items():
            # Skip services that don't have a name or are marked as hidden
            if "name" not in service_data:
                continue
            if service_data.get("hidden", False) and helpers.get_config("DEBUG_MODE") is False:
                continue
                
            radio_button = QRadioButton(service_data["name"])
            
            # Set the first button as checked by default
            if first_button:
                radio_button.setChecked(True)
                first_button = False
            
            # Store reference to the button
            self.service_buttons[service_id] = radio_button
            
            # Add to button group for mutual exclusivity
            self.service_button_group.addButton(radio_button)
            
            # Connect to controller
            radio_button.toggled.connect(
                lambda checked, sid=service_id: self.on_service_changed(sid, checked)
            )
            
            # Add to layout
            layout.addWidget(radio_button)
        
        logger.info(f"Loaded {len(self.service_buttons)} services: {list(self.service_buttons.keys())}")

    def on_service_changed(self, service_id, checked):
        """Handle service selection change"""
        if checked:
            logger.info(f"Service changed to: {service_id}")
            try:
                if not self.controller.set_lvm(service_id):
                    QMessageBox.critical(self, "Error", f"Failed to set service to {service_id}")
                    return
                helpers.save("service", service_id)
            except ValueError as e:
                QMessageBox.critical(self, "Error", str(e))
                logger.error(f"Invalid service selection: {e}")

    def on_movie_id_changed(self):
        """Handle movie ID input change"""
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
        # If empty, don't set anything - will be validated later

    def on_owner_id_changed(self):
        """Handle owner ID input change"""
        value = self.ui.OwnerId.value()
        if value > 0:  # Only try to set if there's a valid value
            try:
                if not self.controller.set_owner_id(value):
                    QMessageBox.critical(self, "Error", "Failed to set owner ID")
                    return
                logger.info(f"Owner ID set to: {value}")
            except ValueError as e:
                QMessageBox.critical(self, "Error", str(e))
                logger.error(f"Invalid owner ID: {e}")
        # If 0 or negative, don't set anything - will be validated later

    def kickstart(self):
        if not self.verify_inputs():
            return

        # Ask if user wants to attach to existing clips
        response = QMessageBox.StandardButton.No  # Default to not attach (reset)
        if self.controller.editor.clips:
            response = QMessageBox.question(
                self,
                "Attach to end",
                "Would you like to attach this video that you are about to export to your already existing videos? (This will merge your previous video with the current video.)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
        
        # Check the user's resolution is not higher than the capture resolution
        if helpers.exceeds_monitor_resolution(self.controller.width, self.controller.height):
            QMessageBox.critical(self, "Error", "The selected resolution exceeds your monitor's resolution. Please select a lower resolution that is less or equal to your monitor's resolution.")
            return

        # Hide the window
        self.hide()

        # Reset the controller if not attaching
        if response != QMessageBox.StandardButton.Yes:
            self.controller.reset()
        self.controller.setpath()
        self.controller.start_server()
        self.controller.generate()
        self.controller.export()
        self.controller.stop_server()
        self.controller.final(self.should_include_outro())

        # Show the window again
        self.show()
        QMessageBox.information(self, "Success", f"Your video has been successfully exported! It is located at {self.controller.RECORDING_EDITED}")

        # Enable the output folder button
        self.ui.OutputFolder.setEnabled(True)

    def verify_inputs(self):
        """Verify all required inputs are valid before starting export"""
        # Check if movieId is required and validate it
        if hasattr(self.controller, 'svr_required') and 'movieId' in self.controller.svr_required:
            movie_id = self.ui.VideoId.text().strip()
            if not movie_id:
                QMessageBox.critical(self, "Error", "Movie ID is required for this service but not provided")
                return False
            try:
                if not self.controller.set_movie_id(movie_id):
                    QMessageBox.critical(self, "Error", "Failed to set movie ID")
                    return False
            except ValueError as e:
                QMessageBox.critical(self, "Error", f"Invalid movie ID: {e}")
                return False
        
        # Check if movieOwnerId is required and validate it
        if hasattr(self.controller, 'svr_required') and 'movieOwnerId' in self.controller.svr_required:
            owner_id = self.ui.OwnerId.value()
            if owner_id <= 0:
                QMessageBox.critical(self, "Error", "Owner ID is required for this service but not provided")
                return False
            try:
                if not self.controller.set_owner_id(owner_id):
                    QMessageBox.critical(self, "Error", "Failed to set owner ID")
                    return False
            except ValueError as e:
                QMessageBox.critical(self, "Error", f"Invalid owner ID: {e}")
                return False
        
        # Validate aspect ratio and resolution
        try:
            aspect_ratio = self.ui.AspectRatio.currentText()
            if not self.controller.set_aspect_ratio(aspect_ratio):
                QMessageBox.critical(self, "Error", "Failed to set aspect ratio")
                return False
                
            resolution = self.ui.Resolution_2.currentText()
            if not self.controller.set_resolution(resolution):
                QMessageBox.critical(self, "Error", "Failed to set resolution")
                return False
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Invalid resolution settings: {e}")
            return False
        
        return True

    def should_include_outro(self):
        return self.ui.Outro.isChecked()    

    def on_outro_changed(self, state):
        logger.info(f"Outro checked: {self.ui.Outro.isChecked()}")

    def open_settings(self):
        self.settings_window = Settings()
        self.settings_window.show()

    def reload_variables(self):
        # Set the service based on data.json
        service = helpers.load("service", "local")
        
        # Select the appropriate radio button if it exists
        if service in self.service_buttons:
            self.service_buttons[service].setChecked(True)
            try:
                if not self.controller.set_lvm(service):
                    logger.error(f"Failed to set service to {service}")
            except ValueError as e:
                logger.error(f"Invalid service '{service}': {e}")
        else:
            # Fallback to first available service
            if self.service_buttons:
                first_service = list(self.service_buttons.keys())[0]
                self.service_buttons[first_service].setChecked(True)
                try:
                    if not self.controller.set_lvm(first_service):
                        logger.error(f"Failed to set fallback service to {first_service}")
                except ValueError as e:
                    logger.error(f"Invalid fallback service '{first_service}': {e}")
                logger.warning(f"Service '{service}' not found, defaulting to '{first_service}'")
        
        # Set the movie ID - just populate the UI, don't validate yet
        movie_id = helpers.load("movie_id", "")
        self.ui.VideoId.setText(movie_id)

        # Set the owner ID - just populate the UI, don't validate yet
        owner_id = helpers.load("owner_id", 0)
        self.ui.OwnerId.setValue(owner_id)

        # aspect ratio combo
        self.ui.AspectRatio.clear()
        self.ui.AspectRatio.addItems(self.sizes.keys())

        # Set the aspect ratio
        aspect_ratio = helpers.load("aspect_ratio", "4:3")
        resolution = helpers.load("resolution", "240p")
        self.ui.AspectRatio.setCurrentText(aspect_ratio)
        try:
            if not self.controller.set_aspect_ratio(aspect_ratio):
                logger.error(f"Failed to set aspect ratio to {aspect_ratio}")
        except ValueError as e:
            logger.error(f"Invalid aspect ratio '{aspect_ratio}': {e}")
        
        self.update_resolutions(aspect_ratio)

        # Set the resolution
        self.ui.Resolution_2.setCurrentText(resolution)
        try:
            if not self.controller.set_resolution(resolution):
                logger.error(f"Failed to set resolution to {resolution}")
        except ValueError as e:
            logger.error(f"Invalid resolution '{resolution}': {e}")

        # Enable auto editing
        try:
            if not self.controller.set_auto_edit(True):
                logger.error("Failed to set auto edit")
        except Exception as e:
            logger.error(f"Error setting auto edit: {e}")

    def update_resolutions(self, aspect_ratio):
        self.ui.Resolution_2.disconnect()
        if not aspect_ratio:
            return
        self.ui.Resolution_2.clear()
        if aspect_ratio in self.sizes:
            self.ui.Resolution_2.addItems(self.sizes[aspect_ratio].keys())
        
        try:
            if not self.controller.set_aspect_ratio(aspect_ratio):
                logger.error(f"Failed to set aspect ratio to {aspect_ratio}")
        except ValueError as e:
            logger.error(f"Invalid aspect ratio '{aspect_ratio}': {e}")
        
        self.ui.Resolution_2.currentTextChanged.connect(self.on_resolution_selected)
        
        # Set the current resolution
        current_resolution = self.ui.Resolution_2.currentText()
        if current_resolution:
            try:
                if not self.controller.set_resolution(current_resolution):
                    logger.error(f"Failed to set resolution to {current_resolution}")
            except ValueError as e:
                logger.error(f"Invalid resolution '{current_resolution}': {e}")

    def on_resolution_selected(self, resolution):
        if not resolution:
            return
        try:
            if not self.controller.set_resolution(resolution):
                logger.error(f"Failed to set resolution to {resolution}")
                QMessageBox.critical(self, "Error", f"Failed to set resolution to {resolution}")
        except ValueError as e:
            logger.error(f"Invalid resolution '{resolution}': {e}")
            QMessageBox.critical(self, "Error", f"Invalid resolution: {e}")
