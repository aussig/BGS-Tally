import csv
import tkinter as tk
from datetime import UTC, datetime, timedelta
from functools import partial
from os import path
from threading import Thread
from time import sleep
from tkinter import PhotoImage, ttk
from tkinter.messagebox import askyesno
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from bgstally.bgstally import BGSTally
    from bgstally.state import State

import myNotebook as nb  # type: ignore
from plugins.common_coreutils import api_keys_label_common, show_pwd_var_common # type: ignore
from ttkHyperlinkLabel import HyperlinkLabel  # type: ignore

from config import config # type: ignore
import edmc_data # type: ignore

from bgstally.activity import STATES_ELECTION, STATES_WAR, Activity
from bgstally.constants import (DATETIME_FORMAT_ACTIVITY, FOLDER_ASSETS, FOLDER_DATA, FONT_HEADING_2, FONT_SMALL,
                                TAG_OVERLAY_HIGHLIGHT, CheckStates, DiscordActivity, FavouriteActivity, UpdateUIPolicy,
                                Vehicle, ShipState, UIState)
from bgstally.debug import Debug
from bgstally.utils import _, available_langs, catch_exceptions, get_by_path, get_localised_filepath, human_format
from bgstally.windows.activity import WindowActivity
from bgstally.windows.api import WindowAPI
from bgstally.windows.cmdrs import WindowCMDRs
from bgstally.windows.colonisation import ColonisationWindow
from bgstally.windows.fleetcarrier import WindowFleetCarrier
from bgstally.windows.legend import WindowLegend
from bgstally.windows.objectives import WindowObjectives
from bgstally.windows.objectives_overlay_settings import WindowObjectivesOverlaySettings
from bgstally.windows.progress import ProgressWindow
from thirdparty.tksheet import Sheet
from thirdparty.Tooltip import ToolTip

DATETIME_FORMAT_OVERLAY = "%Y-%m-%d %H:%M"
FILENAME_COMMODITIES_CSV = "commodity.csv"
FILENAME_RARE_COMMODITIES_CSV = "rare_commodity.csv"
SIZE_BUTTON_PIXELS = 30
SIZE_STATUS_ICON_PIXELS = 16
TIME_WORKER_PERIOD_S = 2
TIME_TICK_ALERT_M = 60
TIME_TICK_OBJECTIVES_REFRESH_S = 30
URL_LATEST_RELEASE = "https://github.com/aussig/BGS-Tally/releases/latest"
URL_WIKI = "https://github.com/aussig/BGS-Tally/wiki"

