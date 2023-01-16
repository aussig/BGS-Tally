import tkinter as tk
from tkinter import PhotoImage, ttk
from functools import partial
import sys
import webbrowser
from inspect import cleandoc
from os import path

from bgstally.api import API
from bgstally.constants import FOLDER_ASSETS, FONT_HEADING, FONT_TEXT
from bgstally.debug import Debug
from bgstally.widgets import EntryPlus, HyperlinkManager
from requests import Response
from bgstally.requestmanager import BGSTallyRequest


class WindowAPI:
    """
    Handles a window showing details for the currently configured API
    """

    def __init__(self, bgstally, api:API):
        self.bgstally = bgstally
        self.api:API = api
        self.toplevel:tk.Toplevel = None

        self.image_icon_green_tick = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_green_tick.png"))
        self.image_icon_red_cross = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_red_cross.png"))


    def show(self, parent_frame:tk.Frame = None):
        """
        Show the window
        """
        # TODO: When we support multiple APIs, this will no longer be a single instance window, so get rid
        if self.toplevel is not None and self.toplevel.winfo_exists():
            self.toplevel.lift()
            self.toplevel.focus()
            # TODO: May need to refresh information in the window here
            return

        self.discovery_done = False

        if parent_frame is None: parent_frame = self.bgstally.ui.frame
        self.toplevel = tk.Toplevel(parent_frame)
        self.toplevel.title(f"{self.bgstally.plugin_name} - API Settings")
        self.toplevel.resizable(False, False)

        if sys.platform == 'win32':
            self.toplevel.attributes('-toolwindow', tk.TRUE)

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

        tk.Label(frame_main, text="About This", font=FONT_HEADING).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=4); current_row += 1
        self.txt_intro:tk.Text = tk.Text(frame_main, font=default_font, wrap=tk.WORD, bd=0, highlightthickness=0, borderwidth=0, bg=default_bg, cursor="")
        hyperlink = HyperlinkManager(self.txt_intro)
        self.txt_intro.insert(tk.END, "An Application Programming Interface (API) is used to send your data to a server.\n\nTake care when agreeing to this - if " \
            "you approve this server, BGS-Tally will send your information to it, which will include CMDR details such as your location, " \
            "missions and kills. \n\nThe exact set of Events that will be sent is listed in the 'Events Requested' section below. " \
            "Further information about these Events and what they contain is provided here: ")
        self.txt_intro.insert(tk.END, "Player Journal Documentation", hyperlink.add(partial(webbrowser.open, "https://elite-journal.readthedocs.io/en/latest/")))
        self.txt_intro.insert(tk.END, ".\n\nPLEASE ENSURE YOU TRUST the server you send this information to!\n")
        self.txt_intro.configure(state='disabled')
        self.txt_intro.tag_config("sel", background=default_bg, foreground=default_fg) # Make the selected text colour the same as the widget background
        self.txt_intro.grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=4); current_row += 1

        tk.Label(frame_main, text="API Settings", font=FONT_HEADING).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=4); current_row += 1
        tk.Label(frame_main, text="The following information will be provided by the administrator of the server").grid(row=current_row, column=0, columnspan=2, sticky=tk.NW, pady=4); current_row += 1
        tk.Label(frame_main, text="Server URL").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        self.var_apiurl:tk.StringVar = tk.StringVar(value=self.api.url)
        self.entry_apiurl:EntryPlus = EntryPlus(frame_main, textvariable=self.var_apiurl)
        self.entry_apiurl.grid(row=current_row, column=1, pady=4, sticky=tk.EW); current_row += 1
        self.var_apiurl.trace_add('write', partial(self._field_edited, self.entry_apiurl))
        self.label_apikey:tk.Label = tk.Label(frame_main, text="API Key")
        self.var_apikey:tk.StringVar = tk.StringVar(value=self.api.key)
        self.label_apikey.grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        self.entry_apikey:EntryPlus = EntryPlus(frame_main, textvariable=self.var_apikey)
        self.entry_apikey.grid(row=current_row, column=1, pady=4, sticky=tk.EW); current_row += 1
        self.var_apikey.trace_add('write', partial(self._field_edited, self.entry_apikey))
        self.cb_apiactivities:ttk.Checkbutton = ttk.Checkbutton(frame_main, text="Enable /activities Requests")
        self.cb_apiactivities.grid(row=current_row, column=1, pady=4, sticky=tk.W); current_row += 1
        self.cb_apiactivities.configure(command=partial(self._field_edited, self.cb_apiactivities))
        self.cb_apiactivities.state(['selected', '!alternate'] if self.api.activities_enabled else ['!selected', '!alternate'])
        self.cb_apievents:ttk.Checkbutton = ttk.Checkbutton(frame_main, text="Enable /events Requests")
        self.cb_apievents.grid(row=current_row, column=1, pady=4, sticky=tk.W); current_row += 1
        self.cb_apievents.configure(command=partial(self._field_edited, self.cb_apievents))
        self.cb_apievents.state(['selected', '!alternate'] if self.api.events_enabled else ['!selected', '!alternate'])
        self.btn_fetch = tk.Button(frame_main, text="Establish Connection", command=partial(self._discover))
        self.btn_fetch.grid(row=current_row, column=1, pady=4, sticky=tk.E); current_row += 1

        tk.Label(frame_main, text="API Information", font=FONT_HEADING).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=4); current_row += 1
        tk.Label(frame_main, text="The following information will be discovered automatically when you establish a connection").grid(row=current_row, column=0, columnspan=2, sticky=tk.NW, pady=4); current_row += 1
        tk.Label(frame_main, text="Name").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        self.lbl_apiname:tk.Label = tk.Label(frame_main, wraplength=text_width, justify=tk.LEFT)
        self.lbl_apiname.grid(row=current_row, column=1, sticky=tk.W, pady=4); current_row += 1
        tk.Label(frame_main, text="Description").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        self.lbl_apidescription:tk.Label = tk.Label(frame_main, wraplength=text_width, justify=tk.LEFT)
        self.lbl_apidescription.grid(row=current_row, column=1, sticky=tk.W, pady=4); current_row += 1
        tk.Label(frame_main, text="Events Requested").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        self.lbl_apievents:tk.Label = tk.Label(frame_main, wraplength=text_width, justify=tk.LEFT)
        self.lbl_apievents.grid(row=current_row, column=1, sticky=tk.W, pady=4); current_row += 1
        tk.Label(frame_main, text="Approved by you").grid(row=current_row, column=0, sticky=tk.NW, pady=4)
        self.lbl_approved:ttk.Label = ttk.Label(frame_main, image=self.image_icon_green_tick if self.api.user_approved else self.image_icon_red_cross)
        self.lbl_approved.grid(row=current_row, column=1, sticky=tk.W, pady=4); current_row += 1

        self.btn_decline:tk.Button = tk.Button(frame_buttons, text="I Do Not Accept", command=partial(self._decline))
        self.btn_decline.pack(side=tk.RIGHT, padx=5, pady=5)
        self.btn_accept:tk.Button = tk.Button(frame_buttons, text="I Accept", command=partial(self._accept))
        self.btn_accept.pack(side=tk.RIGHT, padx=5, pady=5)

        self.toplevel.focus()
        frame_main.after(1, self._update) # Do this in an 'after' so that the auto-height resizing works on txt_intro


    def _field_edited(self, widget:tk.Widget, *args):
        """
        A field in the window has been edited by the user
        """
        # Any edit to URL means user must re-discover and re-approve
        if widget == self.entry_apiurl:
            self.api.user_approved = False
            self.discovery_done = False

        self.api.url = self.entry_apiurl.get().rstrip('/') + '/'
        self.api.key = self.entry_apikey.get()
        self.api.activities_enabled = self.cb_apiactivities.instate(['selected'])
        self.api.events_enabled = self.cb_apievents.instate(['selected'])
        self._update()


    def _update(self, *args):
        """
        Update the prefs UI after something has changed
        """
        # Automatically adjust height of Text field
        height = self.txt_intro.tk.call((self.txt_intro._w, "count", "-update", "-displaylines", "1.0", "end"))
        self.txt_intro.configure(height=height)

        url_valid:bool = self.bgstally.request_manager.url_valid(self.api.url)

        self.btn_fetch.configure(state='normal' if url_valid else 'disabled')

        self.label_apikey.configure(state='normal' if url_valid else 'disabled')
        self.entry_apikey.configure(state='normal' if url_valid else 'disabled')
        self.cb_apiactivities.state(['!disabled'] if url_valid else ['disabled'])
        self.cb_apievents.state(['!disabled'] if url_valid else ['disabled'])

        self.lbl_apiname.configure(text=self.api.name)
        self.lbl_apidescription.configure(text=self.api.description)
        self.lbl_apievents.configure(text=", ".join(self.api.events.keys()))

        self.btn_decline.configure(state='normal' if url_valid and self.discovery_done else 'disabled')
        self.btn_accept.configure(state='normal' if url_valid and self.discovery_done else 'disabled')

        self.lbl_approved.configure(image=self.image_icon_green_tick if self.api.user_approved else self.image_icon_red_cross)


    def _discover(self):
        """
        The user has clicked the 'Fetch information' button
        """
        self.btn_fetch.configure(state='disabled')
        self.api.discover(self.discovery_received)


    def discovery_received(self, success:bool, response:Response, request:BGSTallyRequest):
        """
        Discovery API information received from the server
        """
        self.btn_fetch.configure(state='normal')
        self.discovery_done = True
        self.api.discovery_received(success, response, request)
        self._update()


    def _accept(self):
        """
        User has clicked the approve button
        """
        self.api.user_approved = True
        self.toplevel.destroy()


    def _decline(self):
        """
        User has clicked the don't approve button
        """
        self.api.user_approved = False
        self.toplevel.destroy()
