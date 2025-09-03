import threading
import tkinter as tk
from tkinter import ttk

import config
import helpers
import main


class GoExportGUI:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        master.title("GoExport GUI")

        # Service selection
        tk.Label(master, text="Service:").grid(row=0, column=0, sticky="w")
        services = list(config.AVAILABLE_SERVICES.keys())
        self.service_var = tk.StringVar(value=services[0])
        self.service_menu = ttk.Combobox(master, textvariable=self.service_var, values=services, state="readonly")
        self.service_menu.grid(row=0, column=1, pady=2, sticky="ew")

        # Aspect ratio selection
        tk.Label(master, text="Aspect Ratio:").grid(row=1, column=0, sticky="w")
        self.aspect_var = tk.StringVar(value=config.AVAILABLE_ASPECT_RATIOS[0])
        self.aspect_menu = ttk.Combobox(master, textvariable=self.aspect_var, values=config.AVAILABLE_ASPECT_RATIOS, state="readonly")
        self.aspect_menu.grid(row=1, column=1, pady=2, sticky="ew")
        self.aspect_var.trace_add("write", self.update_resolutions)

        # Resolution selection
        tk.Label(master, text="Resolution:").grid(row=2, column=0, sticky="w")
        self.res_var = tk.StringVar()
        self.res_menu = ttk.Combobox(master, textvariable=self.res_var, state="readonly")
        self.res_menu.grid(row=2, column=1, pady=2, sticky="ew")
        self.update_resolutions()

        # Owner ID
        tk.Label(master, text="Owner ID:").grid(row=3, column=0, sticky="w")
        self.owner_entry = tk.Entry(master)
        self.owner_entry.grid(row=3, column=1, pady=2, sticky="ew")

        # Movie ID
        tk.Label(master, text="Movie ID:").grid(row=4, column=0, sticky="w")
        self.movie_entry = tk.Entry(master)
        self.movie_entry.grid(row=4, column=1, pady=2, sticky="ew")

        # Auto-edit option
        self.auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(master, text="Auto Edit", variable=self.auto_var).grid(row=5, column=0, columnspan=2, sticky="w")

        # Include outro option
        self.outro_var = tk.BooleanVar(value=True)
        tk.Checkbutton(master, text="Include Outro", variable=self.outro_var).grid(row=6, column=0, columnspan=2, sticky="w")

        # Start button
        tk.Button(master, text="Start", command=self.start).grid(row=7, column=0, columnspan=2, pady=5)

        master.columnconfigure(1, weight=1)

    def update_resolutions(self, *args) -> None:
        aspect = self.aspect_var.get()
        options = list(config.AVAILABLE_SIZES[aspect].keys())
        self.res_menu["values"] = options
        if options:
            self.res_var.set(options[0])

    def start(self) -> None:
        helpers.parameters.no_input = True
        helpers.parameters.service = self.service_var.get()
        helpers.parameters.aspect_ratio = self.aspect_var.get()
        helpers.parameters.resolution = self.res_var.get()
        owner = self.owner_entry.get().strip()
        movie = self.movie_entry.get().strip()
        helpers.parameters.owner_id = owner if owner else None
        helpers.parameters.movie_id = movie if movie else None
        helpers.parameters.auto_edit = self.auto_var.get()
        helpers.parameters.include_outro = self.outro_var.get()
        threading.Thread(target=main.main, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    gui = GoExportGUI(root)
    root.mainloop()
