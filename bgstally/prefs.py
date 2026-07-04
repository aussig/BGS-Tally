from dataclasses import dataclass, field, fields
from typing import get_origin
from copy import deepcopy
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable
from functools import partial
import tkinter as tk
from tkinter import ttk

import myNotebook as nb # type:ignore
from ttkHyperlinkLabel import HyperlinkLabel # type:ignore

from bgstally.constants import (FOLDER_DATA, FILE_SUFFIX,FONT_HEADING_2, FONT_SMALL, CheckStates, FavouriteActivity)
from bgstally.debug import Debug
from bgstally.utils import _, available_langs, catch_exceptions, get_by_path, get_localised_filepath, human_format
from bgstally.widgets import EntryPlus
from bgstally.windows.objectives_overlay_settings import WindowObjectivesOverlaySettings

from thirdparty.tksheet import Sheet

if TYPE_CHECKING:
    from bgstally.bgstally import BGSTally

URL_WIKI = "https://github.com/aussig/BGS-Tally/wiki"
PREFS_STRUCTURE = "prefs_structure" + FILE_SUFFIX

@dataclass
class Pref:
    """Class to hold a single preference."""
    name:str = ""
    type:str = ""
    var:Any = None
    default:Any = None
    desc:str = ""
    options:dict = field(default_factory=dict)
    custom:str|None = None

@dataclass
class Section:
    """Class to hold a single section of preferences."""
    name:str = ""
    desc:str = ""
    cols:int = 1
    prefs:list[Pref] = field(default_factory=list)

@dataclass
class Tab:
    """Class to hold a single tab of preferences."""
    name:str = ""
    sections:list[Section] = field(default_factory=list)

