# Import pyqt6 modules UIC
import os
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QApplication, QMessageBox, QRadioButton, QButtonGroup
from PyQt6.QtGui import QIcon
import sys
import helpers
from modules.logger import logger
from modules.flow import Controller
from modules.capture import Capture
from modules.update import Update

class Settings(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(helpers.get_path(None, helpers.get_config("DEFAULT_GUI_FILENAME"), "Settings.ui"), self)
        self.setWindowTitle(f"{helpers.get_config('APP_NAME')} Settings (v{helpers.get_config('APP_VERSION')})")
        self.setWindowIcon(QIcon(helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_ASSETS_FILENAME"), "icon.png")))
        self.OBSAddr.setText(helpers.load("obs_websocket_address", helpers.get_config("OBS_SERVER_HOST")))
        self.OBSPort.setValue(helpers.load("obs_websocket_port", helpers.get_config("OBS_SERVER_PORT")))
        self.OBSPass.setText(helpers.load("obs_websocket_password", helpers.get_config("OBS_SERVER_PASSWORD")))
        self.SaveButton.clicked.connect(self.save_settings)
    
    def save_settings(self):
        helpers.save("obs_websocket_address", self.OBSAddr.text().strip())
        helpers.save("obs_websocket_port", self.OBSPort.value())
        helpers.save("obs_websocket_password", self.OBSPass.text())
        logger.info("Settings saved")
        QMessageBox.information(self, "Settings", "Settings have been saved. Please restart the application for changes to take effect.")
        self.close()

class Window(QMainWindow):
    def __init__(self, controller: Controller, update: Update):
        super().__init__()
        uic.loadUi(helpers.get_path(None, helpers.get_config("DEFAULT_GUI_FILENAME"), "Main.ui"), self)
        self.setWindowTitle(f"{helpers.get_config('APP_NAME')} (v{helpers.get_config('APP_VERSION')})")
        self.setWindowIcon(QIcon(helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_ASSETS_FILENAME"), "icon.png")))
        self.sizes = helpers.get_config("AVAILABLE_SIZES")
        self.controller = controller
        self._update = update
        
        # Service radio buttons setup
        self.service_buttons = {}
        self.service_button_group = QButtonGroup(self)
        self.setup_service_buttons()

        # Reload all variables
        self.reload_variables()

        self.AspectRatio.currentTextChanged.connect(self.update_resolutions)
        self.Resolution_2.currentTextChanged.connect(self.on_resolution_selected)
        self.VideoId.editingFinished.connect(
            lambda: (
                controller.set_movie_id(text)
                if (text := self.VideoId.text().strip())
                else None
            )
        )

        self.OwnerId.editingFinished.connect(
            lambda: (
                controller.set_owner_id(value)
                if (value := self.OwnerId.value())
                else None
            )
        )

        self.Confirm.clicked.connect(self.kickstart)
        self.OutputFolder.clicked.connect(lambda: helpers.open_folder(self.controller.RECORDING_EDITED_PATH))
        self.actionSettings_2.triggered.connect(self.open_settings)
        self.actionExit.triggered.connect(self.close)
        self.Outro.stateChanged.connect(self.on_outro_changed)

        if controller.capture.is_obs:
            self.CaptureLabel.setText("Capture Method: OBS")
        else:
            self.CaptureLabel.setText("Capture Method: Native")
        
        QMessageBox.information(self, "Update available!", f"{helpers.get_config("APP_NAME")} has an update available! v{self._update.current_update}")

    def restart(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def setup_service_buttons(self):
        """Dynamically create radio buttons for each service in AVAILABLE_SERVICES"""
        available_services = helpers.get_config("AVAILABLE_SERVICES")
        layout = self.serviceButtonsLayout
        
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
            self.controller.set_lvm(service_id)
            helpers.save("service", service_id)

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
        self.OutputFolder.setEnabled(True)

    def verify_inputs(self):
        if not hasattr(self.controller, 'movieid') or not self.controller.movieid:
            logger.error("Movie ID not set")
            QMessageBox.critical(self, "Error", "Movie ID not set")
            return False
        if not hasattr(self.controller, 'ownerid') or self.controller.ownerid == 0:
            logger.error("Owner ID not set")
            QMessageBox.critical(self, "Error", "Owner ID not set")
            return False
        return True

    def should_include_outro(self):
        return self.Outro.isChecked()    

    def on_outro_changed(self, state):
        logger.info(f"Outro checked: {self.Outro.isChecked()}")

    def open_settings(self):
        self.settings_window = Settings()
        self.settings_window.show()

    def reload_variables(self):
        # Set the service based on data.json
        service = helpers.load("service", "local")
        
        # Select the appropriate radio button if it exists
        if service in self.service_buttons:
            self.service_buttons[service].setChecked(True)
            self.controller.set_lvm(service)
        else:
            # Fallback to first available service
            if self.service_buttons:
                first_service = list(self.service_buttons.keys())[0]
                self.service_buttons[first_service].setChecked(True)
                self.controller.set_lvm(first_service)
                logger.warning(f"Service '{service}' not found, defaulting to '{first_service}'")
        
        # Set the movie ID
        movie_id = helpers.load("movie_id", "")
        self.VideoId.setText(movie_id)
        self.controller.set_movie_id(movie_id)

        # Set the owner ID
        owner_id = helpers.load("owner_id", 0)
        self.OwnerId.setValue(owner_id)
        self.controller.set_owner_id(owner_id)

        # aspect ratio combo
        self.AspectRatio.clear()
        self.AspectRatio.addItems(self.sizes.keys())

        # Set the aspect ratio
        aspect_ratio = helpers.load("aspect_ratio", "4:3")
        resolution = helpers.load("resolution", "240p")
        self.AspectRatio.setCurrentText(aspect_ratio)
        self.controller.set_aspect_ratio(aspect_ratio)
        self.update_resolutions(aspect_ratio)

        # Set the resolution
        self.Resolution_2.setCurrentText(resolution)
        self.controller.set_resolution(resolution)

        # Disable auto editing
        self.controller.set_auto_edit(True)

    def update_resolutions(self, aspect_ratio):
        self.Resolution_2.disconnect()
        if not aspect_ratio:
            return
        self.Resolution_2.clear()
        if aspect_ratio in self.sizes:
            self.Resolution_2.addItems(self.sizes[aspect_ratio].keys())
        self.controller.set_aspect_ratio(aspect_ratio)
        self.Resolution_2.currentTextChanged.connect(self.on_resolution_selected)
        self.controller.set_resolution(self.Resolution_2.currentText())

    def on_resolution_selected(self, resolution):
        if not resolution:
            return
        aspect_ratio = self.AspectRatio.currentText()
        if aspect_ratio in self.sizes and resolution in self.sizes[aspect_ratio]:
            width, height, widescreen = self.sizes[aspect_ratio][resolution]
        self.controller.set_resolution(resolution)