class UI:
    """
    Display the user's activity
    """

    def __init__(self, bgstally: 'BGSTally'):
        self.bgstally: BGSTally = bgstally
        self.frame: tk.Frame|None = None

        self.image_logo_bgstally_100 = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "logo_bgstally_100x67.png"))
        self.image_logo_bgstally_16 = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "logo_bgstally_16x16.png"))
        self.image_logo_bgstally_32 = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "logo_bgstally_32x32.png"))
        self.image_logo_edgis = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "logo_edgis.png"))
        self.image_logo_inara = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "logo_inara.png"))

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
        self.image_icon_edit = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_col_edit.png"))
        self.image_icon_info = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_col_info.png"))
        self.image_icon_world = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_col_world.png"))
        self.image_icon_delete = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_col_delete.png"))
        self.image_icon_note = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_col_note.png"))
        self.image_icon_base = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_col_base.png"))
        self.image_icon_refresh = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_col_refresh.png"))

        self.indicate_activity:bool = False
        self.activity_system_address:str|None = None
        self.info_system_address:str|None = None
        self.info_station:dict[str, str]|None = None
        self.report_cmdr_data:dict|None = None
        self.warning:str|None = None

        # RavenColonial API key management
        self.apikey:nb.EntryMenu
        self.apikey_label:tk.Label

        # Show/hide based on UI state
        self.show_colonisation_overlay:bool = True
        self.show_carrier_overlay:bool = True

        # Single-instance windows
        self.window_cmdrs:WindowCMDRs = WindowCMDRs(self.bgstally)
        self.window_fc:WindowFleetCarrier = WindowFleetCarrier(self.bgstally)
        self.window_legend:WindowLegend = WindowLegend(self.bgstally)
        self.window_objectives:WindowObjectives = WindowObjectives(self.bgstally)
        self.window_objectives_overlay_settings:WindowObjectivesOverlaySettings = WindowObjectivesOverlaySettings(self.bgstally)
        self.window_colonisation:ColonisationWindow = ColonisationWindow(self.bgstally)
        self.window_progress:ProgressWindow = ProgressWindow(self.bgstally)

        # TODO: When we support multiple APIs, this will no longer be a single instance window
        self.window_api:WindowAPI = WindowAPI(self.bgstally, self.bgstally.api_manager.apis[0])

        # Multi-instance windows
        self.window_activity:dict = {}

        self.thread: Optional[Thread] = Thread(target=self._worker, name="BGSTally UI worker")
        self.thread.daemon = True
        self.thread.start()

        # Localisation lookups
        self._load_commodities()


    def shut_down(self):
        """
        Shut down all worker threads.
        """


    def get_plugin_frame(self, parent_frame: tk.Frame) -> tk.Frame:
        """
        Return a TK Frame for adding to the EDMC main window
        """
        self.frame = tk.Frame(parent_frame)

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
            self.btn_carrier: tk.Button|None = tk.Button(self.frame, image=self.image_button_carrier, state=('normal' if self.bgstally.fleet_carrier.available() else 'disabled'), height=SIZE_BUTTON_PIXELS, width=SIZE_BUTTON_PIXELS, command=self._show_fc_window)
            self.btn_carrier.grid(row=current_row, column=current_column, padx=3)
            ToolTip(self.btn_carrier, text=_("Show fleet carrier window")) # LANG: Main window tooltip
            current_column += 1
        else:
            self.btn_carrier: tk.Button|None = None

        self.btn_objectives: tk.Button = tk.Button(self.frame, image=self.image_button_objectives, state=('normal' if self.bgstally.objectives_manager.objectives_available() else 'disabled'), height=SIZE_BUTTON_PIXELS, width=SIZE_BUTTON_PIXELS, command=self._show_objectives_window)
        self.btn_objectives.grid(row=current_row, column=current_column, padx=3)
        ToolTip(self.btn_objectives, text=_("Show objectives / missions window")) # LANG: Main window tooltip
        current_column += 1

        self.btn_colonisation: tk.Button = tk.Button(self.frame, image=self.image_button_colonisation, state=('normal' if self.bgstally.state.enable_colonisation == True else 'disabled'), height=SIZE_BUTTON_PIXELS, width=SIZE_BUTTON_PIXELS, command=self._show_colonisation_window)
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

        self.btn_colonisation.config(state=('normal' if self.bgstally.state.enable_colonisation == True else 'disabled'))
        self.window_progress.update_display()


    def save_prefs(self):
        """
        Preferences frame has been saved (from EDMC core or any plugin)
        """
        self.update_plugin_frame()
        self._load_commodities()


    def show_system_info(self, system_address: int):
        """
        Show the system info overlay
        """
        self.info_system_address = str(system_address)


    def show_station_info(self, station: str, station_faction: str):
        """Show the station info overlay

        Args:
            station (str): The station name
            station_faction (str): The station controlling faction name
        """
        self.info_station = {"station": station, "faction": station_faction}


    def show_system_activity(self, system_address: str):
        """
        Show the system activity overlay
        """
        self.indicate_activity = True
        self.activity_system_address = str(system_address)


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


    def _load_commodities(self):
        """
        Load the commodity and rare_commodity CSV files containing full list of commodities. We build a dict where the key is the commodity
        internal name from the 'symbol' column in the CSV, lowercased, and the value is a dict containing the other fields (ID, Category, Name)
        where Name is localised.

        The CSV files are sourced from the EDCD FDevIDs project https://github.com/EDCD/FDevIDs and should be updated occasionally, along with the
        localised versions in the L10n folder. Note that commodity.csv has an extra column 'InaraID' which we maintain.
        """
        self.commodities = {}
        filepath: str|None = get_localised_filepath(FILENAME_COMMODITIES_CSV, path.join(self.bgstally.plugin_dir, FOLDER_DATA))
        if filepath is None: return

        try:
            with open(filepath, encoding = 'utf-8') as csv_file_handler:
                csv_reader = csv.DictReader(csv_file_handler)

                for rows in csv_reader:
                    self.commodities[rows.get('symbol', "").lower()] = {'ID': rows.get('id', ""), 'InaraID': rows.get('inara_id', ""), 'Category': rows.get('category', ""), 'Name': rows.get('name', "")}
        except Exception as e:
                Debug.logger.error(f"Unable to load {filepath}")

        rare_filepath: str|None = get_localised_filepath(FILENAME_RARE_COMMODITIES_CSV, path.join(self.bgstally.plugin_dir, FOLDER_DATA))
        if rare_filepath is None: return

        try:
            with open(rare_filepath, encoding = 'utf-8') as csv_file_handler:
                csv_reader = csv.DictReader(csv_file_handler)

                for rows in csv_reader:
                    self.commodities[rows.get('symbol', "").lower()] = {'ID': rows.get('id', ""), 'Category': rows.get('category', ""), 'Name': rows.get('name', "")}
        except Exception as e:
                Debug.logger.error(f"Unable to load {rare_filepath}")


    @catch_exceptions
    def _worker(self) -> None:
        """
        Handle thread work for overlay
        """
        Debug.logger.debug("Starting UI Worker...")

        while True:
            if config.shutting_down:
                Debug.logger.debug("Shutting down UI Worker...")
                return

            sleep(TIME_WORKER_PERIOD_S)

            current_activity:Activity|None = self.bgstally.activity_manager.get_current_activity()

            # Current Galaxy and System Tick Times
            if self.bgstally.state.enable_overlay_current_tick:
                self.bgstally.overlay.display_message("tick", _("Galaxy Tick: {tick_time}").format(tick_time=self.bgstally.tick.get_formatted(DATETIME_FORMAT_OVERLAY)), True) # LANG: Overlay galaxy tick message

                if current_activity is not None:
                    current_system: dict|None = current_activity.get_current_system()
                    system_tick: str|None = current_system.get('TickTime') if current_system is not None else None

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
                    self.bgstally.overlay.display_message("tickwarn", _("Tick {minutes_delta}m Overdue (Estimated)").format(minutes_delta=minutes_delta), True) # LANG: Overlay overdue tick message
                elif datetime.now(UTC) > self.bgstally.tick.next_predicted():
                    self.bgstally.overlay.display_message("tickwarn", _("Past Estimated Tick Time"), True, text_colour_override="#FFA500") # LANG: Overlay past estimated time tick message
                elif datetime.now(UTC) > self.bgstally.tick.next_predicted() - timedelta(minutes = TIME_TICK_ALERT_M):
                    self.bgstally.overlay.display_message("tickwarn", _("Within {minutes_to_tick}m of Next Tick (Estimated)").format(minutes_to_tick=TIME_TICK_ALERT_M), True, text_colour_override="yellow") # LANG: Overlay close to tick message

            # Activity Indicator
            if self.bgstally.state.enable_overlay_activity and self.indicate_activity:
                self.bgstally.overlay.display_indicator("indicator")
                self.indicate_activity = False

            # Thargoid War Progress Report
            if self.bgstally.state.enable_overlay_tw_progress and current_activity is not None:
                current_system:dict|None = current_activity.get_current_system()
                if current_system and current_system.get('tw_status') is not None:
                    progress:float = float(get_by_path(current_system, ['tw_status', 'WarProgress'], 0))
                    percent:float = round(progress * 100, 2)

                    self.bgstally.overlay.display_progress_bar("tw", _("TW War Progress in {current_system}: {percent}%").format(current_system=current_system.get('System', 'Unknown'), percent=percent), progress) # LANG:Overlay TW report message

            # System Activity. Shares same overlay panel as System Info and Station Info
            fmtr = self.bgstally.formatter_manager.get_default_formatter()
            if self.bgstally.state.enable_overlay_system and current_activity is not None and fmtr is not None:

                if self.activity_system_address is not None:
                    # Report recent activity in a designated system, overrides pinned systems
                    report_system:dict|None = current_activity.get_system_by_address(self.activity_system_address)
                    if report_system is not None:
                        self.bgstally.overlay.display_message("system_info", fmtr.get_overlay(current_activity, DiscordActivity.BOTH, [report_system['System']], lang=self.bgstally.state.discord_lang), fit_to_text=True)
                    self.activity_system_address = None
                else:
                    # Report pinned systems
                    pinned_systems:list = current_activity.get_pinned_systems()
                    if pinned_systems is not None and pinned_systems != []:
                        self.bgstally.overlay.display_message("system_info", fmtr.get_overlay(current_activity, DiscordActivity.BOTH, pinned_systems, lang=self.bgstally.state.discord_lang), fit_to_text=True, ttl_override=TIME_WORKER_PERIOD_S + 2) # Overlay pinned systems message

            system_and_station_info:str = ""

            # System Information. Shares same overlay panel as System Activity and Station Info
            if self.info_system_address is not None and current_activity is not None:
                report_system:dict|None = current_activity.get_system_by_address(self.info_system_address)
                if report_system is not None:
                    system_and_station_info = self._build_system_info(current_activity, report_system)
                self.info_system_address = None

            # Station Information. Shares same overlay panel as System Activity and System Info
            if self.info_station is not None:
                system_and_station_info += "\n" if system_and_station_info != "" else ""
                system_and_station_info += self._build_station_info(self.info_station)
                self.info_station = None

            if self.bgstally.state.enable_overlay_system and system_and_station_info != "":
                self.bgstally.overlay.display_message("system_info", system_and_station_info, fit_to_text=True)

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
                mode: int = self.bgstally.state.overlay_objectives_mode
                objectives_text: str = ""
                show_objectives: bool = False

                # Check if we're within TIME_TICK_OBJECTIVES_REFRESH_S  of objectives changing (for modes 0-2)
                time_since_change: timedelta|None = None
                if self.bgstally.objectives_manager.objectives_changed_timestamp:
                    time_since_change = datetime.now(UTC) - self.bgstally.objectives_manager.objectives_changed_timestamp

                match mode:
                    case 0:  # Notification for new objectives
                        if (time_since_change is not None and
                            time_since_change.total_seconds() <= TIME_TICK_OBJECTIVES_REFRESH_S and
                            self.bgstally.objectives_manager.objectives_change_type == "new"):
                            objectives_text = self.bgstally.objectives_manager.get_overlay_objectives_notification()
                            show_objectives = True

                    case 1:  # Full text for new objectives
                        if (time_since_change is not None and
                            time_since_change.total_seconds() <= TIME_TICK_OBJECTIVES_REFRESH_S and
                            self.bgstally.objectives_manager.objectives_change_type == "new"):
                            objectives_text = self.bgstally.objectives_manager.get_overlay_objectives_details(use_changed_objective=True)
                            show_objectives = True

                    case 2: # Full text for new and updated objectives
                        if time_since_change is not None and time_since_change.total_seconds() <= TIME_TICK_OBJECTIVES_REFRESH_S:
                            objectives_text = self.bgstally.objectives_manager.get_overlay_objectives_details(use_changed_objective=True)
                            show_objectives = True

                    case 3:  # Always show top priority objective
                        objectives_text = self.bgstally.objectives_manager.get_overlay_objectives_details(use_changed_objective=False)
                        show_objectives = True

                    case 4:  # Always show all objectives
                        objectives_text = self.bgstally.objectives_manager.get_overlay_objectives()
                        show_objectives = True

                if show_objectives and objectives_text:
                    self.bgstally.overlay.display_message("objectives", objectives_text, fit_to_text=True, title=self.bgstally.objectives_manager.get_title())

            state:State = self.bgstally.state

            # Colonisation
            show_colonisation_overlay = bool(
                state.vehicle == Vehicle.SHIP and \
                state.ui_state in (UIState.STATION_SERVICES, UIState.NO_FOCUS, UIState.INTERNAL_PANEL) and \
                (ShipState.HARDPOINTS_DEPLOYED not in state.ship_state))
            if self.bgstally.state.enable_overlay_colonisation and show_colonisation_overlay:
                colonisation_text:str = self.window_progress.overlay_text()
                if colonisation_text != "":
                    self.bgstally.overlay.display_message("colonisation", colonisation_text, fit_to_text=True, ttl_override=3)

            show_carrier_overlay = bool(
                state.vehicle == Vehicle.SHIP and \
                state.ui_state in (UIState.STATION_SERVICES, UIState.NO_FOCUS) and \
                (ShipState.HARDPOINTS_DEPLOYED not in state.ship_state))
            #Debug.logger.debug(f"{self.bgstally.state.enable_overlay_carrier} {show_carrier_overlay} {state.vehicle} {state.ui_state}")
            if self.bgstally.state.enable_overlay_carrier and show_carrier_overlay:
                carrier_text:str = self.bgstally.fleet_carrier.update_overlay()
                if carrier_text != "":
                    self.bgstally.overlay.display_message("fleetcarrier", carrier_text, fit_to_text=True, ttl_override=3)

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


    def _show_activity_window(self, activity:Activity|None):
        """
        Display the appropriate activity data window, using data from the passed in activity object
        """
        if activity is None:
            return

        existing_activity_window:WindowActivity|None = self.window_activity.get(activity.tick_id)
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


    def _build_system_info(self, activity: Activity, system: dict) -> str:
        """ Build a human-readable system info string for overlay display

        Args:
            Activity (activity): The activity object containing the data
        Returns:
            str: The human-readable system info
        """
        result:str = ""

        result += TAG_OVERLAY_HIGHLIGHT + _("Entered System: {system}").format(system=system.get("System", _("Unknown"))) + "\n" # LANG: System information overlay title

        ordered_factions: list[dict] = activity.get_ordered_factions(system['Factions'])
        if len(ordered_factions) == 0:
            result += _("No factions found in system") + "\n" # LANG: System information overlay no factions
        else:
            controlling_faction: dict = ordered_factions[0]
            result += _("Controlling Faction: {faction} - Influence: {influence}%").format(faction=controlling_faction.get("Faction", _("Unknown")), influence=round(controlling_faction.get("Influence", 0) * 100, 2)) + "\n" # LANG: System information overlay controlling faction

            conflicts: str = ""
            factions_handled: list = []

            for faction in ordered_factions:
                if faction.get("Faction", "") in factions_handled:
                    continue
                if faction.get("FactionState", "None") in STATES_ELECTION + STATES_WAR:
                    opposing_faction: dict = system['Factions'].get(faction.get("Opponent", ""), {})
                    conflicts += "  " + _("{state}: {faction1} vs {faction2} - {score_for}:{score_against}").format( # LANG: System information overlay conflict information
                        state=faction.get("FactionState", _("Unknown")),  # LANG: System information overlay conflict state
                        faction1=faction.get("Faction", _("Unknown")),  # LANG: System information overlay conflict faction
                        faction2=opposing_faction.get("Faction", _("Unknown")), # LANG: System information overlay conflict opposing faction
                        score_for=faction.get("Score", _("Unknown")), # LANG: System information overlay conflict score
                        score_against=opposing_faction.get("Score", _("Unknown"))) + "\n"  # LANG: System information overlay controlling faction conflict information
                    conflicts += "    " + _("Asset won: {stake}").format(stake=opposing_faction.get("Stake", _("Unknown"))) + "\n"  # LANG: System information overlay conflict asset at stake information
                    conflicts += "    " + _("Asset lost: {stake}").format(stake=faction.get("Stake", _("Unknown"))) + "\n"  # LANG: System information overlay conflict asset at stake information
                    factions_handled.append(opposing_faction.get("Faction", ""))

            if conflicts != "":
                result += _("Conflicts:") + "\n" + conflicts  # LANG: System information overlay conflicts title

        result += _("Population: {population}").format(population=human_format(system.get("Population", 0))) + "\n" # LANG: System information overlay population
        result += _("Government: {government}").format(government=system.get("Government", _("Unknown"))) + "\n" # LANG: System information overlay government
        result += _("Security: {security}").format(security=system.get("Security", _("Unknown"))) + "\n" # LANG: System information overlay security

        return result


    def _build_station_info(self, station_info: dict[str, str]) -> str:
        """Build a human-readable station info string for overlay display

        Args:
            station_info (dict[str, str]): Dictionary containing station name and faction name

        Returns:
            str: The human-readable station info
        """
        result:str = ""

        result += TAG_OVERLAY_HIGHLIGHT + _("Entered Station: {station}").format(station=station_info.get("station", _("Unknown"))) + "\n" # LANG: Station information overlay title
        result += _("Controlling Faction: {faction}").format(faction=station_info.get("faction", _("Unknown"))) + "\n" # LANG: Station information overlay controlling faction

        return result
