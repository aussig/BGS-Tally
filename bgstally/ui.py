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
from ttkHyperlinkLabel import HyperlinkLabel

from thirdparty.tksheet import Sheet
from bgstally.activity import Activity
from bgstally.constants import FOLDER_ASSETS, FONT_HEADING_2, FONT_SMALL, CheckStates, DiscordActivity, DiscordPostStyle, UpdateUIPolicy
from bgstally.debug import Debug
from bgstally.widgets import EntryPlus
from bgstally.windows.activity import WindowActivity
from bgstally.windows.api import WindowAPI
from bgstally.windows.cmdrs import WindowCMDRs
from bgstally.windows.fleetcarrier import WindowFleetCarrier
from bgstally.windows.legend import WindowLegend
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
        self.frame = None

        self.image_blank = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "blank.png"))
        self.image_button_dropdown_menu = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "button_dropdown_menu.png"))
        self.image_button_cmdrs = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "button_cmdrs.png"))
        self.image_button_carrier = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "button_carrier.png"))

        self.indicate_activity:bool = False
        self.report_system_address:str = None

        # Single-instance windows
        self.window_cmdrs:WindowCMDRs = WindowCMDRs(self.bgstally)
        self.window_fc:WindowFleetCarrier = WindowFleetCarrier(self.bgstally)
        self.window_legend:WindowLegend = WindowLegend(self.bgstally)
        # TODO: When we support multiple APIs, this will no longer be a single instance window
        self.window_api:WindowAPI = WindowAPI(self.bgstally, self.bgstally.api_manager.apis[0])

        self.thread: Optional[Thread] = Thread(target=self._worker, name="BGSTally UI worker")
        self.thread.daemon = True
        self.thread.start()


    def shut_down(self):
        """
        Shut down all worker threads.
        """


    def get_plugin_frame(self, parent_frame:tk.Frame):
        """
        Return a TK Frame for adding to the EDMC main window
        """
        self.frame = tk.Frame(parent_frame)

        current_row = 0
        tk.Label(self.frame, text="BGS Tally (Aussi)").grid(row=current_row, column=0, sticky=tk.W)
        self.label_version = HyperlinkLabel(self.frame, text=f"v{str(self.bgstally.version)}", background=nb.Label().cget('background'), url=URL_LATEST_RELEASE, underline=True)
        self.label_version.grid(row=current_row, column=1, columnspan=3 if self.bgstally.capi_fleetcarrier_available() else 2, sticky=tk.W)
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
        if self.bgstally.update_manager.update_available:
            self.label_version.configure(text="Update will be installed on shutdown", url=URL_LATEST_RELEASE, foreground='red')
        elif self.bgstally.api_manager.api_updated:
            self.label_version.configure(text="API changed, open settings to re-approve", url="", foreground='red')
        else:
            self.label_version.configure(text=f"v{str(self.bgstally.version)}", url=URL_LATEST_RELEASE, foreground='blue')

        self.label_tick.config(text=self.bgstally.tick.get_formatted())
        self.button_latest_tick.config(command=partial(self._show_activity_window, self.bgstally.activity_manager.get_current_activity()))
        if self.button_carrier is not None:
            self.button_carrier.config(state=('normal' if self.bgstally.fleet_carrier.available() else 'disabled'))


    def get_prefs_frame(self, parent_frame: tk.Frame):
        """
        Return a TK Frame for adding to the EDMC settings dialog
        """
        self.plugin_frame:tk.Frame = parent_frame
        frame = nb.Frame(parent_frame)
        # Make the second column fill available space
        frame.columnconfigure(1, weight=1)

        current_row = 1
        nb.Label(frame, text=f"BGS Tally (Aussi) v{str(self.bgstally.version)}", font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.W)
        HyperlinkLabel(frame, text="Instructions for Use", background=nb.Label().cget('background'), url=URL_WIKI, underline=True).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="General", font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW)
        nb.Checkbutton(frame, text="BGS Tally Active", variable=self.bgstally.state.Status, onvalue="Active", offvalue="Paused").grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Checkbutton(frame, text="Show Systems with Zero Activity", variable=self.bgstally.state.ShowZeroActivitySystems, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="Discord", font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW) # Don't increment row because we want the 1st radio option to be opposite title
        nb.Label(frame, text="Activity to Include").grid(row=current_row + 1, column=0, padx=10, sticky=tk.W)
        nb.Radiobutton(frame, text="BGS", variable=self.bgstally.state.DiscordActivity, value=DiscordActivity.BGS).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Radiobutton(frame, text="Thargoid War", variable=self.bgstally.state.DiscordActivity, value=DiscordActivity.THARGOIDWAR).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Radiobutton(frame, text="Both", variable=self.bgstally.state.DiscordActivity, value=DiscordActivity.BOTH).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Label(frame, text="Post Format").grid(row=current_row, column=0, padx=10, sticky=tk.W)
        nb.Radiobutton(frame, text="Modern", variable=self.bgstally.state.DiscordPostStyle, value=DiscordPostStyle.EMBED).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Radiobutton(frame, text="Legacy", variable=self.bgstally.state.DiscordPostStyle, value=DiscordPostStyle.TEXT).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Label(frame, text="Other Options").grid(row=current_row, column=0, padx=10, sticky=tk.W)
        nb.Checkbutton(frame, text="Abbreviate Faction Names", variable=self.bgstally.state.AbbreviateFactionNames, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Checkbutton(frame, text="Include Secondary INF", variable=self.bgstally.state.IncludeSecondaryInf, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Checkbutton(frame, text="Report Newly Visited System Activity By Default", variable=self.bgstally.state.EnableSystemActivityByDefault, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="Discord Webhooks", font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW); current_row += 1
        nb.Label(frame, text="Post to Discord as").grid(row=current_row, column=0, padx=10, sticky=tk.W)
        EntryPlus(frame, textvariable=self.bgstally.state.DiscordUsername).grid(row=current_row, column=1, padx=10, pady=1, sticky=tk.W); current_row += 1
        self.sheet_webhooks:Sheet = Sheet(frame, show_row_index=True, row_index_width=10, enable_edit_cell_auto_resize=False, height=140, width=880,
                                     column_width=55, header_align="left", empty_vertical=15, empty_horizontal=0, font=FONT_SMALL,
                                     show_horizontal_grid=False, show_vertical_grid=False, show_top_left=False, edit_cell_validation=False,
                                     headers=["Nickname", "Webhook URL", "BGS", "TW", "FC Mats", "FC Ops", "CMDR"])
        self.sheet_webhooks.grid(row=current_row, columnspan=2, padx=5, pady=5, sticky=tk.NSEW); current_row += 1
        self.sheet_webhooks.checkbox_column(c = [2, 3, 4, 5, 6])
        self.sheet_webhooks.set_sheet_data(data=self.bgstally.webhook_manager.get_webhooks())
        self.sheet_webhooks.column_width(column=0, width=150, redraw=False)
        self.sheet_webhooks.column_width(column=1, width=400, redraw=True)
        self.sheet_webhooks.enable_bindings(('single_select', 'row_select', 'arrowkeys', 'right_click_popup_menu', 'rc_select', 'rc_insert_row',
                            'rc_delete_row', 'copy', 'cut', 'paste', 'delete', 'undo', 'edit_cell', 'modified'))
        self.sheet_webhooks.extra_bindings('all_modified_events', func=self._webhooks_table_modified)
        nb.Label(frame, text="Add a webhook: Right-click on a row number and select 'Insert rows above / below'.", font=FONT_SMALL).grid(row=current_row, columnspan=2, padx=10, sticky=tk.NW); current_row += 1
        nb.Label(frame, text="Delete a webhook: Right-click on a row number and select 'Delete rows'.", font=FONT_SMALL).grid(row=current_row, columnspan=2, padx=10, sticky=tk.NW); current_row += 1

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="In-game Overlay", font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW)
        nb.Checkbutton(frame, text="Show In-game Overlay",
                       variable=self.bgstally.state.EnableOverlay,
                       state=self._overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1

        nb.Label(frame, text="Panels").grid(row=current_row, column=0, padx=10, sticky=tk.NW)
        overlay_options_frame:ttk.Frame = ttk.Frame(frame)
        overlay_options_frame.grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Checkbutton(overlay_options_frame, text="Current Tick",
                       variable=self.bgstally.state.EnableOverlayCurrentTick,
                       state=self._overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).pack(side=tk.LEFT)
        nb.Checkbutton(overlay_options_frame, text="Activity Indicator",
                       variable=self.bgstally.state.EnableOverlayActivity,
                       state=self._overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).pack(side=tk.LEFT)
        nb.Checkbutton(overlay_options_frame, text="Thargoid War Progress",
                       variable=self.bgstally.state.EnableOverlayTWProgress,
                       state=self._overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).pack(side=tk.LEFT)
        nb.Checkbutton(overlay_options_frame, text="System Information",
                       variable=self.bgstally.state.EnableOverlaySystem,
                       state=self._overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).pack(side=tk.LEFT)
        if self.bgstally.overlay.edmcoverlay == None:
            nb.Label(frame, text="In-game overlay support requires the separate EDMCOverlay plugin to be installed - see the instructions for more information.").grid(columnspan=2, padx=10, sticky=tk.W); current_row += 1

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="Integrations", font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW)
        tk.Button(frame, text="Configure Remote Server", command=partial(self._show_api_window, parent_frame)).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="Advanced", font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW)
        tk.Button(frame, text="FORCE Tick", command=self._confirm_force_tick, bg="red", fg="white").grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1

        return frame


    def show_system_report(self, system_address:int):
        """
        Show the system report overlay
        """
        self.indicate_activity = True
        self.report_system_address = str(system_address)


    def _webhooks_table_modified(self, event=None):
        """
        Callback for all modifications to the webhooks table

        Args:
            event (namedtuple, optional): Variables related to the callback. Defaults to None.
        """
        self.bgstally.webhook_manager.set_webhooks(self.sheet_webhooks.get_sheet_data())


    def _worker(self) -> None:
        """
        Handle thread work for overlay
        """
        Debug.logger.debug("Starting UI Worker...")

        while True:
            if config.shutting_down:
                Debug.logger.debug("Shutting down UI Worker...")
                return

            current_activity:Activity = self.bgstally.activity_manager.get_current_activity()

            # Current Tick Time
            if self.bgstally.state.enable_overlay_current_tick:
                self.bgstally.overlay.display_message("tick", f"Curr Tick: {self.bgstally.tick.get_formatted(DATETIME_FORMAT_OVERLAY)}", True)

            # Tick Warning
            minutes_delta:int = int((datetime.utcnow() - self.bgstally.tick.next_predicted()) / timedelta(minutes=1))
            if self.bgstally.state.enable_overlay_current_tick:
                if datetime.utcnow() > self.bgstally.tick.next_predicted() + timedelta(minutes = TIME_TICK_ALERT_M):
                    self.bgstally.overlay.display_message("tickwarn", f"Tick {minutes_delta}m Overdue (Estimated)", True)
                elif datetime.utcnow() > self.bgstally.tick.next_predicted():
                    self.bgstally.overlay.display_message("tickwarn", f"Past Estimated Tick Time", True, text_colour_override="#FFA500")
                elif datetime.utcnow() > self.bgstally.tick.next_predicted() - timedelta(minutes = TIME_TICK_ALERT_M):
                    self.bgstally.overlay.display_message("tickwarn", f"Within {TIME_TICK_ALERT_M}m of Next Tick (Estimated)", True, text_colour_override="yellow")

            # Activity Indicator
            if self.bgstally.state.enable_overlay_activity and self.indicate_activity:
                self.bgstally.overlay.display_indicator("indicator")
                self.indicate_activity = False

            # Thargoid War Progress Report
            if self.bgstally.state.enable_overlay_tw_progress and self.bgstally.state.system_tw_status is not None and current_activity is not None:
                current_system:dict = current_activity.get_current_system()
                if current_system:
                    progress:float = float(self.bgstally.state.system_tw_status.get('WarProgress', 0))
                    percent:float = round(progress * 100, 2)

                    self.bgstally.overlay.display_progress_bar("tw", f"TW War Progress in {current_system.get('System', 'Unknown')}: {percent}%", progress)

            # System Information
            if self.bgstally.state.enable_overlay_system and self.report_system_address is not None and current_activity is not None:
                report_system:dict = current_activity.get_system_by_address(self.report_system_address)
                if report_system is not None:
                    self.bgstally.overlay.display_message("system_info", current_activity.generate_text(DiscordActivity.BOTH, False, report_system['System']), fit_to_text=True, has_title=True)
                self.report_system_address = None

            sleep(TIME_WORKER_PERIOD_S)


    def _previous_ticks_popup(self):
        """
        Display a menu of activity for previous ticks
        """
        menu = tk.Menu(self.frame, tearoff = 0)

        activities: List = self.bgstally.activity_manager.get_previous_activities()

        for activity in activities:
            menu.add_command(label=activity.get_title(), command=partial(self._show_activity_window, activity))

        try:
            menu.tk_popup(self.button_previous_ticks.winfo_rootx(), self.button_previous_ticks.winfo_rooty())
        finally:
            menu.grab_release()


    def _show_activity_window(self, activity: Activity):
        """
        Display the activity data window, using data from the passed in activity object
        """
        WindowActivity(self.bgstally, self, activity)


    def _show_cmdr_list_window(self):
        """
        Display the CMDR list window
        """
        self.window_cmdrs.show()


    def _show_fc_window(self):
        """
        Display the Fleet Carrier Window
        """
        self.window_fc.show()


    def _show_api_window(self, parent_frame:tk.Frame):
        """
        Display the API configuration window
        """
        self.window_api.show(parent_frame)


    def show_legend_window(self):
        """
        Display the Discord Legend Window
        """
        self.window_legend.show()


    def _confirm_force_tick(self):
        """
        Force a tick when user clicks button
        """
        answer = askyesno(title="Confirm FORCE a New Tick", message="This will move your current activity into the previous tick, and clear activity for the current tick.\n\nWARNING: It is not usually necessary to force a tick. Only do this if you know FOR CERTAIN there has been a tick but BGS-Tally is not showing it.\n\nAre you sure that you want to do this?", default="no")
        if answer: self.bgstally.new_tick(True, UpdateUIPolicy.IMMEDIATE)


    def _overlay_options_state(self):
        """
        If the overlay plugin is not available, we want to disable the options so users are not interacting
        with them expecting results
        """
        return "disabled" if self.bgstally.overlay.edmcoverlay == None else "enabled"
