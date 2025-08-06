import tkinter as tk
from datetime import UTC, datetime, timedelta
from functools import partial
from os import path
from threading import Thread
from time import sleep
from tkinter import PhotoImage, ttk
from tkinter.messagebox import askyesno
from typing import List, Optional

import myNotebook as nb
from ttkHyperlinkLabel import HyperlinkLabel

from bgstally.activity import Activity
from bgstally.constants import DATETIME_FORMAT_ACTIVITY, FOLDER_ASSETS, FONT_HEADING_2, FONT_SMALL, CheckStates, DiscordActivity, UpdateUIPolicy, TAG_OVERLAY_HIGHLIGHT
from bgstally.debug import Debug
from bgstally.utils import _, available_langs, get_by_path
from bgstally.widgets import EntryPlus
from bgstally.windows.activity import WindowActivity
from bgstally.windows.api import WindowAPI
from bgstally.windows.cmdrs import WindowCMDRs
from bgstally.windows.colonisation import ColonisationWindow
from bgstally.windows.progress import ProgressWindow
from bgstally.windows.fleetcarrier import WindowFleetCarrier
from bgstally.windows.legend import WindowLegend
from bgstally.windows.objectives import WindowObjectives
from config import config
from thirdparty.tksheet import Sheet
from thirdparty.Tooltip import ToolTip

