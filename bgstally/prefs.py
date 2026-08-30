from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable
from functools import partial

import tkinter as tk
from tkinter import ttk, font as tkfont
from tkinter.messagebox import askyesno

import myNotebook as nb # type:ignore
from ttkHyperlinkLabel import HyperlinkLabel # type:ignore

from thirdparty.tksheet import Sheet
from thirdparty.Tooltip import ToolTip

from bgstally.constants import (FOLDER_DATA, FILE_SUFFIX, FONT_HEADING_2, FONT_SMALL, CheckStates, UpdateUIPolicy)
from bgstally.debug import Debug
from bgstally.utils import _, available_langs, catch_exceptions

if TYPE_CHECKING:
    from bgstally.bgstally import BGSTally

URL_GITHUB = "https://github.com/aussig/BGS-Tally"
URL_WIKI = f"{URL_GITHUB}/wiki"
PREFS_STRUCTURE = "prefs_structure" + FILE_SUFFIX


"""
  Preferences are defined in the prefs_structure.json file which defines tabs, sections and preferences.
  Most preferences are simple and can be created automatically from the JSON file.

  Values for preferences depend on the type but the following are common:

  type indicates the type of preference:
  - label: Just for displaying text
  - entry / str: A text entry field for a string or numeric preference
  - checkbox / bool: A checkbox for a simple on/off boolean preference
  - radio / radiobutton: A radio button for a single choice with multiple options
  - menu: A dropdown menu for a preference with multiple options (a different way to implement radio buttons)
  - password: A password entry field for a string preference
  - custom: A preference type that requires a custom function to create the UI elements

  var indicates the bgstally state variable the preference is bound to. If not provided, it will default to the name of the preference.

  desc is an optional description for the preference that will be shown as a tooltip.

  state is optional and a function name that returns "enabled" or "disabled" allowing dynamic enabling/disabling of preferences.
"""

@dataclass
class Pref:
    """Class to hold a single preference."""
    name:str = ""
    label:str = ""
    type:str = ""
    var:Any = None
    default:Any = None
    desc:str = ""
    options:dict = field(default_factory=dict)
    custom:str|None = None
    state:str = "enabled"
    value:str = ""

@dataclass
class Section:
    """Class to hold a single section of preferences."""
    label:str = ""
    desc:str = ""
    cols:int = 1
    prefs:list[Pref] = field(default_factory=list)

@dataclass
class Tab:
    """Class to hold a single tab of preferences."""
    label:str = ""
    state:str = "normal"
    sections:list[Section] = field(default_factory=list)

