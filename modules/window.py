# Import pyqt6 modules UIC
import os
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QApplication, QMessageBox
from PyQt6.QtGui import QIcon
import sys
import helpers
from modules.logger import logger
from modules.flow import Controller
from modules.capture import Capture

import re

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class EmittingStream:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, text):
        clean_text = ANSI_ESCAPE.sub('', text)  # Remove ANSI codes
        if clean_text.strip():
            self.text_widget.appendPlainText(clean_text.strip())

    def flush(self):
        pass

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
    def __init__(self, controller: Controller):
        super().__init__()
        uic.loadUi(helpers.get_path(None, helpers.get_config("DEFAULT_GUI_FILENAME"), "Main.ui"), self)
        self.setWindowTitle(f"{helpers.get_config('APP_NAME')} (v{helpers.get_config('APP_VERSION')})")
        self.setWindowIcon(QIcon(helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_ASSETS_FILENAME"), "icon.png")))
        self.sizes = helpers.get_config("AVAILABLE_SIZES")
        self.controller = controller

        # Reload all variables
        self.reload_variables()

        # Redirect print output to Console widget
        sys.stdout = EmittingStream(self.Console)
        sys.stderr = EmittingStream(self.Console)

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

        self.serviceButton_2.toggled.connect(lambda checked: controller.set_lvm("local") if checked else controller.set_lvm("ft"))
        self.Confirm.clicked.connect(self.kickstart)
        self.OutputFolder.clicked.connect(lambda: helpers.open_folder(self.controller.RECORDING_EDITED_PATH))
        self.actionSettings_2.triggered.connect(self.open_settings)
        self.actionExit.triggered.connect(self.close)
        self.Outro.stateChanged.connect(self.on_outro_changed)

        if controller.capture.is_obs:
            self.CaptureLabel.setText("Capture Method: OBS")
        else:
            self.CaptureLabel.setText("Capture Method: Native")

    def restart(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)

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
        print("Outro checked:", self.Outro.isChecked())

    def open_settings(self):
        self.settings_window = Settings()
        self.settings_window.show()

    def reload_variables(self):
        # Set between the Wrapper or FlashThemes based on the data.json
        service = helpers.load("service", "local")
        if service == "local":
            self.serviceButton_2.setChecked(True)
            self.controller.set_lvm("local")
        else:
            self.serviceButton.setChecked(True)
            self.controller.set_lvm("ft")
        
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