DATETIME_FORMAT_OVERLAY = "%Y-%m-%d %H:%M"
SIZE_BUTTON_PIXELS = 30
SIZE_STATUS_ICON_PIXELS = 16
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

        self.image_logo_bgstally_100 = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "logo_bgstally_100x67.png"))
        self.image_logo_bgstally_16 = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "logo_bgstally_16x16.png"))
        self.image_logo_bgstally_32 = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "logo_bgstally_32x32.png"))
        self.image_blank = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "blank.png"))
        self.image_button_dropdown_menu = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "button_dropdown_menu.png"))
        self.image_button_cmdrs = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "button_cmdrs.png"))
        self.image_button_carrier = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "button_carrier.png"))
        self.image_button_objectives = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "button_objectives.png"))
        self.image_button_colonisation = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "button_colonisation.png"))
        self.image_icon_green_tick = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_green_tick_16x16.png"))
        self.image_icon_red_cross = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_red_cross_16x16.png"))
        self.image_icon_left_arrow = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_col_left_arrow.png"))
        self.image_icon_right_arrow = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_col_right_arrow.png"))
        self.image_icon_change_view = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_col_change_view.png"))

        self.indicate_activity:bool = False
        self.report_system_address:str = None
        self.report_cmdr_data:dict = None
        self.warning:str = None

        # Single-instance windows
        self.window_cmdrs:WindowCMDRs = WindowCMDRs(self.bgstally)
        self.window_fc:WindowFleetCarrier = WindowFleetCarrier(self.bgstally)
        self.window_legend:WindowLegend = WindowLegend(self.bgstally)
        self.window_objectives:WindowObjectives = WindowObjectives(self.bgstally)
        self.window_colonisation:ColonisationWindow = ColonisationWindow(self.bgstally)
        self.window_progress:ProgressWindow = ProgressWindow(self.bgstally)

        # TODO: When we support multiple APIs, this will no longer be a single instance window
        self.window_api:WindowAPI = WindowAPI(self.bgstally, self.bgstally.api_manager.apis[0])

        # Multi-instance windows
        self.window_activity:dict = {}

        self.thread: Optional[Thread] = Thread(target=self._worker, name="BGSTally UI worker")
        self.thread.daemon = True
        self.thread.start()


    def shut_down(self):
        """
        Shut down all worker threads.
        """


    def get_plugin_frame(self, parent_frame: tk.Frame) -> tk.Frame:
        """
        Return a TK Frame for adding to the EDMC main window
        """
        self.frame: tk.Frame = tk.Frame(parent_frame)

        column_count: int = 3
        if self.bgstally.capi_fleetcarrier_available(): column_count += 1

        current_row: int = 0
        tk.Label(self.frame, image=self.image_logo_bgstally_100).grid(row=current_row, column=0, rowspan=3, sticky=tk.W)
        self.lbl_version: HyperlinkLabel = HyperlinkLabel(self.frame, text=f"v{str(self.bgstally.version)}", background=nb.Label().cget('background'), url=URL_LATEST_RELEASE, underline=True)
        self.lbl_version.grid(row=current_row, column=1, columnspan=column_count, sticky=tk.W)
        current_row += 1
        frm_status: tk.Frame = tk.Frame(self.frame)
        frm_status.grid(row=current_row, column=1, columnspan=column_count, sticky=tk.W)
        self.lbl_status: tk.Label = tk.Label(frm_status, text=_("{plugin_name} Status:").format(plugin_name=self.bgstally.plugin_name)) # LANG: Main window label
        self.lbl_status.pack(side=tk.LEFT)
        self.lbl_active: tk.Label = tk.Label(frm_status, width=SIZE_STATUS_ICON_PIXELS, height=SIZE_STATUS_ICON_PIXELS, image=self.image_icon_green_tick if self.bgstally.state.Status.get() == CheckStates.STATE_ON else self.image_icon_red_cross)
        self.lbl_active.pack(side=tk.LEFT)
        current_row += 1
        self.lbl_tick: tk.Label = tk.Label(self.frame, text=_("Last BGS Tick:") + " " + self.bgstally.tick.get_formatted()) # LANG: Main window label
        self.lbl_tick.grid(row=current_row, column=1, columnspan=column_count, sticky=tk.W)
        current_row += 1
        current_column: int = 0
        self.btn_latest_tick: tk.Button = tk.Button(self.frame, text=_("Latest BGS Tally"), height=SIZE_BUTTON_PIXELS-2, image=self.image_blank, compound=tk.RIGHT, command=partial(self._show_activity_window, self.bgstally.activity_manager.get_current_activity())) # LANG: Button label
        self.btn_latest_tick.grid(row=current_row, column=current_column, padx=3)
        current_column += 1
        self.btn_previous_ticks: tk.Button = tk.Button(self.frame, text=_("Previous BGS Tallies") + " ", height=SIZE_BUTTON_PIXELS-2, image=self.image_button_dropdown_menu, compound=tk.RIGHT, command=self._previous_ticks_popup) # LANG: Button label
        self.btn_previous_ticks.grid(row=current_row, column=current_column, padx=3, sticky=tk.W)
        current_column += 1
        self.btn_cmdrs: tk.Button = tk.Button(self.frame, image=self.image_button_cmdrs, height=SIZE_BUTTON_PIXELS, width=SIZE_BUTTON_PIXELS, command=self._show_cmdr_list_window)
        self.btn_cmdrs.grid(row=current_row, column=current_column, padx=3)
        current_column += 1
        ToolTip(self.btn_cmdrs, text=_("Show CMDR information window")) # LANG: Main window tooltip
        if self.bgstally.capi_fleetcarrier_available():
            self.btn_carrier: tk.Button = tk.Button(self.frame, image=self.image_button_carrier, state=('normal' if self.bgstally.fleet_carrier.available() else 'disabled'), height=SIZE_BUTTON_PIXELS, width=SIZE_BUTTON_PIXELS, command=self._show_fc_window)
            self.btn_carrier.grid(row=current_row, column=current_column, padx=3)
            ToolTip(self.btn_carrier, text=_("Show fleet carrier window")) # LANG: Main window tooltip
            current_column += 1
        else:
            self.btn_carrier: tk.Button = None

        self.btn_objectives: tk.Button = tk.Button(self.frame, image=self.image_button_objectives, state=('normal' if self.bgstally.objectives_manager.objectives_available() else 'disabled'), height=SIZE_BUTTON_PIXELS, width=SIZE_BUTTON_PIXELS, command=self._show_objectives_window)
        self.btn_objectives.grid(row=current_row, column=current_column, padx=3)
        ToolTip(self.btn_objectives, text=_("Show objectives / missions window")) # LANG: Main window tooltip
        current_column += 1

        self.btn_colonisation: tk.Button = tk.Button(self.frame, image=self.image_button_colonisation, height=SIZE_BUTTON_PIXELS, width=SIZE_BUTTON_PIXELS, command=self._show_colonisation_window)
        self.btn_colonisation.grid(row=current_row, column=current_column, padx=3)
        ToolTip(self.btn_colonisation, text=_("Show colonisation window")) # LANG: Main window tooltip
        current_column += 1
        current_row += 1

        self.window_progress.create_frame(self.frame, current_row, column_count)

        return self.frame


    def update_plugin_frame(self):
        """
        Update the tick time label, current activity button, carrier button and all labels in the plugin frame
        """
        self.btn_latest_tick.configure(text=_("Latest BGS Tally")) # LANG: Button label
        self.btn_previous_ticks.configure(text=_("Previous BGS Tallies") + " ") # LANG: Button label
        self.lbl_active.configure(image=self.image_icon_green_tick if self.bgstally.state.Status.get() == CheckStates.STATE_ON else self.image_icon_red_cross)
        self.lbl_tick.configure(text=_("Last BGS Tick:") + " " + self.bgstally.tick.get_formatted()) # LANG: Main window label

        if self.bgstally.update_manager.update_available:
            self.lbl_version.configure(text=_("Update will be installed on shutdown"), url=URL_LATEST_RELEASE, foreground='red') # LANG: Main window label
        elif self.bgstally.api_manager.api_updated:
            self.lbl_version.configure(text=_("API changed, open settings to re-approve"), url="", foreground='red') # LANG: Main window label
        else:
            self.lbl_version.configure(text=f"v{str(self.bgstally.version)}", url=URL_LATEST_RELEASE, foreground='blue')

        self.btn_latest_tick.config(command=partial(self._show_activity_window, self.bgstally.activity_manager.get_current_activity()))
        if self.btn_carrier is not None:
            self.btn_carrier.config(state=('normal' if self.bgstally.fleet_carrier.available() else 'disabled'))
        self.btn_objectives.config(state=('normal' if self.bgstally.objectives_manager.objectives_available() else 'disabled'))


    def get_prefs_frame(self, parent_frame: tk.Frame):
        """
        Return a TK Frame for adding to the EDMC settings dialog
        """
        self.plugin_frame:tk.Frame = parent_frame
        frame = nb.Frame(parent_frame)
        # Make the second column fill available space
        frame.columnconfigure(1, weight=1)

        current_row = 1
        nb.Label(frame, text=f"{self.bgstally.plugin_name} v{str(self.bgstally.version)}", font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.W)
        HyperlinkLabel(frame, text=_("Instructions for Use"), background=nb.Label().cget('background'), url=URL_WIKI, underline=True).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences label

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text=_("General Options"), font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW) # LANG: Preferences heading
        nb.Checkbutton(frame, text=_("{plugin_name} Active").format(plugin_name=self.bgstally.plugin_name), variable=self.bgstally.state.Status, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.update_plugin_frame).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences checkbox label
        nb.Checkbutton(frame, text=_("Show Systems with Zero Activity"), variable=self.bgstally.state.ShowZeroActivitySystems, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences checkbox label

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text=_("Discord Options"), font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW) # Don't increment row because we want the 1st radio option to be opposite title # LANG: Preferences heading
        nb.Checkbutton(frame, text=_("Abbreviate Faction Names"), variable=self.bgstally.state.AbbreviateFactionNames, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.bgstally.state.refresh).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences checkbox label
        nb.Checkbutton(frame, text=_("Show Detailed INF"), variable=self.bgstally.state.DetailedInf, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.bgstally.state.refresh).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences checkbox label
        nb.Checkbutton(frame, text=_("Include Secondary INF"), variable=self.bgstally.state.IncludeSecondaryInf, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.bgstally.state.refresh).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences checkbox label
        nb.Checkbutton(frame, text=_("Show Detailed Trade"), variable=self.bgstally.state.DetailedTrade, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.bgstally.state.refresh).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences checkbox label
        nb.Checkbutton(frame, text=_("Report Newly Visited System Activity By Default"), variable=self.bgstally.state.EnableSystemActivityByDefault, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences checkbox label
        nb.Checkbutton(frame, text=_("Automatically Post BGS and TW Activity"), variable=self.bgstally.state.DiscordBGSTWAutomatic, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.bgstally.state.refresh).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences checkbox label
        nb.Label(frame, text=_("Post to Discord as")).grid(row=current_row, column=0, padx=10, sticky=tk.W) # LANG: Preferences label
        EntryPlus(frame, textvariable=self.bgstally.state.DiscordUsername).grid(row=current_row, column=1, padx=10, pady=1, sticky=tk.W); current_row += 1
        nb.Label(frame, text=_("Discord Avatar URL")).grid(row=current_row, column=0, padx=10, sticky=tk.W) # LANG: Preferences label
        EntryPlus(frame, textvariable=self.bgstally.state.DiscordAvatarURL, width=80).grid(row=current_row, column=1, padx=10, pady=1, sticky=tk.W); current_row += 1
        self.languages: dict[str: str] = available_langs()
        self.language:tk.StringVar = tk.StringVar(value=self.languages.get(self.bgstally.state.discord_lang, _('Default')))
        self.formatters: dict[str: str] = self.bgstally.formatter_manager.get_formatters()
        self.formatter:tk.StringVar = tk.StringVar(value=self.formatters.get(self.bgstally.state.discord_formatter, _('Default')))
        nb.Label(frame, text=_("Language for Discord Posts")).grid(row=current_row, column=0, padx=10, sticky=tk.W) # LANG: Preferences label
        nb.OptionMenu(frame, self.language, self.language.get(), *self.languages.values(), command=self._language_modified).grid(row=current_row, column=1, padx=10, pady=1, sticky=tk.W); current_row += 1
        nb.Label(frame, text=_("Format for Discord Posts")).grid(row=current_row, column=0, padx=10, sticky=tk.W) # LANG: Preferences label
        nb.OptionMenu(frame, self.formatter, self.formatter.get(), *sorted(self.formatters.values()), command=self._formatter_modified).grid(row=current_row, column=1, padx=10, pady=1, sticky=tk.W); current_row += 1

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text=_("Discord Webhooks"), font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW); current_row += 1 # LANG: Preferences heading
        ui_scaling:float = self.frame.tk.call('tk', 'scaling')
        sheet_headings:list = ["UUID",
                               _("Nickname"), # LANG: Preferences table heading
                               _("Webhook URL"), # LANG: Preferences table heading
                               "BGS",
                               "TW",
                               _("FC C/M"), # LANG: Preferences table heading, abbreviation for fleet carrier commodities / materials
                               _("FC Ops"), # LANG: Preferences table heading, abbreviation for fleet carrier operations
                               "CMDR"]
        self.sheet_webhooks:Sheet = Sheet(frame, show_row_index=True, row_index_width=10, cell_auto_resize_enabled=False, height=140, width=880,
                                     column_width=int(55 * ui_scaling), header_align="left", empty_vertical=15, empty_horizontal=0, font=FONT_SMALL,
                                     show_horizontal_grid=True, show_vertical_grid=False, show_top_left=False,
                                     headers=sheet_headings)
        self.sheet_webhooks.grid(row=current_row, columnspan=2, padx=5, pady=5, sticky=tk.NSEW); current_row += 1
        self.sheet_webhooks.hide_columns(columns=[0])                       # Visible column indexes
        self.sheet_webhooks.checkbox_column(c=[3, 4, 5, 6, 7])              # Data column indexes
        self.sheet_webhooks.set_sheet_data(data=self.bgstally.webhook_manager.get_webhooks_as_list())
        self.sheet_webhooks.column_width(column=0, width=int(150 * ui_scaling), redraw=False) # Visible column indexes
        self.sheet_webhooks.column_width(column=1, width=int(400 * ui_scaling), redraw=True)  # Visible column indexes
        self.sheet_webhooks.enable_bindings(('single_select', 'row_select', 'arrowkeys', 'right_click_popup_menu', 'rc_select', 'rc_insert_row',
                            'rc_delete_row', 'copy', 'cut', 'paste', 'delete', 'undo', 'edit_cell', 'modified'))
        self.sheet_webhooks.extra_bindings('all_modified_events', func=self._webhooks_table_modified)
        nb.Label(frame, text=_("To add a webhook: Right-click on a row number and select 'Insert rows above / below'."), font=FONT_SMALL).grid(row=current_row, columnspan=2, padx=10, sticky=tk.NW); current_row += 1
        nb.Label(frame, text=_("To delete a webhook: Right-click on a row number and select 'Delete rows'."), font=FONT_SMALL).grid(row=current_row, columnspan=2, padx=10, sticky=tk.NW); current_row += 1

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text=_("In-game Overlay"), font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW) # LANG: Preferences heading
        nb.Checkbutton(frame, text=_("Show In-game Overlay"), # LANG: Preferences checkbox label
                       variable=self.bgstally.state.EnableOverlay,
                       state=self.overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1

        nb.Label(frame, text=_("Panels")).grid(row=current_row, column=0, padx=10, sticky=tk.NW)
        overlay_options_frame_1:ttk.Frame = ttk.Frame(frame)
        overlay_options_frame_1.grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Checkbutton(overlay_options_frame_1, text=_("Activity Indicator"), # LANG: Preferences checkbox label
                       variable=self.bgstally.state.EnableOverlayActivity,
                       state=self.overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).pack(side=tk.LEFT)
        nb.Checkbutton(overlay_options_frame_1, text=_("CMDR Info"), # LANG: Preferences checkbox label
                       variable=self.bgstally.state.EnableOverlayCMDR,
                       state=self.overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).pack(side=tk.LEFT)
        nb.Checkbutton(overlay_options_frame_1, text=_("Colonisation"), # LANG: Preferences checkbox label
                       variable=self.bgstally.state.EnableOverlayColonisation,
                       state=self.overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).pack(side=tk.LEFT)
        nb.Checkbutton(overlay_options_frame_1, text=_("Current Tick"), # LANG: Preferences checkbox label
                       variable=self.bgstally.state.EnableOverlayCurrentTick,
                       state=self.overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).pack(side=tk.LEFT)
        nb.Checkbutton(overlay_options_frame_1, text=_("Objectives"), # LANG: Preferences checkbox label
                       variable=self.bgstally.state.EnableOverlayObjectives,
                       state=self.overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).pack(side=tk.LEFT)
        overlay_options_frame_2:ttk.Frame = ttk.Frame(frame)
        overlay_options_frame_2.grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        nb.Checkbutton(overlay_options_frame_2, text=_("System Information"), # LANG: Preferences checkbox label
                       variable=self.bgstally.state.EnableOverlaySystem,
                       state=self.overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).pack(side=tk.LEFT)
        nb.Checkbutton(overlay_options_frame_2, text=_("Thargoid War Progress"), # LANG: Preferences checkbox label
                       variable=self.bgstally.state.EnableOverlayTWProgress,
                       state=self.overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).pack(side=tk.LEFT)
        nb.Checkbutton(overlay_options_frame_2, text=_("Warnings"), # LANG: Preferences checkbox label
                       variable=self.bgstally.state.EnableOverlayWarning,
                       state=self.overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).pack(side=tk.LEFT)

        if self.bgstally.overlay.edmcoverlay == None:
            nb.Label(frame, text=_("In-game overlay support requires the separate EDMCOverlay plugin to be installed - see the instructions for more information.")).grid(columnspan=2, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences label

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text=_("Integrations"), font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW) # LANG: Preferences heading
        tk.Button(frame, text=_("Configure Remote Server"), command=partial(self._show_api_window, parent_frame)).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences button label

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text=_("Advanced"), font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW) # LANG: Preferences heading
        tk.Button(frame, text=_("Force Tick"), command=self._confirm_force_tick, bg="red", fg="white").grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences button label

        return frame


    def save_prefs(self):
        """
        Preferences frame has been saved (from EDMC core or any plugin)
        """
        self.update_plugin_frame()


    def show_system_report(self, system_address: int):
        """
        Show the system report overlay
        """
        self.indicate_activity = True
        self.report_system_address = str(system_address)


    def show_cmdr_report(self, cmdr_data: dict):
        """Show the CMDR report overlay

        Args:
            cmdr_data (dict): Information about the CMDR
        """
        self.indicate_activity = True
        self.report_cmdr_data = cmdr_data


    def show_warning(self, warning: str):
        """
        Show the warning overlay
        """
        self.warning = warning


    def show_legend_window(self):
        """
        Display the Discord Legend Window
        """
        self.window_legend.show()


    def overlay_options_state(self):
        """
        If the overlay plugin is not available, we want to disable the options so users are not interacting
        with them expecting results
        """
        return "disabled" if self.bgstally.overlay.edmcoverlay == None else "enabled"


    def _webhooks_table_modified(self, event=None):
        """
        Callback for all modifications to the webhooks table

        Args:
            event (namedtuple, optional): Variables related to the callback. Defaults to None.
        """
        self.bgstally.webhook_manager.set_webhooks_from_list(self.sheet_webhooks.get_sheet_data())


    def _language_modified(self, event=None):
        """Callback for change in language dropdown

        Args:
            event (_type_, optional): Variable related to the callback. Defaults to None.
        """
        langs_by_name: dict = {v: k for k, v in self.languages.items()}  # Codes by name
        self.bgstally.state.discord_lang = langs_by_name.get(self.language.get()) or ''  # or '' used here due to Default being None above


    def _formatter_modified(self, event=None):
        """Callback for change in formatter dropdown

        Args:
            event (_type_, optional): Variable related to the callback. Defaults to None.
        """
        formatters_by_name: dict = {v: k for k, v in self.formatters.items()}
        self.bgstally.state.discord_formatter = formatters_by_name.get(self.formatter.get())


    def _worker(self) -> None:
        """
        Handle thread work for overlay
        """
        Debug.logger.debug("Starting UI Worker...")

        while True:
            if config.shutting_down:
                Debug.logger.debug("Shutting down UI Worker...")
                return

            current_activity: Activity = self.bgstally.activity_manager.get_current_activity()

            # Current Galaxy and System Tick Times
            if self.bgstally.state.enable_overlay_current_tick:
                self.bgstally.overlay.display_message("tick", _("Galaxy Tick: {tick_time}").format(tick_time=self.bgstally.tick.get_formatted(DATETIME_FORMAT_OVERLAY)), True) # LANG: Overlay galaxy tick message

                if current_activity is not None:
                    current_system: dict = current_activity.get_current_system()
                    system_tick: str = current_system.get('TickTime')

                    if system_tick is not None and system_tick != "":
                        system_tick_datetime: datetime = datetime.strptime(system_tick, DATETIME_FORMAT_ACTIVITY)
                        system_tick_datetime = system_tick_datetime.replace(tzinfo=UTC)

                        tick_text: str = _("System Tick: {tick_time}").format(tick_time=self.bgstally.tick.get_formatted(DATETIME_FORMAT_OVERLAY, tick_time = system_tick_datetime)) # LANG: Overlay system tick message

                        if system_tick_datetime < self.bgstally.tick.tick_time:
                            self.bgstally.overlay.display_message("system_tick", tick_text, True, text_colour_override="#FF0000")
                        else:
                            self.bgstally.overlay.display_message("system_tick", tick_text, True)

            # Tick Warning
            minutes_delta:int = int((datetime.now(UTC) - self.bgstally.tick.next_predicted()) / timedelta(minutes=1))
            if self.bgstally.state.enable_overlay_current_tick:
                if datetime.now(UTC) > self.bgstally.tick.next_predicted() + timedelta(minutes = TIME_TICK_ALERT_M):
                    self.bgstally.overlay.display_message("tickwarn", _("Tick {minutes_delta}m Overdue (Estimated)").format(minutes_delta=minutes_delta), True) # Overlay tick message
                elif datetime.now(UTC) > self.bgstally.tick.next_predicted():
                    self.bgstally.overlay.display_message("tickwarn", _("Past Estimated Tick Time"), True, text_colour_override="#FFA500") # Overlay tick message
                elif datetime.now(UTC) > self.bgstally.tick.next_predicted() - timedelta(minutes = TIME_TICK_ALERT_M):
                    self.bgstally.overlay.display_message("tickwarn", _("Within {minutes_to_tick}m of Next Tick (Estimated)").format(minutes_to_tick=TIME_TICK_ALERT_M), True, text_colour_override="yellow") # Overlay tick message

            # Activity Indicator
            if self.bgstally.state.enable_overlay_activity and self.indicate_activity:
                self.bgstally.overlay.display_indicator("indicator")
                self.indicate_activity = False

            # Thargoid War Progress Report
            if self.bgstally.state.enable_overlay_tw_progress and current_activity is not None:
                current_system:dict = current_activity.get_current_system()
                if current_system and current_system.get('tw_status') is not None:
                    progress:float = float(get_by_path(current_system, ['tw_status', 'WarProgress'], 0))
                    percent:float = round(progress * 100, 2)

                    self.bgstally.overlay.display_progress_bar("tw", _("TW War Progress in {current_system}: {percent}%").format(current_system=current_system.get('System', 'Unknown'), percent=percent), progress) # Overlay TW report message

            # System Information
            if self.bgstally.state.enable_overlay_system and current_activity is not None:
                if self.report_system_address is not None:
                    # Report recent activity in a designated system, overrides pinned systems
                    report_system:dict = current_activity.get_system_by_address(self.report_system_address)
                    if report_system is not None:
                        self.bgstally.overlay.display_message("system_info", self.bgstally.formatter_manager.get_default_formatter().get_overlay(current_activity, DiscordActivity.BOTH, [report_system['System']], lang=self.bgstally.state.discord_lang), fit_to_text=True)
                    self.report_system_address = None
                else:
                    # Report pinned systems
                    pinned_systems:list = current_activity.get_pinned_systems()
                    self.bgstally.overlay.display_message("system_info", self.bgstally.formatter_manager.get_default_formatter().get_overlay(current_activity, DiscordActivity.BOTH, pinned_systems, lang=self.bgstally.state.discord_lang), fit_to_text=True, ttl_override=TIME_WORKER_PERIOD_S + 2) # Overlay pinned systems message

            # CMDR Information
            if self.bgstally.state.enable_overlay_cmdr and self.report_cmdr_data is not None:
                # Report recent interaction with a CMDR
                display_text: str = TAG_OVERLAY_HIGHLIGHT + self.bgstally.target_manager.get_human_readable_reason(self.report_cmdr_data.get('Reason', 0), False) + ": " + self.report_cmdr_data.get('TargetName', _("Unknown")) + "\n" # LANG: Overlay CMDR information report message
                display_text += _("In system: {system}").format(system=self.report_cmdr_data.get('System', _("Unknown"))) + "  " # LANG: Overlay CMDR information report message
                display_text += _("Squadron ID: {squadron}").format(squadron=self.report_cmdr_data.get('SquadronID', _("Unknown"))) + "\n" # LANG: Overlay CMDR information report message
                display_text += _("In ship: {ship}").format(ship=self.report_cmdr_data.get('Ship', _("Unknown"))) + "  " # LANG: Overlay CMDR information report message
                display_text += _("Legal status: {legal}").format(legal=self.report_cmdr_data.get('LegalStatus', _("Unknown"))) + "\n" # LANG: Overlay CMDR information report message
                if 'ranks' in self.report_cmdr_data: display_text += _("INARA INFORMATION AVAILABLE") # LANG: Overlay CMDR information report message

                self.bgstally.overlay.display_message("cmdr_info", display_text, fit_to_text=True)
                self.report_cmdr_data = None

            # Warning
            if self.bgstally.state.enable_overlay_warning and self.warning is not None:
                self.bgstally.overlay.display_message("warning", self.warning, fit_to_text=True)
                self.warning = None

            # Objectives
            if self.bgstally.state.enable_overlay_objectives and self.bgstally.objectives_manager.get_objectives() != []:
                objectives_text: str = self.bgstally.objectives_manager.get_human_readable_objectives(False)
                self.bgstally.overlay.display_message("objectives", objectives_text, fit_to_text=True, title=self.bgstally.objectives_manager.get_title())

            # Colonisation
            if self.bgstally.state.enable_overlay_colonisation:
                colonisation_text: str = self.window_progress.as_text(False)  # Placeholder for actual colonisation text
                self.bgstally.overlay.display_message("colonisation", colonisation_text, fit_to_text=True)  # Placeholder for actual colonisation title

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
            menu.tk_popup(self.btn_previous_ticks.winfo_rootx(), self.btn_previous_ticks.winfo_rooty())
        finally:
            menu.grab_release()


    def _show_activity_window(self, activity: Activity):
        """
        Display the appropriate activity data window, using data from the passed in activity object
        """
        existing_activity_window:WindowActivity = self.window_activity.get(activity.tick_id)
        if existing_activity_window is not None:
            existing_activity_window.show(activity)
        else:
            self.window_activity[activity.tick_id] = WindowActivity(self.bgstally, self, activity)


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


    def _show_objectives_window(self):
        """Display the Objectives Window
        """
        self.window_objectives.show()


    def _show_api_window(self, parent_frame:tk.Frame):
        """
        Display the API configuration window
        """
        self.window_api.show(parent_frame)

    def _show_colonisation_window(self):
        """
        Display the Colonisation Window
        """
        self.window_colonisation.show()

    def _confirm_force_tick(self):
        """
        Force a tick when user clicks button
        """
        message:str = _("This will move your current activity into the previous tick, and clear activity for the current tick.") + "\n\n" # LANG: Preferences force tick popup text
        message += _("WARNING: It is not usually necessary to force a tick. Only do this if you know FOR CERTAIN there has been a tick but {plugin_name} is not showing it.").format(plugin_name=self.bgstally.plugin_name) + "\n\n" # LANG: Preferences force tick popup text
        message += _("Are you sure that you want to do this?") # LANG: Preferences force tick text

        answer = askyesno(title=_("Confirm Force a New Tick"), message=message, default="no") # LANG: Preferences force tick popup title
        if answer: self.bgstally.new_tick(True, UpdateUIPolicy.IMMEDIATE)
