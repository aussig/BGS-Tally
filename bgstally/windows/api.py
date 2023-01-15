import tkinter as tk
from tkinter import ttk
from functools import partial
import sys

from bgstally.apimanager import APIManager
from bgstally.constants import CheckStates, FONT_HEADING
from bgstally.widgets import EntryPlus


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
        # TODO: This will no longer be a single instance window, so get rid
        if self.toplevel is not None and self.toplevel.winfo_exists():
            self.toplevel.lift()
            self.toplevel.focus()
            # TODO: May need to refresh information in the window here
            return

        self.toplevel = tk.Toplevel(plugin_frame)
        self.toplevel.title(f"{self.bgstally.plugin_name} - API Settings")
        self.toplevel.resizable(False, False)
        #self.toplevel.overrideredirect(True) # Remove all window decorations
        #self.toplevel.grab_set() # Makes it application-modal

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
        tk.Label(frame_main, text="API URL").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        self.entry_apiurl:EntryPlus = EntryPlus(frame_main, textvariable=self.bgstally.state.APIURL)
        self.entry_apiurl.grid(row=current_row, column=1, pady=4, sticky=tk.EW); current_row += 1
        if not self.bgstally.state.APIURL.trace_info():  self.bgstally.state.APIURL.trace_add("write", self._update)
        self.label_apikey:tk.Label = tk.Label(frame_main, text="API Key")
        self.label_apikey.grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        self.entry_apikey:EntryPlus = EntryPlus(frame_main, textvariable=self.bgstally.state.APIKey)
        self.entry_apikey.grid(row=current_row, column=1, pady=4, sticky=tk.EW); current_row += 1
        self.cb_apiactivities:tk.Checkbutton = tk.Checkbutton(frame_main, text="Enable /activities Requests", variable=self.bgstally.state.APIActivitiesEnabled, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF)
        self.cb_apiactivities.grid(row=current_row, column=1, pady=4, sticky=tk.W); current_row += 1
        self.cb_apievents:tk.Checkbutton = tk.Checkbutton(frame_main, text="Enable /events Requests", variable=self.bgstally.state.APIEventsEnabled, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF)
        self.cb_apievents.grid(row=current_row, column=1, pady=4, sticky=tk.W); current_row += 1
        self.btn_fetch = tk.Button(frame_main, text="Fetch API Information", command=partial(self._decline))
        self.btn_fetch.grid(row=current_row, column=1, pady=4, sticky=tk.W); current_row += 1

        tk.Label(frame_main, text="API Information", font=FONT_HEADING).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=4); current_row += 1
        tk.Label(frame_main, text="Name").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        tk.Label(frame_main, text=self.bgstally.api_manager.name, wraplength=text_width, justify=tk.LEFT).grid(row=current_row, column=1, sticky=tk.W, pady=4); current_row += 1
        tk.Label(frame_main, text="Description").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        tk.Label(frame_main, text=self.bgstally.api_manager.description, wraplength=text_width, justify=tk.LEFT).grid(row=current_row, column=1, sticky=tk.W, pady=4); current_row += 1
        tk.Label(frame_main, text="Events Requested").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        tk.Label(frame_main, text=str(self.bgstally.api_manager.events.keys()), wraplength=text_width, justify=tk.LEFT).grid(row=current_row, column=1, sticky=tk.W, pady=4); current_row += 1

        tk.Button(frame_buttons, text="I Do Not Accept", command=partial(self._decline)).pack(side=tk.RIGHT, padx=5, pady=5)
        tk.Button(frame_buttons, text="I Accept", command=partial(self._accept)).pack(side=tk.RIGHT, padx=5, pady=5)

        self._update()
        self.toplevel.focus() # Necessary because this window is modal, to ensure we lock focus to it immediately


    def _update(self, var_name:str = None, var_index:str = None, operation:str = None):
        """
        Update the prefs UI after a setting has changed
        """
        api_settings_enabled:bool = self.bgstally.request_manager.url_valid(self.bgstally.state.APIURL.get())

        self.btn_fetch.configure(state="normal" if api_settings_enabled else "disabled")
        self.label_apikey.configure(state="normal" if api_settings_enabled else "disabled")
        self.entry_apikey.configure(state="normal" if api_settings_enabled else "disabled")
        self.cb_apiactivities.configure(state="normal" if api_settings_enabled else "disabled")
        self.cb_apievents.configure(state="normal" if api_settings_enabled else "disabled")


    def _accept(self):
        self.toplevel.destroy()

    def _decline(self):
        self.toplevel.destroy()
