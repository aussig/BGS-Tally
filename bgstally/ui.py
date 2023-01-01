import tkinter as tk
from datetime import datetime, timedelta
from functools import partial
from os import path
from threading import Thread
from time import sleep
from tkinter import PhotoImage, ttk
from tkinter.messagebox import askyesno
from typing import List, Optional

import myNotebook as nb
import semantic_version
from theme import theme
from ttkHyperlinkLabel import HyperlinkLabel

from bgstally.activity import Activity
from bgstally.constants import FOLDER_ASSETS, CheckStates, DiscordActivity, DiscordPostStyle, UpdateUIPolicy
from bgstally.debug import Debug
from bgstally.widgets import EntryPlus
from bgstally.windows.activity import WindowActivity
from bgstally.windows.cmdrs import WindowCMDRs
from bgstally.windows.fleetcarrier import WindowFleetCarrier
from config import config

DATETIME_FORMAT_OVERLAY = "%Y-%m-%d %H:%M"
SIZE_BUTTON_PIXELS = 30
TIME_WORKER_PERIOD_S = 2
TIME_TICK_ALERT_M = 60
URL_LATEST_RELEASE = "https://github.com/aussig/BGS-Tally/releases/latest"
URL_WIKI = "https://github.com/aussig/BGS-Tally/wiki"