class Prefs:
    """Class to hold and manage user preferences."""

    def __init__(self, bgstally:"BGSTally"):
        self.bgstally = bgstally
        self.prefs_fr:tk.Frame|None = None

        self.window_objectives_overlay_settings:WindowObjectivesOverlaySettings = WindowObjectivesOverlaySettings(self.bgstally)
        self.prefs:list[Tab] = self._load_prefs_structure()

    def get_prefs_frame(self, parent_frame:tk.Frame) -> tk.Frame:
        """
        Return a TK Frame for adding to the EDMC settings dialog
        """
        self.prefs_fr = parent_frame
        self.frame = nb.Frame(parent_frame)
        # Make the second column fill available space
        self.frame.columnconfigure(1, weight=1)

        current_row = 1
        nb.Label(self.frame, text=f"{self.bgstally.plugin_name} v{str(self.bgstally.version)}", font=FONT_HEADING_2).\
            grid(row=current_row, column=0, padx=10, sticky=tk.W)
        HyperlinkLabel(self.frame, text=_("Instructions for Use"), background=nb.Label().cget('background'), url=URL_WIKI, underline=True).\
            grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences label

        ttk.Separator(self.frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1

        self._create_tabs(self.frame, current_row)
        return self.frame

    def _create_tabs(self, frame:tk.Frame, current_row:int) -> None:
        """
        Create the tabs for the preferences window
        """
        nb.Notebook(frame, width=800, height=600).grid(row=current_row, columnspan=2, padx=10, pady=10, sticky=tk.NSEW); current_row += 1
        for tab in self.prefs:
            self._create_tab(frame, tab)

    def _create_tab(self, parent_frame:tk.Frame, tab:Tab) -> None:
        """
        Create a tab in the preferences notebook
        """
        nb.Label(parent_frame, text=tab.name, font=FONT_HEADING_2).grid(row=0, column=0, padx=10, sticky=tk.W)
        tab_frame = nb.Frame(parent_frame)
        tab_frame.grid(row=1, column=0, padx=10, pady=10, sticky=tk.NSEW)
        for section in tab.sections:
            self._create_section(tab_frame, section)

    def _create_section(self, parent_frame:tk.Frame, section:Section) -> None:
        """
        Create a section in a tab
        """
        nb.Label(parent_frame, text=section.name, font=FONT_HEADING_2).grid(row=0, column=0, padx=10, sticky=tk.W)
        section_frame = nb.Frame(parent_frame)
        section_frame.grid(row=1, column=0, padx=10, pady=10, sticky=tk.NSEW)
        row:int = 0; column:int = 0
        for pref in section.prefs:
            self._create_pref(section_frame, pref, row, column*2)
            column += 1
            if column >= section.cols:
                column = 0
                row += 1

    @catch_exceptions
    def _create_pref(self, parent_frame:tk.Frame, pref:Pref, row:int, column:int) -> None:
        """
        Create a preference in a section
        """
        nb.Label(parent_frame, text=pref.desc).grid(row=row, column=column, padx=10, sticky=tk.W)
        match pref.type:
            case "bool":
                nb.Checkbutton(parent_frame, variable=getattr(self.bgstally.state, pref.var, ""), onvalue=CheckStates.STATE_ON,
                               offvalue=CheckStates.STATE_OFF).grid(row=row, column=column+1, padx=10, sticky=tk.W)
            case "menu":
                options:dict = pref.options
                Debug.logger.debug(f"Creating menu for {pref.var} state: {getattr(self.bgstally.state, pref.var, '')}")
                var:tk.StringVar|str = getattr(self.bgstally.state, pref.var)
                if isinstance(var, str): # Sometimes the state variable is a string instead of a StringVar, so we need to convert it
                    var = tk.StringVar(value=var, name=pref.var)
                Debug.logger.debug(f"Creating menu for {pref.var} with options {options} and initial value {var}")
                nb.OptionMenu(parent_frame, var, var.get(), *options.values(), command=partial(self._menu_selected, pref.var, options)).\
                    grid(row=row, column=column+1, padx=10, sticky=tk.W)
            case "custom" if pref.custom is not None:
                func:Callable = getattr(self, pref.custom)
                func(parent_frame, row, column+1)
            case _:
                EntryPlus(parent_frame, textvariable=getattr(self.bgstally.state, pref.var, "")).grid(row=row, column=column+1, padx=10, pady=1, sticky=tk.W)

    def _menu_selected(self, var_name:str, options:dict, value:str) -> None:
        """
        Callback for when a menu option is selected
        """
        k = next(k for k, v in options.items() if v == value)
        getattr(self.bgstally.state, var_name).set(k)
        self.bgstally.state.refresh()

    def _hydrate_pref(self, pref:Pref) -> Pref:
        """ Hydrate a preference with default values and options if not provided. """
        # Fill in a default variable name if not provided
        if pref.var is None:
            pref.var = pref.name.replace("_", " ").title().replace(" ", "")
        if pref.type == "bool" and pref.default is None:
            pref.default = "Yes"
        if pref.type == "str" and pref.default is None:
            pref.default = ""
        if pref.name == "discord_lang":
            pref.options = available_langs()
        if pref.name == "discord_formatter":
            pref.options = self.bgstally.formatter_manager.get_formatters()
        return pref

    def _from_dict(self, data:dict, which:str = "") -> Any:
        """ Deserialize a dictionary into a list of tab objects """

        res:Tab|Section|Pref = Tab() if which =="tab" else Section() if which == "section" else Pref()
        for k, v in data.items():
            match k:
                case "tabs" | "sections" | "prefs":
                    setattr(res, k, [self._from_dict(item, k[:-1]) for item in v])
                case _:
                    setattr(res, k, v)

        # Hydrate dynamic preferences with available options
        if isinstance(res, Pref):
            res = self._hydrate_pref(res)

        return res

    @catch_exceptions
    def _load_prefs_structure(self) -> list[Tab]:
        """ Load the preferences structure from a JSON file."""
        file:Path = Path(self.bgstally.plugin_dir, FOLDER_DATA, PREFS_STRUCTURE)
        with file.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        return [tab for tab in (self._from_dict(tab_data, "tab") for tab_data in raw) if isinstance(tab, Tab)]

    @catch_exceptions
    def _discord_webhooks(self, frame:tk.Frame, row:int, column:int) -> None:
        ui_scaling:float = frame.tk.call('tk', 'scaling')
        sheet_headings:list = ["UUID",
                               _("Nickname"), # LANG: Preferences table heading
                               _("Webhook URL"), # LANG: Preferences table heading
                               "BGS",
                               "TW",
                               _("FC C/M"), # LANG: Preferences table heading, abbreviation for fleet carrier commodities / materials
                               _("FC Ops"), # LANG: Preferences table heading, abbreviation for fleet carrier operations
                               "CMDR",
                               "PP"]
        self.sheet_webhooks:Sheet = Sheet(frame, show_row_index=True, row_index_width=10, cell_auto_resize_enabled=False,
                                          height=140, width=880, column_width=int(45 * ui_scaling), header_align="left",
                                          empty_vertical=15, empty_horizontal=0, font=FONT_SMALL,
                                          show_horizontal_grid=True, show_vertical_grid=False, show_top_left=False,
                                          headers=sheet_headings)
        self.sheet_webhooks.grid(row=row, column=column, columnspan=2, padx=5, pady=5, sticky=tk.NSEW); row += 1
        self.sheet_webhooks.hide_columns(columns=[0])                       # Visible column indexes
        self.sheet_webhooks.checkbox_column(c=[3, 4, 5, 6, 7, 8])           # Data column indexes
        self.sheet_webhooks.set_sheet_data(data=self.bgstally.webhook_manager.get_webhooks_as_list())
        self.sheet_webhooks.column_width(column=0, width=int(150 * ui_scaling), redraw=False) # Visible column indexes
        self.sheet_webhooks.column_width(column=1, width=int(200 * ui_scaling), redraw=True)  # Visible column indexes
        self.sheet_webhooks.enable_bindings(('single_select', 'row_select', 'arrowkeys', 'right_click_popup_menu', 'rc_select', 'rc_insert_row',
                            'rc_delete_row', 'copy', 'cut', 'paste', 'delete', 'undo', 'edit_cell', 'modified'))
        self.sheet_webhooks.extra_bindings('all_modified_events', func=self._webhooks_table_modified)

    def unused(self, frame:tk.Frame, current_row:int) -> tk.Frame:
        nb.Label(frame, text=_("General Options"), font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW) # LANG: Preferences heading
        nb.Checkbutton(frame, text=_("{plugin_name} Active").format(plugin_name=self.bgstally.plugin_name), variable=self.bgstally.state.Status, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.bgstally.ui.update_plugin_frame).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences checkbox label
        nb.Checkbutton(frame, text=_("Show Systems with Zero Activity"), variable=self.bgstally.state.ShowZeroActivitySystems, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences checkbox label
        nb.Checkbutton(frame, text=_("Colonisation Active"), variable=self.bgstally.state.ColonisationStatus, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self._colonisation_change).grid(row=current_row, column=1, padx=10, sticky=tk.NW); current_row += 1 # LANG: Preferences checkbox label

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text=_("Discord Options"), font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW) # LANG: Preferences heading
        discofr = nb.Frame(frame)
        discofr.grid(row=current_row, column=1, padx=0, sticky=tk.W); current_row += 1
        row:int = 0; column:int = 0
        nb.Checkbutton(discofr, text=_("Show Detailed INF"), variable=self.bgstally.state.DetailedInf, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.bgstally.state.refresh).grid(row=row, column=0, padx=10, sticky=tk.W)# LANG: Preferences checkbox label
        nb.Checkbutton(discofr, text=_("Include Secondary INF"), variable=self.bgstally.state.IncludeSecondaryInf, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.bgstally.state.refresh).grid(row=row, column=1, padx=10, sticky=tk.W); row += 1 # LANG: Preferences checkbox label
        nb.Checkbutton(discofr, text=_("Show Detailed Trade"), variable=self.bgstally.state.DetailedTrade, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.bgstally.state.refresh).grid(row=row, column=0, padx=10, sticky=tk.W)# LANG: Preferences checkbox label
        nb.Checkbutton(discofr, text=_("Report Newly Visited System Activity By Default"), variable=self.bgstally.state.EnableSystemActivityByDefault, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF).grid(row=row, column=1, padx=10, sticky=tk.W); row += 1 # LANG: Preferences checkbox label
        nb.Checkbutton(discofr, text=_("Show Powerplay Merits Gained"), variable=self.bgstally.state.EnableShowMerits, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.bgstally.state.refresh).grid(row=row, column=0, padx=10, sticky=tk.W) # LANG: Preferences checkbox label
        favourite_types: dict = {FavouriteActivity.IGNORE: _("Include all factions"), # LANG: Dropdown menu on activity window
                                 FavouriteActivity.FACTIONS: _("Include favourite factions only"), # LANG: Dropdown menu on activity window
                                 FavouriteActivity.SYSTEMS: _("Include systems containing favourite factions")} # LANG: Dropdown menu on activity window
        var_favourite_type: tk.StringVar = tk.StringVar(value=favourite_types.get(self.bgstally.state.FavouriteActivityMode.get(), FavouriteActivity.IGNORE))
        self.mnu_favourite_type: nb.OptionMenu = nb.OptionMenu(discofr, var_favourite_type, var_favourite_type.get(),
                                                            *favourite_types.values(),
                                                            command=partial(self._favourite_type_selected, favourite_types), direction='below')
        self.mnu_favourite_type.grid(row=row, column=1, padx=10, sticky=tk.W); row += 1
        nb.Checkbutton(discofr, text=_("Use Colonisation Plan name instead of System Name"), variable=self.bgstally.state.UseColonisationName, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.bgstally.state.refresh).grid(row=row, column=0, padx=10, sticky=tk.W) # LANG: Preferences checkbox label
        nb.Checkbutton(discofr, text=_("Automatically Post BGS and TW Activity"), variable=self.bgstally.state.DiscordBGSTWAutomatic, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.bgstally.state.refresh).grid(row=row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences checkbox label

        nb.Label(frame, text=_("Post to Discord as")).grid(row=current_row, column=0, padx=10, sticky=tk.W) # LANG: Preferences label
        self.languages: dict[str|None, str] = available_langs()
        self.language:tk.StringVar = tk.StringVar(value=self.languages.get(self.bgstally.state.discord_lang, _('Default'))) # LANG: Preferences label
        self.formatters: dict[str|None, str] = self.bgstally.formatter_manager.get_formatters()
        self.formatter:tk.StringVar = tk.StringVar(value=self.formatters.get(self.bgstally.state.discord_formatter, _('Default'))) # LANG: Preferences label
        discofr2 = nb.Frame(frame)
        discofr2.grid(row=current_row, column=1, padx=0, sticky=tk.W); current_row += 1
        row = 0
        EntryPlus(discofr2, textvariable=self.bgstally.state.DiscordUsername).grid(row=row, column=0, padx=10, pady=1, sticky=tk.W)
        nb.Label(discofr2, text=_("Language for Discord Posts")).grid(row=row, column=1, padx=10, sticky=tk.W) # LANG: Preferences label
        #nb.Label(discofr2, text=_("Post Language")).grid(row=row, column=1, padx=10, sticky=tk.W) # LANG: Preferences label
        nb.OptionMenu(discofr2, self.language, self.language.get(), *self.languages.values(), command=self._language_modified).grid(row=row, column=2, padx=10, pady=1, sticky=tk.W)
        nb.Label(discofr2, text=_("Format for Discord Posts")).grid(row=row, column=3, padx=(50,10), sticky=tk.W) # LANG: Preferences label
        #nb.Label(discofr2, text=_("Post Format")).grid(row=row, column=3, padx=10, sticky=tk.W) # LANG: Preferences label
        nb.OptionMenu(discofr2, self.formatter, self.formatter.get(), *sorted(self.formatters.values()), command=self._formatter_modified).grid(row=row, column=4, padx=10, pady=1, sticky=tk.W)
        nb.Label(frame, text=_("Discord Avatar URL")).grid(row=current_row, column=0, padx=10, sticky=tk.W) # LANG: Preferences label
        EntryPlus(frame, textvariable=self.bgstally.state.DiscordAvatarURL, width=80).grid(row=current_row, column=1, padx=10, pady=1, sticky=tk.W); current_row += 1

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
                               "CMDR",
                               "PP"]
        self.sheet_webhooks:Sheet = Sheet(frame, show_row_index=True, row_index_width=10, cell_auto_resize_enabled=False, height=140, width=880,
                                     column_width=int(45 * ui_scaling), header_align="left", empty_vertical=15, empty_horizontal=0, font=FONT_SMALL,
                                     show_horizontal_grid=True, show_vertical_grid=False, show_top_left=False,
                                     headers=sheet_headings)
        self.sheet_webhooks.grid(row=current_row, columnspan=2, padx=5, pady=5, sticky=tk.NSEW); current_row += 1
        self.sheet_webhooks.hide_columns(columns=[0])                       # Visible column indexes
        self.sheet_webhooks.checkbox_column(c=[3, 4, 5, 6, 7, 8])           # Data column indexes
        self.sheet_webhooks.set_sheet_data(data=self.bgstally.webhook_manager.get_webhooks_as_list())
        self.sheet_webhooks.column_width(column=0, width=int(150 * ui_scaling), redraw=False) # Visible column indexes
        self.sheet_webhooks.column_width(column=1, width=int(200 * ui_scaling), redraw=True)  # Visible column indexes
        self.sheet_webhooks.enable_bindings(('single_select', 'row_select', 'arrowkeys', 'right_click_popup_menu', 'rc_select', 'rc_insert_row',
                            'rc_delete_row', 'copy', 'cut', 'paste', 'delete', 'undo', 'edit_cell', 'modified'))
        self.sheet_webhooks.extra_bindings('all_modified_events', func=self._webhooks_table_modified)
        nb.Label(frame, text=_("To add a webhook: Right-click on a row number and select 'Insert rows above / below'."), font=FONT_SMALL).grid(row=current_row, columnspan=2, padx=10, sticky=tk.NW); current_row += 1 # LANG: Preferences label
        nb.Label(frame, text=_("To delete a webhook: Right-click on a row number and select 'Delete rows'."), font=FONT_SMALL).grid(row=current_row, columnspan=2, padx=10, sticky=tk.NW); current_row += 1 # LANG: Preferences label

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text=_("In-game Overlay"), font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW) # LANG: Preferences heading
        nb.Checkbutton(frame, text=_("Show In-game Overlay"), # LANG: Preferences checkbox label
                       variable=self.bgstally.state.EnableOverlay,
                       state=self.overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1

        nb.Label(frame, text=_("Panels")).grid(row=current_row, column=0, padx=10, sticky=tk.NW) # LANG: Preferences label
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
        ttk.Button(overlay_options_frame_1, text="⚙", width=3,
                   state=self.overlay_options_state(),
                   command=partial(self.window_objectives_overlay_settings.show, parent_frame)
                   ).pack(side=tk.LEFT, padx=(2, 0))
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
        nb.Checkbutton(overlay_options_frame_2, text=_("Alerts and Warnings"), # LANG: Preferences checkbox label
                       variable=self.bgstally.state.EnableOverlayWarning,
                       state=self.overlay_options_state(),
                       onvalue=CheckStates.STATE_ON,
                       offvalue=CheckStates.STATE_OFF,
                       command=self.bgstally.state.refresh
                       ).pack(side=tk.LEFT)
        nb.Checkbutton(overlay_options_frame_2, text=_("Fleetcarrier"), # LANG: Preferences checkbox label
                    variable=self.bgstally.state.EnableOverlayCarrier,
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
        nb.Label(frame, text=_("Colonisation"), font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW); current_row += 1 # LANG: Preferences heading
        nb.Label(frame, text=_("Maximum commodities")).grid(row=current_row, column=0, padx=10, sticky=tk.W) # LANG: Preferences label
        EntryPlus(frame, textvariable=self.bgstally.state.ColonisationMaxCommodities).grid(row=current_row, column=1, padx=10, pady=1, sticky=tk.W); current_row += 1
        nb.Checkbutton(frame, text=_("Use scrollbar (restart required)"), variable=self.bgstally.state.EnableProgressScrollbar, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.bgstally.state.refresh).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences checkbox label

        api_keys_label_common(self, current_row, frame)
        current_row += 1
        show_pwd_var_common(frame, current_row, self)
        current_row += 1
        self.apikey_label.configure(text=_("RavenColonial API Key")) # LANG: Preferences label
        self.apikey.configure(textvariable=self.bgstally.state.ColonisationRCAPIKey)

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text=_("Fleet Carrier"), font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW); current_row += 1 # LANG: Preferences heading
        nb.Label(frame, text=_("Fleet Carrier Cooldown Notifications")).grid(row=current_row, column=0, padx=10, sticky=tk.W) # LANG: Preferences label
        cdnotifications: dict = {"none": _("None"), # LANG: Dropdown menu on prefs window
                                 "popup": _("Popup only"), # LANG: Dropdown menu on prefs window
                                 "overlay": _("Overlay only"), # LANG: Dropdown menu on prefs window
                                 "both": _("Popup and Overlay")} # LANG: Dropdown menu on prefs window
        notifications_var:tk.StringVar = tk.StringVar(value=cdnotifications.get(self.bgstally.state.FcCooldown.get(), "Both"))
        self.fccooldown:nb.OptionMenu = nb.OptionMenu(frame, notifications_var, notifications_var.get(),
                                                            *cdnotifications.values(),
                                                            command=partial(self._cooldown_selected, cdnotifications), direction='below')
        self.fccooldown.grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); current_row += 1
        nb.Label(frame, text=_("Advanced"), font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.NW) # LANG: Preferences heading
        tk.Button(frame, text=_("Force Tick"), command=self._confirm_force_tick, bg="red", fg="white").grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences button label

        return frame


    def save_prefs(self):
        """
        Preferences frame has been saved (from EDMC core or any plugin)
        """
        self.update_plugin_frame()
        self._load_commodities()


    def _formatter_modified(self, event=None):
        """Callback for change in formatter dropdown

        Args:
            event (_type_, optional): Variable related to the callback. Defaults to None.
        """
        formatters_by_name: dict = {v: k for k, v in self.formatters.items()}
        self.bgstally.state.discord_formatter = formatters_by_name.get(self.formatter.get())

    def _colonisation_change(self, event=None):
        """Callback for change in colonisation status

        Args:
            event (_type_, optional): Variable related to the callback. Defaults to None.
        """
        self.bgstally.state.refresh()
        self.update_plugin_frame()

    def _favourite_type_selected(self, favourite_types: dict, value: str):
        """The user has changed the dropdown to choose the favourite faction posting type
        """
        k: str = next(k for k, v in favourite_types.items() if v == value)
        self.bgstally.state.FavouriteActivityMode.set(k)
        self.bgstally.state.refresh

    def _cooldown_selected(self, cooldown_types: dict, value: str):
        k: str = next(k for k, v in cooldown_types.items() if v == value)
        self.bgstally.state.FcCooldown.set(k)
        self.bgstally.state.refresh()


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

    def overlay_options_state(self):
        """
        If the overlay plugin is not available, we want to disable the options so users are not interacting
        with them expecting results
        """
        return "disabled" if self.bgstally.overlay.edmcoverlay == None else "enabled"




    # def _deserialise(self, pref_data:dict[str, Any]) -> dict[str, Any]:
    #     """ Deserialize a dictionary into a Pref object, handling special cases for certain types and options. """
    #     pref_type = pref_data.get("type", "str")
    #     default = pref_data.get("default")
    #     if pref_type == "bool" and isinstance(default, str):
    #         try:
    #             default = CheckStates(default)
    #         except ValueError:
    #             pass

    #     options:dict[Any, Any] = {}
    #     raw_options = pref_data.get("options", [])
    #     if isinstance(raw_options, list):
    #         options = self._deserialise_options(pref_data.get("var", ""), raw_options)
    #     elif isinstance(raw_options, dict):
    #         options = raw_options

    #     return {
    #         "name": pref_data["name"],
    #         "type": pref_type,
    #         "var": pref_data["var"],
    #         "default": default,
    #         "desc": pref_data.get("desc", ""),
    #         "options": options,
    #         "custom": pref_data.get("custom"),
    #     }
    # def _deserialise_options(self, pref_var:str, option_items:list[dict[str, Any]]) -> dict[Any, Any]:
    #     """ Deserialize a list of option items into a dictionary for a Pref object."""
    #     options:dict[Any, Any] = {}
    #     for item in option_items:
    #         key = item.get("key")
    #         if pref_var == "FavouriteActivityMode" and isinstance(key, str):
    #             try:
    #                 key = FavouriteActivity(key)
    #             except ValueError:
    #                 pass
    #         options[key] = item.get("value")
    #     return options


    # def _deserialise_pref(self, pref_data:dict[str, Any]) -> Pref:
    #     """ Deserialize a dictionary into a Pref object, handling special cases for certain types and options. """
    #     pref_type = pref_data.get("type", "str")
    #     default = pref_data.get("default")
    #     if pref_type == "bool" and isinstance(default, str):
    #         try:
    #             default = CheckStates(default)
    #         except ValueError:
    #             pass

    #     options:dict[Any, Any] = {}
    #     raw_options = pref_data.get("options", [])
    #     if isinstance(raw_options, list):
    #         options = self._deserialise_options(pref_data.get("var", ""), raw_options)
    #     elif isinstance(raw_options, dict):
    #         options = raw_options

    #     return Pref(
    #         name=pref_data["name"],
    #         type=pref_type,
    #         var=pref_data["var"],
    #         default=default,
    #         desc=pref_data.get("desc", ""),
    #         options=options,
    #         custom=pref_data.get("custom"),
    #     )


    # def _to_dict(self, pref:list|Tab|Section|Pref) -> dict[str, Any]:
    #     """ Serialize a Pref object to a dictionary for saving to JSON."""
    #     if isinstance(pref, list):
    #         return { "prefs_data": [self._to_dict(p) for p in pref]}
    #     res:dict[str, Any] = {}
    #     for attr in fields(pref):
    #         if attr.type is list or get_origin(attr.type) is list:
    #             res[attr.name] = [self._to_dict(p) for p in getattr(pref, attr.name)]
    #         elif isinstance(pref, Pref) and attr.name == "options" and pref.name in ["discord_lang", "discord_formatter"]:
    #             res["options"] = []
    #         elif isinstance(pref, Pref) and attr.name == "options":
    #             res["options"] = [{"key": k, "value": v} for k, v in pref.options.items()] # We leave these empty as they are dynamically hydrated
    #         else:
    #             res[attr.name] = getattr(pref, attr.name)
    #     return res

    # def save_prefs_structure(self, path:Path|None = None, prefs_data:list[Tab]|None = None) -> None:
    #     """ Save the preferences structure to a JSON file."""
    #     prefs_path = path or PREFS_STRUCTURE_PATH
    #     data:dict = self._to_dict(prefs_data or [])
    #     prefs_path.parent.mkdir(parents=True, exist_ok=True)
    #     with prefs_path.open("w", encoding="utf-8") as f:
    #         json.dump(data, f, indent=2, ensure_ascii=False)
