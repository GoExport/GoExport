# Import pyqt6 modules UIC
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QApplication
import sys
import helpers
from modules.logger import logger
from modules.flow import Controller

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

class Window(QMainWindow):
    def __init__(self, controller: Controller):
        super().__init__()
        uic.loadUi(helpers.get_path(None, helpers.get_config("DEFAULT_GUI_FILENAME"), "Main.ui"), self)
        self.setWindowTitle("GoExport")
        self.sizes = helpers.get_config("AVAILABLE_SIZES")
        self.controller = controller

        # Redirect print output to Console widget
        sys.stdout = EmittingStream(self.Console)
        sys.stderr = EmittingStream(self.Console)

        # Set default values
        self.controller.set_lvm("local")
        self.controller.set_owner_id(1)

        # aspect ratio combo
        self.AspectRatio.clear()
        self.AspectRatio.addItems(self.sizes.keys())

        # initialize AspectRatio first
        default_aspect = self.AspectRatio.itemText(0)  # first item
        self.AspectRatio.setCurrentText(default_aspect)
        self.controller.set_auto_edit(True)
        self.controller.set_aspect_ratio(default_aspect)
        self.update_resolutions(default_aspect)

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

    def kickstart(self):
        self.controller.setpath()
        self.controller.start_server()
        self.controller.generate()
        self.controller.export()
        self.controller.stop_server()
        self.controller.final(self.Outro.isChecked())

        # Enable the output folder button
        self.OutputFolder.setEnabled(True)

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