class UI:
    """
    Display the user's activity
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.image_blank = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "blank.png"))
        self.image_button_dropdown_menu = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "button_dropdown_menu.png"))
        self.image_button_cmdrs = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "button_cmdrs.png"))
        self.image_button_carrier = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "button_carrier.png"))

        self.heading_font = ("Helvetica", 11, "bold")

        self.thread: Optional[Thread] = Thread(target=self._worker, name="BGSTally UI worker")
        self.thread.daemon = True
        self.thread.start()


    def shut_down(self):
        """
        Shut down all worker threads.
        """


    def get_plugin_frame(self, parent_frame: tk.Frame, git_version: Optional[semantic_version.Version]):
        """
        Return a TK Frame for adding to the EDMC main window
        """
        self.frame = tk.Frame(parent_frame)

        current_row = 0
        tk.Label(self.frame, text="BGS Tally (Aussi)").grid(row=current_row, column=0, sticky=tk.W)
        tk.Label(self.frame, text=f"v{str(self.bgstally.version)}").grid(row=current_row, column=1, sticky=tk.W)
        if git_version > self.bgstally.version:
            HyperlinkLabel(self.frame, text=f"New version available (v{str(git_version)})", background=nb.Label().cget('background'), url=URL_LATEST_RELEASE, underline=True).grid(row=current_row, column=1, columnspan=2, sticky=tk.W)
        current_row += 1
        self.button_latest_tick: tk.Button = tk.Button(self.frame, text="Latest BGS Tally", height=SIZE_BUTTON_PIXELS-2, image=self.image_blank, compound=tk.RIGHT, command=partial(self._show_activity_window, self.bgstally.activity_manager.get_current_activity()))
        self.button_latest_tick.grid(row=current_row, column=0, padx=3)
        self.button_previous_ticks: tk.Button = tk.Button(self.frame, text="Previous BGS Tallies ", height=SIZE_BUTTON_PIXELS-2, image=self.image_button_dropdown_menu, compound=tk.RIGHT, command=self._previous_ticks_popup)
        self.button_previous_ticks.grid(row=current_row, column=1, padx=3)
        tk.Button(self.frame, image=self.image_button_cmdrs, height=SIZE_BUTTON_PIXELS, width=SIZE_BUTTON_PIXELS, command=self._show_cmdr_list_window).grid(row=current_row, column=2, padx=3)
        if self.bgstally.capi_fleetcarrier_available():
            self.button_carrier: tk.Button = tk.Button(self.frame, image=self.image_button_carrier, state=('normal' if self.bgstally.fleet_carrier.available() else 'disabled'), height=SIZE_BUTTON_PIXELS, width=SIZE_BUTTON_PIXELS, command=self._show_fc_window)
            self.button_carrier.grid(row=current_row, column=3, padx=3)
        else:
            self.button_carrier: tk.Button = None
        current_row += 1
        tk.Label(self.frame, text="BGS Tally Status:").grid(row=current_row, column=0, sticky=tk.W)
        tk.Label(self.frame, textvariable=self.bgstally.state.Status).grid(row=current_row, column=1, sticky=tk.W)
        current_row += 1
        tk.Label(self.frame, text="Last BGS Tick:").grid(row=current_row, column=0, sticky=tk.W)
        self.label_tick: tk.Label = tk.Label(self.frame, text=self.bgstally.tick.get_formatted())
        self.label_tick.grid(row=current_row, column=1, sticky=tk.W)
        current_row += 1

        return self.frame


    def update_plugin_frame(self):
        """
        Update the tick time label, current activity button and carrier button in the plugin frame
        """
        self.label_tick.config(text=self.bgstally.tick.get_formatted())
        self.button_latest_tick.config(command=partial(self._show_activity_window, self.bgstally.activity_manager.get_current_activity()))
        if self.button_carrier is not None:
            self.button_carrier.config(state=('normal' if self.bgstally.fleet_carrier.available() else 'disabled'))


    def get_prefs_frame(self, parent_frame: tk.Frame):
        """
        Return a TK Frame for adding to the EDMC settings dialog
        """

        frame = nb.Frame(parent_frame)
        # Make the second column fill available space
        frame.columnconfigure(1, weight=1)

        current_row = 1
        nb.Label(frame, text=f"BGS Tally (modified by Aussi) v{str(self.bgstally.version)}", font=self.heading_font).grid(column=0, padx=10, sticky=tk.W)
        HyperlinkLabel(frame, text="Instructions for Use", background=nb.Label().cget('background'), url=URL_WIKI, underline=True).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="General", font=self.heading_font).grid(column=0, padx=10, sticky=tk.W); current_row += 1
        nb.Checkbutton(frame, text="BGS Tally Active", variable=self.bgstally.state.Status, onvalue="Active", offvalue="Paused").grid(column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Checkbutton(frame, text="Show Systems with Zero Activity", variable=self.bgstally.state.ShowZeroActivitySystems, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF).grid(column=1, padx=10, sticky=tk.W); current_row += 1

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="Discord", font=self.heading_font).grid(column=0, padx=10, sticky=tk.W); current_row += 1
        nb.Label(frame, text="Post Format").grid(row=current_row, column=0, padx=10, sticky=tk.W)
        nb.Radiobutton(frame, text="Modern", variable=self.bgstally.state.DiscordPostStyle, value=DiscordPostStyle.EMBED).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Radiobutton(frame, text="Legacy", variable=self.bgstally.state.DiscordPostStyle, value=DiscordPostStyle.TEXT).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Label(frame, text="Activity to Include").grid(row=current_row, column=0, padx=10, sticky=tk.W)
        nb.Radiobutton(frame, text="BGS", variable=self.bgstally.state.DiscordActivity, value=DiscordActivity.BGS).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Radiobutton(frame, text="Thargoid War", variable=self.bgstally.state.DiscordActivity, value=DiscordActivity.THARGOIDWAR).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Radiobutton(frame, text="Both", variable=self.bgstally.state.DiscordActivity, value=DiscordActivity.BOTH).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Label(frame, text="Other Options").grid(row=current_row, column=0, padx=10, sticky=tk.W)
        nb.Checkbutton(frame, text="Abbreviate Faction Names", variable=self.bgstally.state.AbbreviateFactionNames, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Checkbutton(frame, text="Include Secondary INF", variable=self.bgstally.state.IncludeSecondaryInf, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Label(frame, text="Discord BGS Webhook URL").grid(row=current_row, column=0, padx=10, sticky=tk.W)
        EntryPlus(frame, textvariable=self.bgstally.state.DiscordBGSWebhook).grid(row=current_row, column=1, padx=10, pady=1, sticky=tk.EW); current_row += 1
        #nb.Label(frame, text="Discord FC Webhook URL").grid(row=current_row, column=0, padx=10, sticky=tk.W)
        #EntryPlus(frame, textvariable=self.bgstally.state.DiscordFCWebhook).grid(row=current_row, column=1, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="Discord Thargoid War Webhook URL").grid(row=current_row, column=0, padx=10, sticky=tk.W)
        EntryPlus(frame, textvariable=self.bgstally.state.DiscordTWWebhook).grid(row=current_row, column=1, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="Discord Post as User").grid(row=current_row, column=0, padx=10, sticky=tk.W)
        EntryPlus(frame, textvariable=self.bgstally.state.DiscordUsername).grid(row=current_row, column=1, padx=10, pady=1, sticky=tk.W); current_row += 1

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="In-game Overlay", font=self.heading_font).grid(column=0, padx=10, sticky=tk.W); current_row += 1
        nb.Checkbutton(frame, text="Show In-game Overlay", variable=self.bgstally.state.EnableOverlay, state="disabled" if self.bgstally.overlay.edmcoverlay == None else "enabled", onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.bgstally.state.refresh).grid(column=1, padx=10, sticky=tk.W); current_row += 1
        if self.bgstally.overlay.edmcoverlay == None:
            nb.Label(frame, text="In-game overlay support requires the separate EDMCOverlay plugin to be installed - see the instructions for more information.").grid(columnspan=2, padx=10, sticky=tk.W); current_row += 1

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="Advanced", font=self.heading_font).grid(column=0, padx=10, sticky=tk.W); current_row += 1
        tk.Button(frame, text="FORCE Tick", command=self._confirm_force_tick, bg="red", fg="white").grid(column=1, padx=10, sticky=tk.W, row=current_row); current_row += 1

        return frame


    def _worker(self) -> None:
        """
        Handle thread work for overlay
        """
        Debug.logger.debug("Starting UI Worker...")

        while True:
            if config.shutting_down:
                Debug.logger.debug("Shutting down UI Worker...")
                return

            self.bgstally.overlay.display_message("tick", f"Curr Tick: {self.bgstally.tick.get_formatted(DATETIME_FORMAT_OVERLAY)}", True)

            if datetime.utcnow() > self.bgstally.tick.next_predicted() + timedelta(minutes = TIME_TICK_ALERT_M):
                self.bgstally.overlay.display_message("tickwarn", f"Tick over {TIME_TICK_ALERT_M}m Overdue (Estimated)", True)
            elif datetime.utcnow() > self.bgstally.tick.next_predicted():
                self.bgstally.overlay.display_message("tickwarn", f"Past Estimated Tick Time", True, text_colour_override="#FFA500")
            elif datetime.utcnow() > self.bgstally.tick.next_predicted() - timedelta(minutes = TIME_TICK_ALERT_M):
                self.bgstally.overlay.display_message("tickwarn", f"Within {TIME_TICK_ALERT_M}m of Next Tick (Estimated)", True, text_colour_override="yellow")

            sleep(TIME_WORKER_PERIOD_S)


    def _previous_ticks_popup(self):
        """
        Display a menu of activity for previous ticks
        """
        menu = tk.Menu(self.frame, tearoff = 0)

        activities: List = self.bgstally.activity_manager.get_previous_activities()

        for activity in activities:
            menu.add_command(label=activity.tick_time, command=partial(self._show_activity_window, activity))

        try:
            menu.tk_popup(self.button_previous_ticks.winfo_rootx(), self.button_previous_ticks.winfo_rooty())
        finally:
            menu.grab_release()


    def _show_cmdr_list_window(self):
        """
        Display the CMDR list window
        """
        WindowCMDRs(self.bgstally, self)


    def _show_activity_window(self, activity: Activity):
        """
        Display the activity data window, using data from the passed in activity object
        """
        WindowActivity(self.bgstally, self, activity)


    def _show_fc_window(self):
        """
        Display the Fleet Carrier Window
        """
        WindowFleetCarrier(self.bgstally, self)


    def _confirm_force_tick(self):
        """
        Force a tick when user clicks button
        """
        answer = askyesno(title="Confirm FORCE a New Tick", message="This will move your current activity into the previous tick, and clear activity for the current tick.\n\nWARNING: It is not usually necessary to force a tick. Only do this if you know FOR CERTAIN there has been a tick but BGS-Tally is not showing it.\n\nAre you sure that you want to do this?", default="no")
        if answer: self.bgstally.new_tick(True, UpdateUIPolicy.IMMEDIATE)
