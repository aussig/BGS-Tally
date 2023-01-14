import tkinter as tk
from tkinter import ttk
from functools import partial
import sys

from bgstally.apimanager import APIManager
from bgstally.constants import FONT_HEADING


class WindowAPI:
    """
    Handles a window showing details for the currently configured API
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.toplevel:tk.Toplevel = None


    def show(self, plugin_frame:tk.Frame):
        """
        Show the window
        """
        if self.toplevel is not None and self.toplevel.winfo_exists():
            self.toplevel.lift()
            self.toplevel.focus()
            # TODO: May need to refresh information in the window here
            return

        self.toplevel = tk.Toplevel(plugin_frame)
        self.toplevel.title(f"{self.bgstally.plugin_name} - Confirm API Settings")
        self.toplevel.resizable(False, False)
        self.toplevel.overrideredirect(True) # Remove all window decorations
        self.toplevel.grab_set() # Makes it application-modal

        if sys.platform != 'darwin' or plugin_frame.winfo_rooty() > 0:
            self.toplevel.geometry(f"+{plugin_frame.winfo_rootx()+40}+{plugin_frame.winfo_rooty()+40}")

        frame_container:ttk.Frame = ttk.Frame(self.toplevel)
        frame_container.pack(fill=tk.BOTH, expand=1)

        frame_main:ttk.Frame = ttk.Frame(frame_container)
        frame_main.pack(fill=tk.BOTH, padx=5, pady=5, expand=1)

        frame_buttons:tk.Frame = tk.Frame(frame_container)
        frame_buttons.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)

        current_row:int = 0
        text_width:int = 500
        tk.Label(frame_main, text="API Settings", font=FONT_HEADING).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=4); current_row += 1
        tk.Label(frame_main, text="Name:").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        tk.Label(frame_main, text=self.bgstally.api_manager.name, wraplength=text_width, justify=tk.LEFT).grid(row=current_row, column=1, sticky=tk.W, pady=4); current_row += 1
        tk.Label(frame_main, text="Description:").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        tk.Label(frame_main, text=self.bgstally.api_manager.description, wraplength=text_width, justify=tk.LEFT).grid(row=current_row, column=1, sticky=tk.W, pady=4); current_row += 1
        tk.Label(frame_main, text="Events Requested:").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        tk.Label(frame_main, text=str(self.bgstally.api_manager.events.keys()), wraplength=text_width, justify=tk.LEFT).grid(row=current_row, column=1, sticky=tk.W, pady=4); current_row += 1

        tk.Button(frame_buttons, text="I Do Not Accept", command=partial(self._decline)).pack(side=tk.RIGHT, padx=5, pady=5)
        tk.Button(frame_buttons, text="I Accept", command=partial(self._accept)).pack(side=tk.RIGHT, padx=5, pady=5)

        self.toplevel.focus() # Necessary because this window is modal, to ensure we lock focus to it immediately


    def _accept(self):
        self.toplevel.destroy()

    def _decline(self):
        self.toplevel.destroy()