class Prefs:
    """Class to hold and manage user preferences."""

    def __init__(self, bgstally:"BGSTally"):
        self.bgstally = bgstally
        self.prefs_fr:tk.Frame|None = None
        self.prefs:list[Tab] = self._load_prefs_structure()

    def get_prefs_frame(self, parent_frame:tk.Frame) -> tk.Frame:
        """ Return a TK Frame for adding to the EDMC settings dialog """
        self.prefs_fr = parent_frame
        self.frame = nb.Frame(parent_frame)
        self.frame.columnconfigure(0, weight=0)
        self.frame.columnconfigure(1, weight=0)
        self.frame.columnconfigure(2, weight=1)

        current_row = 1
        HyperlinkLabel(self.frame, text=f"{self.bgstally.plugin_name}", background=nb.Label().cget('background'),
                       foreground=nb.Label().cget('foreground'), url=URL_GITHUB, underline=False, font=FONT_HEADING_2).\
            grid(row=current_row, column=0, padx=10, sticky=tk.W)
        HyperlinkLabel(self.frame, text=_("Instructions for Use"), background=nb.Label().cget('background'), url=URL_WIKI, underline=True).\
            grid(row=current_row, column=1, padx=10, sticky=tk.W) # LANG: Preferences help link text
        nb.Label(self.frame, text=f"v{str(self.bgstally.version)}", font=FONT_HEADING_2).\
            grid(row=current_row, column=2, padx=10, sticky=tk.E)

        current_row += 1
        #ttk.Separator(self.frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=1, sticky=tk.EW); #current_row += 1

        self._create_tabs(self.frame, current_row)
        return self.frame

    def _create_tabs(self, frame:tk.Frame, current_row:int) -> None:
        """ Create the tabs for the preferences window """
        notebook:nb.Notebook = nb.Notebook(frame)
        notebook.grid(row=current_row, columnspan=3, padx=10, pady=10, sticky=tk.NSEW)
        current_row += 1
        [self._create_tab(notebook, tab) for tab in self.prefs]

    def _create_tab(self, notebook:nb.Notebook, tab:Tab) -> None:
        """ Create a tab in the preferences notebook """
        fr:nb.Frame = nb.Frame(notebook)
        row:int = 0
        tab_frame = nb.Frame(fr)
        tab_frame.grid(row=row, column=0, padx=10, pady=10, sticky=tk.NSEW)
        tab_frame.columnconfigure(0, weight=1)
        for section in tab.sections:
            row += 1
            row = self._create_section(tab_frame, row, section)

        state:str|Callable = getattr(self, tab.state)() if callable(getattr(self, tab.state, None)) else tab.state
        notebook.add(fr, text=tab.label, state=state)

    def _create_section(self, parent_frame:tk.Frame, row:int, section:Section) -> int:
        """ Create a section in a tab """

        sfr:tk.Frame|ttk.LabelFrame
        fnt:tkfont.Font = tkfont.nametofont("TkDefaultFont").copy()
        fnt.configure(weight="bold")

        if True: # Horizontal rules
            if row > 1 and section.label.strip() != "":
                ttk.Separator(parent_frame, orient=tk.HORIZONTAL).grid(row=row, columnspan=2, padx=10, pady=10, sticky=tk.EW)
            row += 1

            lbl:nb.Label = nb.Label(parent_frame, text=f"{section.label:<20}", font=fnt)
            lbl.grid(row=row, column=0, padx=10, pady=10, sticky=tk.NW)

            if section.desc.strip() != "":
                ToolTip(lbl, text=section.desc)
            sfr = nb.Frame(parent_frame)
            sfr.grid(row=row, column=1, padx=10, pady=10, sticky=tk.NSEW)

        else: # Bordered frames
            sfr = tk.LabelFrame(parent_frame, text=section.label, font=fnt, bg="SystemWindow")
            sfr.grid(row=row, column=0, padx=10, pady=10, sticky=tk.NSEW)
            sfr.columnconfigure(0, weight=0)
            sfr.columnconfigure(1, weight=1)

        sr:int = 0; sc:int = 0
        for pref in section.prefs:
            if sr > 0 and (pref.type == "custom" or pref.type == "label"):
                sc = 0; sr += 1

            sc = self._create_pref(sfr, pref, sr, sc)
            if (sc := sc + 1) >= section.cols:
                sc = 0; sr += 1

        return row

    @catch_exceptions
    def _create_pref(self, parent_frame:tk.Frame|ttk.LabelFrame, pref:Pref, row:int, column:int) -> int:
        """ Create a preference option """
        col:int = column
        state:str|Callable = getattr(self, pref.state)() if callable(getattr(self, pref.state, None)) else pref.state

        elem:nb.Checkbutton|nb.Radiobutton|nb.OptionMenu|nb.EntryMenu|nb.Label|ttk.Button = None
        match pref.type:
            case "checkbox" | "bool":
                elem = nb.Checkbutton(parent_frame, text=pref.label, variable=getattr(self.bgstally.state, pref.var, ""),
                               onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, state=state)
                elem.grid(row=row, column=col, padx=(10,0), pady=(0,5), sticky=tk.W)

            case "radio" | "radiobutton":
                elem = nb.Radiobutton(parent_frame, text=pref.label, variable=getattr(self.bgstally.state, pref.var, ""),
                               value=pref.value, state=state)
                elem.grid(row=row, column=col, padx=(10,0), pady=(0,5), sticky=tk.W)

            case "menu":
                elem = nb.Label(parent_frame, text=pref.label, state=state)
                elem.grid(row=row, column=col, padx=(10,0), pady=(0,5), sticky=tk.W)
                col += 1

                var:tk.StringVar|str = getattr(self.bgstally.state, pref.var)
                if isinstance(var, str): # Sometimes the state variable is a string instead of a StringVar, so we need to convert it
                    disp_var = tk.StringVar(value=var, name=pref.var)
                else:
                    disp_var = tk.StringVar(value=var.get(), name=pref.var)

                defval:str|None = pref.options.get(disp_var.get(), pref.default)
                values:list = list(pref.options.values())
                nb.OptionMenu(parent_frame, disp_var, defval, *values,
                              command=partial(self._menu_selected, pref.var, pref.options), direction="below"). \
                    grid(row=row, column=col, pady=(0,5), sticky=tk.W)

            case "password":
                elem = nb.Label(parent_frame, text=pref.label, state=state)
                elem.grid(row=row, column=col, padx=(10,0), pady=(0,5), sticky=tk.W)
                col += 1
                item:nb.EntryMenu = nb.EntryMenu(parent_frame, textvariable=getattr(self.bgstally.state, pref.var, ""), show="*",
                                    width=50, state=state)
                item.grid(row=row, column=col, pady=(0,5), sticky=tk.W)
                col += 1
                nb.Button(parent_frame, text="👁", width=3, command=partial(self._toggle_password_visibility, item)).\
                    grid(row=row, column=col, padx=(10,0), pady=(0,5), sticky=tk.W)

            case "custom" if pref.custom is not None:
                func:Callable = getattr(self, pref.custom)
                c = func(parent_frame, row, col, state)
                if c and c > 1: col += c

            case "label":
                elem = nb.Label(parent_frame, text=pref.label, state=state)
                elem.grid(row=row, column=col, columnspan=parent_frame.grid_size()[0] - col, padx=10, pady=(0,5), sticky=tk.W)

            case "entry" | "str":
                elem = nb.Label(parent_frame, text=pref.label, state=state)
                elem.grid(row=row, column=col, padx=(10,0), pady=(0,5), sticky=tk.W)
                col += 1
                nb.EntryMenu(parent_frame, textvariable=getattr(self.bgstally.state, pref.var, ""), width=getattr(pref, "width", 20),
                             state=state). \
                    grid(row=row, column=col, pady=(0,5), sticky=tk.W)

        if pref.desc.strip() != "":
            ToolTip(elem, text=pref.desc)
        return col

    @catch_exceptions
    def _menu_selected(self, var_name:str, options:dict, value:str) -> None:
        """ Callback for when a menu option is selected """

        k = next(k for k, v in options.items() if v == value)
        var = getattr(self.bgstally.state, var_name)
        if isinstance(var, str):
            setattr(self.bgstally.state, var_name, k)
        if isinstance(var, tk.StringVar):
            var.set(k)
        self.bgstally.state.refresh()

    @catch_exceptions
    def _toggle_password_visibility(self, entry: nb.EntryMenu) -> None:
        """ Toggle the visibility of a password entry field """
        if entry.cget("show") == "*":
            entry.config(show="")
        else:
            entry.config(show="*")

    def _hydrate_pref(self, pref:Pref) -> Pref:
        """ Hydrate a preference with default values and options if not provided. """
        # Fill in a default variable name if not provided
        if pref.name is None:
            pref.name = pref.var
        if pref.type == "bool" and pref.default is None:
            pref.default = "Yes"
        if pref.type == "str" and pref.default is None:
            pref.default = ""
        if pref.var == "discord_lang":
            pref.options = available_langs()
        if pref.var == "discord_formatter":
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
    def save_prefs(self):
        """ Preferences frame has been saved (from EDMC core or any plugin) """
        self.bgstally.state.refresh()
        self.bgstally.ui.update_plugin_frame()
        self.bgstally.ui._load_commodities()

    """
    Custom functions for creating specific preference types that require more complex UI elements than the standard ones.

    These functions return an integer indicating how many columns this custom preference takes up in the layout.
    """
    @catch_exceptions
    def _discord_webhooks(self, frame:tk.Frame, row:int, column:int, state:str) -> int:
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
                                          width=1024, column_width=int(45 * ui_scaling), header_align="left",
                                          empty_vertical=15, empty_horizontal=0, font=FONT_SMALL,
                                          show_horizontal_grid=True, show_vertical_grid=False, show_top_left=False,
                                          headers=sheet_headings)
        self.sheet_webhooks.grid(row=row, column=column, columnspan=2, padx=5, pady=5, sticky=tk.NSEW); row += 1
        self.sheet_webhooks.hide_columns(columns=(0))                       # Visible column indexes
        self.sheet_webhooks.checkbox_column(c=iter([3, 4, 5, 6, 7, 8]))           # Data column indexes
        self.sheet_webhooks.set_sheet_data(data=self.bgstally.webhook_manager.get_webhooks_as_list())
        self.sheet_webhooks.column_width(column=0, width=int(150 * ui_scaling), redraw=False) # Visible column indexes
        self.sheet_webhooks.column_width(column=1, width=int(200 * ui_scaling), redraw=True)  # Visible column indexes
        self.sheet_webhooks.enable_bindings('single_select', 'row_select', 'arrowkeys', 'right_click_popup_menu', 'rc_select',
                                            'rc_insert_row', 'rc_delete_row', 'copy', 'cut', 'paste', 'delete', 'undo', 'edit_cell')
        self.sheet_webhooks.extra_bindings('all_modified_events', func=self._webhooks_table_modified)
        self.sheet_webhooks.readonly(state=="disabled")
        return 1

    def _webhooks_table_modified(self, event=None):
        """ Callback for all modifications to the webhooks table """
        self.bgstally.webhook_manager.set_webhooks_from_list(self.sheet_webhooks.get_sheet_data())

    def _overlay_options_state(self):
        """ If the overlay plugin is not available, we want to disable the options """
        return "disabled" if self.bgstally.overlay.edmcoverlay == None else "normal"

    def _show_api_window(self, frame:tk.Frame, row:int, column:int, state:str) -> int:
        """ Show the API window for the overlay plugin """
        nb.Button(frame, text=_("Overlay API Settings"), width=20, command=partial(self.bgstally.ui._show_api_window, frame)).\
            grid(row=row, column=column, padx=10, pady=5, sticky=tk.W) # LANG: Preferences overlay API settings button text
        return 1

    def _force_tick_button(self, frame:tk.Frame, row:int, column:int, state:str) -> int:
        """ Show the Force Tick button """

        fnt:tkfont.Font = tkfont.nametofont("TkDefaultFont").copy()
        fnt.configure(weight="bold")

        style = ttk.Style()
        style.configure('ft.TButton', font=fnt, foreground="red", relief="raised")

        ttk.Button(frame, text=_("Force Tick"), command=self._confirm_force_tick, style='ft.TButton').\
            grid(row=row, column=column, padx=10, pady=5, sticky=tk.W) # LANG: Preferences force tick button text
        return 1

    def _confirm_force_tick(self):
        """ Force a tick when user clicks button """
        message:str = _("This will move your current activity into the previous tick, and clear activity for the current tick.") + "\n\n" # LANG: Preferences force tick popup text
        message += _("WARNING: It is not usually necessary to force a tick. Only do this if you know FOR CERTAIN there has been a tick but {plugin_name} is not showing it.").format(plugin_name=self.bgstally.plugin_name) + "\n\n" # LANG: Preferences force tick popup text
        message += _("Are you sure that you want to do this?") # LANG: Preferences force tick text

        answer = askyesno(title=_("Confirm Force a New Tick"), message=message, default="no") # LANG: Preferences force tick popup title
        if answer: self.bgstally.new_tick(True, UpdateUIPolicy.IMMEDIATE)

    @catch_exceptions
    def _change_favourite(self, name:tk.Variable|str, var:tk.Variable|bool) -> None:
        """ Callback for when a favourite faction is changed or added """
        faction:str = name.get() if isinstance(name, tk.Variable) else name
        fav:bool = var.get() if isinstance(var, tk.Variable) else var

        # Add this to the list of favourite factions if it is not already there
        children:list = [child.cget("text") for child in self.fav_fr.winfo_children() if isinstance(child, nb.Checkbutton)]
        if faction not in children:
            nv:tk.BooleanVar = tk.BooleanVar(value=fav)
            n:int = len(children)
            nb.Checkbutton(self.fav_fr, text=faction, command=partial(self._change_favourite, faction, nv),
                           onvalue=True, offvalue=False, variable=nv, state=nv.get()).\
                            grid(row=(n//3), column=(n%3), padx=(0, 10), sticky=tk.W)

        Debug.logger.debug(f"Preference changed: {faction} ({fav})={fav}")
        self.bgstally.faction_manager.set_favourite(faction, fav)

    @catch_exceptions
    def _favourite_factions(self, frame:tk.Frame, row:int, column:int, state:str) -> int:
        """ Show the favourite factions list and allow the user to add or remove factions from it """
        self.fav_fr:nb.Frame = nb.Frame(frame)
        self.fav_fr.grid(row=row, column=column, columnspan=6, padx=0, pady=(0,5), sticky=tk.NSEW)

        var:tk.Variable
        for i, faction in enumerate(self.bgstally.faction_manager.factions):
            var = tk.BooleanVar(value=self.bgstally.faction_manager.is_favourite(faction))
            nb.Checkbutton(self.fav_fr, text=faction, command=partial(self._change_favourite, faction, var),
                               onvalue=True, offvalue=False, variable=var, state=var.get()). \
                grid(row=(i//3), column=(i%3), padx=(10,0), pady=(0,5), sticky=tk.W)

        row += 1
        var = tk.StringVar(value="")
        nb.EntryMenu(frame, textvariable=var, width=35, state=state, background="red"). \
            grid(row=row, column=column, padx=(10,0), pady=(5,5), sticky=tk.W)
        nb.Button(frame, text=_("Add Faction"), command=partial(self._change_favourite, var, True), state=state). \
            grid(row=row, column=column+1, pady=(5,5), sticky=tk.W) # LANG: Preferences add faction button text

        return 2
