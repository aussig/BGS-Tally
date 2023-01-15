import tkinter as tk
from tkinter import ttk
from functools import partial
import sys
import webbrowser
from inspect import cleandoc

from bgstally.api import API
from bgstally.constants import FONT_HEADING, FONT_TEXT
from bgstally.debug import Debug
from bgstally.widgets import EntryPlus, HyperlinkManager


class WindowAPI:
    """
    Handles a window showing details for the currently configured API
    """

    def __init__(self, bgstally, api:API):
        self.bgstally = bgstally
        self.api:API = api
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

        default_bg = ttk.Style().lookup('TFrame', 'background')
        default_fg = ttk.Style().lookup('TFrame', 'foreground')
        default_font = ttk.Style().lookup('TFrame', 'font')
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
        self.var_apiurl:tk.StringVar = tk.StringVar(value=self.api.url)
        self.var_apiurl.trace_add('write', partial(self._field_edited))
        self.entry_apiurl:EntryPlus = EntryPlus(frame_main, textvariable=self.var_apiurl)
        self.entry_apiurl.grid(row=current_row, column=1, pady=4, sticky=tk.EW); current_row += 1

        self.label_apikey:tk.Label = tk.Label(frame_main, text="API Key")
        self.var_apikey:tk.StringVar = tk.StringVar(value=self.api.key)
        self.var_apikey.trace_add('write', partial(self._field_edited))
        self.label_apikey.grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        self.entry_apikey:EntryPlus = EntryPlus(frame_main, textvariable=self.var_apikey)
        self.entry_apikey.grid(row=current_row, column=1, pady=4, sticky=tk.EW); current_row += 1

        self.cb_apiactivities:ttk.Checkbutton = ttk.Checkbutton(frame_main, text="Enable /activities Requests")
        self.cb_apiactivities.grid(row=current_row, column=1, pady=4, sticky=tk.W); current_row += 1
        self.cb_apiactivities.configure(command=partial(self._field_edited))
        self.cb_apiactivities.state(['selected', '!alternate'] if self.api.activities_enabled else ['!selected', '!alternate'])

        self.cb_apievents:ttk.Checkbutton = ttk.Checkbutton(frame_main, text="Enable /events Requests")
        self.cb_apievents.grid(row=current_row, column=1, pady=4, sticky=tk.W); current_row += 1
        self.cb_apievents.configure(command=partial(self._field_edited))
        self.cb_apievents.state(['selected', '!alternate'] if self.api.events_enabled else ['!selected', '!alternate'])

        self.btn_fetch = tk.Button(frame_main, text="Fetch API Information", command=partial(self._decline))
        self.btn_fetch.grid(row=current_row, column=1, pady=4, sticky=tk.W); current_row += 1

        tk.Label(frame_main, text="API Information", font=FONT_HEADING).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=4); current_row += 1
        self.txt_intro:tk.Text = tk.Text(frame_main, font=default_font, wrap=tk.WORD, bd=0, highlightthickness=0, borderwidth=0, bg=default_bg, cursor="")
        hyperlink = HyperlinkManager(self.txt_intro)
        self.txt_intro.insert(tk.END, "If you approve this API, BGS-Tally will send your information to it, which may include specific information " \
            "relating to your CMDR such as your location, missions and kills. \n\nThe exact set of Events that will be sent is listed in the 'Events Requested' " \
            "section below. Further information about these Events and what they contain is provided here: ")
        self.txt_intro.insert(tk.END, "Player Journal Documentation", hyperlink.add(partial(webbrowser.open, "https://elite-journal.readthedocs.io/en/latest/")))
        self.txt_intro.insert(tk.END, ".\n\nPLEASE ENSURE YOU TRUST the application, website or system you send this information to!\n")
        self.txt_intro.configure(state='disabled')
        self.txt_intro.tag_config("sel", background=default_bg, foreground=default_fg) # Make the selected text colour the same as the widget background
        self.txt_intro.grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=4); current_row += 1
        tk.Label(frame_main, text="Name").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        tk.Label(frame_main, text=self.api.name, wraplength=text_width, justify=tk.LEFT).grid(row=current_row, column=1, sticky=tk.W, pady=4); current_row += 1
        tk.Label(frame_main, text="Description").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        tk.Label(frame_main, text=self.api.description, wraplength=text_width, justify=tk.LEFT).grid(row=current_row, column=1, sticky=tk.W, pady=4); current_row += 1
        tk.Label(frame_main, text="Events Requested").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        tk.Label(frame_main, text=str(", ".join(self.api.events.keys())), wraplength=text_width, justify=tk.LEFT).grid(row=current_row, column=1, sticky=tk.W, pady=4); current_row += 1

        tk.Button(frame_buttons, text="I Do Not Accept", command=partial(self._decline)).pack(side=tk.RIGHT, padx=5, pady=5)
        tk.Button(frame_buttons, text="I Accept", command=partial(self._accept)).pack(side=tk.RIGHT, padx=5, pady=5)

        self.toplevel.focus() # Necessary because this window is modal, to ensure we lock focus to it immediately
        frame_main.after(1, self._update) # Do this in an 'after' so that the auto-height resizing works on txt_intro


    def _field_edited(self, *args):
        """
        A field in the window has been edited by the user
        """
        self.api.url = self.entry_apiurl.get()
        self.api.key = self.entry_apikey.get()
        self.api.activities_enabled = self.cb_apiactivities.instate(['selected'])
        self.api.events_enabled = self.cb_apievents.instate(['selected'])
        self._update()


    def _update(self, *args):
        """
        Update the prefs UI after a setting has changed
        """
        height = self.txt_intro.tk.call((self.txt_intro._w, "count", "-update", "-displaylines", "1.0", "end"))
        self.txt_intro.configure(height=height)

        api_settings_enabled:bool = self.bgstally.request_manager.url_valid(self.api.url)

        self.btn_fetch.configure(state='normal' if api_settings_enabled else 'disabled')
        self.label_apikey.configure(state='normal' if api_settings_enabled else 'disabled')
        self.entry_apikey.configure(state='normal' if api_settings_enabled else 'disabled')
        self.cb_apiactivities.state(['!disabled'] if api_settings_enabled else ['disabled'])
        self.cb_apievents.state(['!disabled'] if api_settings_enabled else ['disabled'])


    def _accept(self):
        self.toplevel.destroy()

    def _decline(self):
        self.toplevel.destroy()
