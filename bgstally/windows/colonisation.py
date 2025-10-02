import re
from functools import partial

import webbrowser
import tkinter as tk
import tkinter.font as tkFont
import traceback
from textwrap import wrap

from math import ceil
from os import path
from tkinter import PhotoImage, messagebox, ttk
from urllib.parse import quote

from bgstally.constants import COLOUR_HEADING_1, FONT_HEADING_2, FOLDER_ASSETS, FOLDER_DATA, FONT_HEADING_1, FONT_SMALL, BuildState
from bgstally.debug import Debug
from bgstally.utils import _, get_localised_filepath, human_format, str_truncate, catch_exceptions
from bgstally.ravencolonial import RavenColonial

from config import config # type: ignore
from thirdparty.ScrollableNotebook import ScrollableNotebook
from thirdparty.tksheet import Sheet, num2alpha, natural_sort_key, ICON_DEL, ICON_ADD
from thirdparty.Tooltip import ToolTip

FILENAME_LEGEND = "colonisation_legend.txt"
SUMMARY_HEADER_ROW = 0
FIRST_SUMMARY_ROW = 1
HEADER_ROW = 3
FIRST_BUILD_ROW = 4

class ColonisationWindow:
    '''
    Window for managing colonisation plans and associated popups.

    This window allows users to view and manage colonisation plans for different systems. It creates a tab for each system,
    and uses a sheet to display both summary and detailed information about the builds in that system.

    It can create popup windows for showing base types, system notes, and system bodies.
    '''
    def __init__(self, bgstally) -> None:
        self.bgstally = bgstally
        self.colonisation = None
        self.image_tab_complete:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_enabled.png"))
        self.image_tab_progress:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_part_enabled.png"))
        self.image_tab_planned:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_disabled.png"))

        self.summary_rows:dict = {
            'Planned': _("Planned"), # LANG: Row heading of planned build totals i.e. ones that aren't complete
            'Complete': _("Complete"), # LANG: Row heading of build totals i.e. ones that are done
        }

        # Table has two sections: summary and builds. This dict defines attributes for each summary column
        self.summary_cols:dict = {
            'Track': {'header': "", 'background': None, 'hide': True, 'format': 'hidden'},
            'Architect': {'header': _("Architect"), 'background': None, 'hide': False}, # LANG: System architect heading
            'Layout': {'header': "", 'background': None, 'hide': True, 'format': 'hidden'},
            'State': {'header': "", 'background': None},
            'Total': {'header': _("Total"), 'background': None, 'format': 'int'}, # LANG: Total number of builds
            'Orbital': {'header': _("Orbital"), 'background': None, 'format': 'int'}, # LANG: Number of orbital/space builds
            'Surface': {'header': _("Surface"), 'background': None, 'format': 'int'}, # LANG: Number of ground/surface builds
            'T2': {'header': _("T2"), 'background': 'rwg', 'format': 'int', 'max': 1}, # LANG: Tier 2 points
            'T3': {'header': _("T3"), 'background': 'rwg', 'format': 'int', 'max': 1}, # LANG: Tier 3 points
            'Cost': {'header': _("Cost"), 'background': 'gyr', 'format': 'int', 'max': 200000}, # LANG: Cost in tonnes of cargo
            'Trips': {'header': _("Loads"), 'background': 'gyr', 'format': 'int', 'max': 260}, # LANG: Number of loads of cargo
            'Location': {'header': "", 'background': None, 'hide': True, 'format': 'hidden'},
            'Population': {'header': _("Pop"), 'background': None, 'hide': True, 'format': 'hidden'},
            'Economy': {'header': _("Economy"), 'background': None, 'hide': True, 'format': 'hidden'},
            'Pop Inc': {'header': _("Pop Inc"), 'background': 'rwg', 'format': 'int', 'max': 20}, # LANG: Population increase
            'Pop Max': {'header': _("Pop Max"), 'background': 'rwg', 'format': 'int', 'max': 20}, # LANG: Population Maximum
            'Economy Influence': {'header': _("Econ Inf"), 'background': None, 'hide': True, 'format': 'hidden'}, # LANG: Economy influence
            'Security': {'header': _("Security"), 'background': 'rwg', 'format': 'int', 'max': 20}, # LANG: Security impact
            'Technology Level' : {'header': _("Tech Lvl"), 'background': 'rwg', 'format': 'int', 'max': 20}, # LANG: Technology level
            'Wealth' : {'header': _("Wealth"), 'background': 'rwg', 'format': 'int', 'max': 20}, # LANG: Wealth impact
            'Standard of Living' : {'header': _("SoL"), 'background': 'rwg', 'format': 'int', 'max': 20}, # LANG: Standard of living impact
            'Development Level' : {'header': _("Dev Lvl"), 'background': 'rwg', 'format': 'int', 'max': 20} # LANG: Development level impact
        }
        # Table has two sections: summary and builds. This dict defines attributes for each build column
        self.detail_cols:dict = {
            'Track': {'header': _("Track"), 'background': None, 'format': 'checkbox', 'width':50}, # LANG: Track this build?
            'Base Type' : {'header': _("Base Type"), 'background': None, 'format': 'dropdown', 'width': 205}, # LANG: type of base
            'Layout' : {'header': _("Layout"), 'background': None, 'format': 'dropdown', 'width': 150}, # LANG: building layout
            'Name' : {'header': _("Base Name"), 'background': None, 'format': 'string', 'width': 175}, # LANG: name of the base
            'Body': {'header': _("Body"), 'background': None, 'format': 'dropdown', 'width': 115}, # LANG: Body the base is on or around
            'Body Type': {'header': _("Type"), 'background': None, 'format': 'string', 'width': 115}, # LANG: body type details
            'State': {'header': _("State"), 'background': 'type', 'format': 'string', 'width': 115}, # LANG: Current build state
            'T2': {'header': _("T2"), 'background': 'rwg', 'format': 'int', 'max':1, 'width': 30}, # LANG: Tier 2 points
            'T3': {'header': _("T3"), 'background': 'rwg', 'format': 'int', 'max':1, 'width': 30}, # LANG: Tier 3
            'Cost': {'header': _("Cost"), 'background': 'gyr', 'format': 'int', 'max':75000, 'width': 75}, # LANG: As above
            'Trips':{'header': _("Loads"), 'background': 'gyr', 'format': 'int', 'max':100, 'width': 60}, # LANG: As above
            'Location': {'header': _('Loc'), 'background': 'type', 'format': 'string', 'width': 35},    # LANG: Station location (O=Orbital, S=Surface)
            'Pad': {'header': _("Pad"), 'background': 'type', 'format': 'string', 'width': 75}, # LANG: Landing pad size
            'Facility Economy': {'header': _("Economy"), 'background': 'type', 'format': 'string', 'width': 80}, # LANG: facility economy
            'Pop Inc': {'header': _("Pop Inc"), 'background': 'rwg', 'format': 'int', 'max':5, 'width': 75}, # LANG: As above
            'Pop Max': {'header': _("Pop Max"), 'background': 'rwg', 'format': 'int', 'max':5, 'width': 75}, # LANG: As above
            'Economy Influence': {'header': _("Econ Inf"), 'background': 'type', 'format': 'string', 'width': 100}, # LANG: economy influence
            'Security': {'header': _("Security"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 70}, # LANG: As above
            'Technology Level': {'header': _("Tech Lvl"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 70}, # LANG: As above
            'Wealth': {'header': _("Wealth"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 70}, # LANG: As above
            'Standard of Living': {'header': _("SoL"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 70}, # LANG: As above
            'Development Level': {'header': _("Dev Lvl"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 70} # LANG: As above
        }
        # Table has two sections: summary and builds. This dict defines attributes for each build column
        self.bases:dict = {
            'Type' : {'header': _("Base Type"), 'background': 'type', 'format': 'string', 'width': 200}, # LANG: type of base
            'Tier' : {'header': _("Tier"), 'background': 'type', 'format': 'string', 'width': 40}, # LANG: tier of base
            'Category' : {'header': _("Category"), 'background': 'type', 'format': 'string', 'width': 125}, # LANG: category of base
            'Location' : {'header': _("Location"), 'background': 'type', 'format': 'string', 'width': 80}, # LANG: base location surface/orbital
            'Type (Listed as/under)': {'header': _("Type (Listed as)"), 'background': None, 'format': 'string', 'width': 160}, # LANG: type of base as listed in the game
            'Prerequisites': {'header': _("Requirements"), 'background': None, 'format': 'string', 'width': 175}, # LANG: any prerequisites for the base
            'T2': {'header': _("T2"), 'background': 'rwg', 'format': 'int', 'max':3, 'width': 30}, # LANG: Tier 2 points
            'T3': {'header': _("T3"), 'background': 'rwg', 'format': 'int', 'max':3, 'width': 30}, # LANG: Tier 3
            'Total Comm': {'header': _("Cost"), 'background': 'gyr', 'format': 'int', 'max':75000, 'width': 75}, # LANG: As above
            'Trips':{'header': _("Loads"), 'background': 'gyr', 'format': 'int', 'max':100, 'width': 60}, # LANG: As above
            'Pad': {'header': _("Pad"), 'background': 'type', 'format': 'string', 'width': 75}, # LANG: Landing pad size
            'Facility Economy': {'header': _("Economy"), 'background': 'type', 'format': 'string', 'width': 80}, # LANG: facility economy
            'Pop Inc': {'header': _("Pop Inc"), 'background': 'rwg', 'format': 'int', 'max':7, 'width': 75}, # LANG: As above
            'Pop Max': {'header': _("Pop Max"), 'background': 'rwg', 'format': 'int', 'max':7, 'width': 75}, # LANG: As above
            'Economy Influence': {'header': _("Econ Inf"), 'background': 'type', 'format': 'string', 'width': 100}, # LANG: economy influence
            'Security': {'header': _("Security"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 70}, # LANG: As above
            'Technology Level': {'header': _("Tech Lvl"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 70}, # LANG: As above
            'Wealth': {'header': _("Wealth"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 70}, # LANG: As above
            'Standard of Living': {'header': _("SoL"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 70}, # LANG: As above
            'Development Level': {'header': _("Dev Lvl"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 70}, # LANG: As above
            #'Building Type' : {'header': _("Building Type"), 'background': None, 'format': 'string', 'width': 175}, # LANG: Building type
            'Layouts' : {'header': _("Building Layouts (click for details)"), 'background': None, 'format': 'string', 'width': 200}, # LANG: Building layout types
            'Boosted By': {'header': _("Boosted By"), 'background': None, 'format': 'string', 'width': 300}, # LANG: any boost effects for the base
            'Decreased By': {'header': _("Decreased By"), 'background': None, 'format': 'string', 'width': 250}, # LANG: any decrease effects for the base
        }
        # Colours for the various types of bases, states, and sizes
        self.colors = {
            'Contraband': '#ebc296', 'Agricultural': '#bbe1ba', 'Extraction' : '#dbeeef',
            'High Tech' : '#c0e1ff', 'Military' : '#94A590', 'Tourism' : '#bac9e5',
            'Industrial' : '#d1c3b7', 'Refinery' : '#92bbe0', 'Colony' : '#d4f2cc', 'None': '#e8eaed',
            'Small' : '#d4edbc', 'Medium' : '#dbe5ff', 'Large': '#dbceff',
            '1' : '#d4edbc', '2' : '#dbe5ff', '3' : '#dbceff',
            'Orbital' : '#d5deeb', 'Surface' : '#ebe6db',
            'Starport' : '#dce9cb', 'Outpost' : '#ddebff', 'Installation' : '#ffe5a0',
            'Planetary Outpost' : "#ddf5f5", 'Planetary Port': '#c0e1ff', 'Settlement' : '#bbe1ba', 'Hub' : '#bac9e5',
            'Planned' : '#ffe5a0', 'Progress' : '#f5b60d', 'Complete' : '#d4edbc', #'#5a3286',
            'L' : '#d4edbc', 'M' : '#dbe5ff', 'O' : '#d5deeb', 'S' : '#ebe6db', 'C' : '#e6dbeb'
        }

        # Links to systems, bodies etc.
        self.links:dict = {'System': {'Inara': 'https://inara.cz/elite/starsystem/search/?search={StarSystem}',
                                      'Spansh': 'https://www.spansh.co.uk/system/{SystemAddress}',
                                      'EDGIS': 'https://elitedangereuse.fr/outils/sysmap.php?system={StarSystem}',
                                      'EDSM': 'https://www.edsm.net/en/system?systemName={StarSystem}',
                                      'RavenColonial': 'https://ravencolonial.com/#sys={StarSystem}'},
                           'Bodies': {'Inara': 'https://inara.cz/elite/starsystem-bodies/search/?search={StarSystem}',
                                      'Spansh': 'https://www.spansh.co.uk/system/{SystemAddress}#system-bodies',
                                      'EDGIS': 'https://elitedangereuse.fr/outils/sysmap.php?system={StarSystem}'},
                           'Base':   {'RavenColonial': 'https://ravencolonial.com/#vis={Layout}'}
                            }
        # UI components'
        self.window:tk.Toplevel = None # type: ignore
        self.tabbar:ScrollableNotebook = None # type: ignore
        self.add_dialog:tk.Frame|None = None
        self.react:tk.Frame|None = None
        self.sheets:list = []
        self.plan_titles:list = []
        self.legend_fr:tk.Toplevel|None = None
        self.notes_fr:tk.Toplevel|None = None
        self.bases_fr:tk.Toplevel|None = None
        self.bodies_fr:tk.Toplevel|None = None
        self.scale:float = 0


    @catch_exceptions
    def show(self) -> None:
        ''' Create and display the colonisation window. Called by ui.py when the colonisation icon is clicked. '''
        if self.window != None and self.window.winfo_exists():
            self.window.lift()
            return
        self.scale = config.get_int('ui_scale') / 100.00
        self.colonisation = self.bgstally.colonisation
        self.window:tk.Toplevel = tk.Toplevel(self.bgstally.ui.frame)
        self.window.title(_("{plugin_name} - Colonisation").format(plugin_name=self.bgstally.plugin_name)) # LANG: window title

        self.window.minsize(400, 100)
        self.window.geometry(f"{int(1500*self.scale)}x{int(500*self.scale)}")
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self._create_frames()   # Create main frames
        self.update_display()   # Populate them


    @catch_exceptions
    def _create_frames(self) -> None:
        ''' Create the system frame notebook and tabs for each system '''
        # Create system tabs notebook
        self.tabbar = ScrollableNotebook(self.window, wheelscroll=True, tabmenu=False)
        self.tabbar.pack(fill=tk.BOTH, side=tk.TOP, expand=True, padx=5, pady=5)
        self.add_dialog = self.add_system_dialog()
        self.update_react_dialog()
        self.tabbar.add(self.add_dialog, text='+')

        # Add tabs for each system
        systems:list = self.colonisation.get_all_systems()
        if len(systems) == 0:
            Debug.logger.info(f"No systems so not creating colonisation section")
            return

        for sysnum, system in enumerate(systems): # Create a frame for the sytem
            tabnum = sysnum + 1
            self._create_system_tab(tabnum, system)

        if tabnum > 0:
            for t in range(0, tabnum-1):
                if systems[t].get('Hidden', True) == False:
                    break
            self.tabbar.select(t+1) # Select the first non-hidden system tab


    @catch_exceptions
    def _create_system_tab(self, tabnum:int, system:dict) -> None:
        ''' Create the frame, title, and sheet for a system '''
        tab:ttk.Frame = ttk.Frame(self.tabbar)
        tab.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)

        self._create_title_frame(tabnum, tab)
        self._create_table_frame(tabnum, tab, system)
        self.tabbar.add(tab, text=system['Name'], compound='right', image=self.image_tab_planned)
        self.tabbar.select(tabnum)

        self._set_system_progress(tabnum, system)

        if system.get('Hidden', False) == True:
            self.tabbar.notebookTab.tab(tabnum, state='hidden')


    @catch_exceptions
    def _set_system_progress(self, tabnum:int, system:dict) -> None:
        ''' Update the tab image based on the system's progress '''
        tabstate:BuildState = BuildState.COMPLETE
        for b in system['Builds']:
            build_state = self.colonisation.get_build_state(b)
            if build_state == BuildState.PLANNED and tabstate != BuildState.PROGRESS:
                tabstate = BuildState.PLANNED
            if build_state == BuildState.PROGRESS:
                tabstate = BuildState.PROGRESS

        match tabstate:
            case BuildState.COMPLETE:
                self.tabbar.notebookTab.tab(tabnum, image=self.image_tab_complete)
            case BuildState.PROGRESS:
                self.tabbar.notebookTab.tab(tabnum, image=self.image_tab_progress)
            case BuildState.PLANNED:
                self.tabbar.notebookTab.tab(tabnum, image=self.image_tab_planned)


    @catch_exceptions
    def _create_title_frame(self, tabnum:int, tab:ttk.Frame) -> None:
        ''' Create the title frame with system name and tick info '''
        sysnum:int = tabnum -1
        systems:list = self.colonisation.get_all_systems()

        title_frame:ttk.Frame = ttk.Frame(tab, style="Title.TFrame")
        title_frame.pack(fill=tk.X, padx=0, pady=(0, 5))

        # Configure style for title frame
        style:ttk.Style = ttk.Style()
        style.configure("Title.TFrame")

        # System name label
        while len(self.plan_titles) <= sysnum:
            self.plan_titles.append({})

        name_label:ttk.Label = ttk.Label(title_frame, text="", font=FONT_HEADING_1, foreground=COLOUR_HEADING_1)
        sysname:str = systems[sysnum].get('StarSystem', '')
        if systems[sysnum].get('RCSync', False) == True:
            name_label = ttk.Label(title_frame, text="", font=FONT_HEADING_1, foreground="#0078d4", cursor="hand2")
            name_label.bind("<Button-1>", partial(self._link, systems[sysnum], 'System', 'RavenColonial'))
            ToolTip(name_label, text=_("Link to RavenColonial")) # LANG: tooltip for ravencolonial link
        name_label.pack(side=tk.LEFT, padx=10, pady=5)
        self.plan_titles[sysnum]['Name'] = name_label

        if sysname != '':
            sys_label:ttk.Label = ttk.Label(title_frame, text=sysname, cursor="hand2")
            sys_label.pack(side=tk.LEFT, padx=5, pady=5)
            self._set_weight(sys_label)
            sys_label.bind("<Button-1>", partial(self._link, systems[sysnum], 'System', ''))
            sys_label.bind("<Button-3>", partial(self._context_menu, systems[sysnum], 'System'))
            ToolTip(sys_label, text=_("Left click view system, right click menu")) # LANG: tooltip for the copy to clipboard icon
            self._set_weight(sys_label)
            self.plan_titles[sysnum]['System'] = sys_label

        if systems[sysnum].get('Bodies', None) != None and len(systems[sysnum]['Bodies']) > 0:
            bodies:str = str(len(systems[sysnum]['Bodies'])) + " " + _("Bodies") # LANG: bodies in the system
            sys_bodies:ttk.Label = ttk.Label(title_frame, text=bodies, cursor="hand2")
            sys_bodies.pack(side=tk.LEFT, padx=10, pady=5)
            ToolTip(sys_bodies, text=_("Show system bodies window")) # LANG: tooltip for the show bodies window
            self._set_weight(sys_bodies)
            sys_bodies.bind("<Button-1>", partial(self.bodies_popup, tabnum))
            sys_bodies.bind("<Button-3>", partial(self._context_menu, systems[sysnum], 'Bodies'))

        allattrs:dict = {'Population': _('Population'), # HINT: Population heading
                         'Economy' : _('Economy'), # HINT: Economy heading
                         'Security' : _('Security')} # HINT: Security heading
        attrs:list = []
        for k, v in allattrs.items():
            if systems[sysnum].get(k, '') != '' and systems[sysnum].get(k, '') != None:
                if isinstance(systems[sysnum].get(k), int):
                    attrs.append(f"{human_format(systems[sysnum].get(k))} {v}")
                else:
                    attrs.append(f"{systems[sysnum].get(k)} {_(v)}")
        details:ttk.Label = ttk.Label(title_frame, text="   ".join(attrs))
        self._set_weight(details)
        details.pack(side=tk.LEFT, padx=10, pady=5)

        btn:ttk.Button = ttk.Button(title_frame, text=_("ⓘ"), width=3, cursor="hand2", command=lambda: self.legend_popup())
        btn.pack(side=tk.RIGHT, padx=(20, 5), pady=5)
        ToolTip(btn, text=_("Show legend window")) # LANG: tooltip for the show legend button

        btn:ttk.Button = ttk.Button(title_frame, text=_("🗑️"), width=3, cursor="hand2", command=lambda: self.delete_system(tabnum, tab)) # LANG: Delete button
        ToolTip(btn, text=_("Delete system plan")) # LANG: tooltip for the delete system button
        btn.pack(side=tk.RIGHT, padx=5, pady=5)

        #btn:ttk.Button = ttk.Button(title_frame, text=_("👁"), width=3, cursor="hand2", command=lambda: self.hide_system(tabnum, tab)) # LANG: Hide button
        #ToolTip(btn, text=_("Hide system plan")) # LANG: tooltip for the hide system button
        #btn.pack(side=tk.RIGHT, padx=5, pady=5)

        btn:ttk.Button = ttk.Button(title_frame, text=_("📝"), width=3, cursor="hand2", command=lambda: self.edit_system_dialog(tabnum, btn)) # LANG: Rename button
        ToolTip(btn, text=_("Edit system plan")) # LANG: tooltip for the edit system button
        btn.pack(side=tk.RIGHT, padx=5, pady=5)

        btn:ttk.Button = ttk.Button(title_frame, text="🔍", width=3, cursor="hand2", command=lambda: self.bases_popup())
        btn.pack(side=tk.RIGHT, padx=(5,20), pady=5)
        ToolTip(btn, text=_("Show base types window")) # LANG: tooltip for the show bases button

        if systems[sysnum].get('Bodies', None) != None and len(systems[sysnum]['Bodies']) > 0:
            btn:ttk.Button = ttk.Button(title_frame, text="🌐", width=3, cursor="hand2", command=partial(self.bodies_popup, tabnum))
            btn.pack(side=tk.RIGHT, padx=5, pady=5)
            ToolTip(btn, text=_("Show system bodies window")) # LANG: tooltip for the show bodies window


        # 📓 📝 📋
        btn:ttk.Button = ttk.Button(title_frame, text=_("📋"), cursor="hand2", width=3, command=partial(self.notes_popup, tabnum))
        btn.pack(side=tk.RIGHT, padx=5, pady=5)
        ToolTip(btn, text=_("Show system notes window")) # LANG: tooltip for the show notes window

        if systems[sysnum].get('RCSync', False) == True:
            #🔄 ⟳
            btn:ttk.Button = ttk.Button(title_frame, text=_("🔄"), cursor="hand2", width=3, command=partial(self._rc_refresh_system, tabnum))
            btn.pack(side=tk.RIGHT, padx=5, pady=5)
            ToolTip(btn, text=_("Refresh from RavenColonial")) # LANG: tooltip for ravencolonial refresh button


    @catch_exceptions
    def _context_menu(self, system:dict, type:str, event: tk.Event) -> None:
        """ Display the context menu when right-clicked."""

        menu = tk.Menu(tearoff=tk.FALSE)
        if type == 'System':
            menu.add_command(label=_('Copy'), command=partial(self._ctc, system['StarSystem']))  # As in Copy and Paste
            menu.add_separator()

        for which in self.links[type].keys():
            menu.add_command(label=_("Open in {w}").format(w=which),  # LANG: Open Element In Selected Provider
                             command=partial(self._link, system, type, which))
        menu.post(event.x_root, event.y_root)


    @catch_exceptions
    def _ctc(self, text:str, event = None) -> None:
        ''' Copy to clipboard '''
        self.window.clipboard_clear()
        self.window.clipboard_append(text)


    @catch_exceptions
    def _link(self, data:dict, type:str = '', dest:str= '', event = None) -> None:
        if dest == '' or dest == None:
            dest = config.get_str('system_provider')
        if type not in self.links.keys():
            Debug.logger.debug(f"Unknown link type: {type}")
            return
        if dest not in self.links[type].keys():
            Debug.logger.debug(f"Unknown destination: {dest}")
            return
        params:dict = {k: quote(str(v)) if str(k) != 'Layout' else str(v).strip().lower().replace(" ","_") for k, v in data.items()}
        webbrowser.open(self.links[type][dest].format(**params))


    @catch_exceptions
    def _base_clicked(self, sheet:Sheet, event) -> None:
        ''' We clicked on a base type, open it in RC '''
        sheet.toggle_select_row(event.selected.row, False, True)
        if event.selected.column == 20:
            layouts:str = str(sheet[self._cell(event['selected'].row, 20)].data)
            self._link({'Layout': layouts.split(', ')[0]}, 'Base', 'RavenColonial')


    @catch_exceptions
    def bases_popup(self) -> None:
        ''' Show a popup with details of all the base types '''
        if self.bases_fr != None and self.bases_fr.winfo_exists():
            self.bases_fr.lift()
            return

        self.bases_fr = tk.Toplevel(self.bgstally.ui.frame)
        self.bases_fr.wm_title(_("{plugin_name} - Colonisation Base Types").format(plugin_name=self.bgstally.plugin_name)) # LANG: Title of the base type popup window
        self.bases_fr.geometry(f"{int(1000*self.scale)}x{int(500*self.scale)}")
        self.bases_fr.protocol("WM_DELETE_WINDOW", self.bases_fr.destroy)
        self.bases_fr.config(bd=2, relief=tk.FLAT)
        header_fnt:tuple = (FONT_SMALL[0], FONT_SMALL[1], "bold")
        sheet:Sheet = Sheet(self.bases_fr, sort_key=natural_sort_key, note_corners=True, show_row_index=False, cell_auto_resize_enabled=True, height=4096,
                        show_horizontal_grid=True, show_vertical_grid=True, show_top_left=False,
                        align="center", show_selected_cells_border=True, table_selected_cells_border_fg='',
                        show_dropdown_borders=False, header_bg='lightgrey', header_selected_cells_bg='lightgrey',
                        empty_vertical=0, empty_horizontal=0, header_font=header_fnt, font=FONT_SMALL, arrow_key_down_right_scroll_page=True,
                        show_header=True, default_row_height=int(19*self.scale))
        sheet.pack(fill=tk.BOTH, padx=0, pady=0)
        sheet.enable_bindings('single_select', 'column_select', 'row_select', 'drag_select', 'column_width_resize', 'right_click_popup_menu', 'copy', 'sort_rows')
        sheet.extra_bindings('cell_select', func=partial(self._base_clicked, sheet))
        data:list = [[0 for _ in range(len(self.bases.keys()))] for _ in range(len(self.colonisation.get_base_types()))]
        sheet.set_header_data([h['header'] for h in self.bases.values()], redraw=False)
        sheet.set_sheet_data(data, redraw=False)
        sheet["A1:A100"].align(align='left')
        sheet["E1:F100"].align(align='left')
        sheet["U1:W100"].align(align='left')

        for i, bt in enumerate(self.colonisation.base_types.values()):
            for j, (name, col) in enumerate(self.bases.items()):
                sheet.column_width(j, col.get('width', 100))
                match col.get('format'):
                    case 'int':
                        v:int = bt.get(name, 0)
                        if name in ['T2', 'T3']:
                            v = bt.get(name+' Reward', 0) - bt.get(name + ' Cost', 0)
                        if name == 'Trips':
                            v = ceil(bt['Total Comm'] / self.colonisation.cargo_capacity)
                        sheet[self._cell(i,j)].data = ' ' if v == 0 else f"{v:,}"
                        sheet[self._cell(i,j)].highlight(bg=self._set_background(col.get('background'), str(v), col.get('max')), redraw=False)
                    case _:
                        sheet[self._cell(i,j)].data = bt.get(name) if bt.get(name, ' ') != ' ' else bt.get(name, ' ')
                        if name == 'Type': # Special case.
                            econ = bt.get('Economy Influence') if bt.get('Economy Influence') != "" else bt.get('Facility Economy')
                            sheet[self._cell(i,j)].highlight(bg=self._set_background(col.get('background'), econ if econ else 'None'), redraw=False)
                        else:
                            sheet[self._cell(i,j)].highlight(bg=self._set_background(col.get('background'), bt.get(name, ' ')), redraw=False)

        sheet.set_all_column_widths(width=None, only_set_if_too_small=True, redraw=True, recreate_selection_boxes=True)


    @catch_exceptions
    def bodies_popup(self, tabnum:int, event = None) -> None:
        ''' Show a popup with details of all the bodies in the system '''
        if self.bodies_fr != None and self.bodies_fr.winfo_exists():
            self.bodies_fr.destroy()

        self.bodies_fr = tk.Toplevel(self.bgstally.ui.frame)
        self.bodies_fr.wm_title(_("{plugin_name} - Colonisation Bodies").format(plugin_name=self.bgstally.plugin_name)) # LANG: Title of the bodies popup window
        self.bodies_fr.wm_attributes('-toolwindow', True) # makes it a tool window
        self.bodies_fr.minsize(600, 600)
        self.bodies_fr.geometry(f"{int(600*self.scale)}x{int(600*self.scale)}")
        self.bodies_fr.config(bd=2, relief=tk.FLAT)
        scr:tk.Scrollbar = tk.Scrollbar(self.bodies_fr, orient=tk.VERTICAL)
        scr.pack(side=tk.RIGHT, fill=tk.Y)
        text:tk.Text = tk.Text(self.bodies_fr, font=FONT_SMALL, yscrollcommand=scr.set)
        text.pack(fill=tk.BOTH, side=tk.TOP, expand=True, padx=5, pady=5)

        sysnum:int = tabnum - 1
        systems:list = self.colonisation.get_all_systems()

        bodies:list = systems[sysnum].get('Bodies', None)
        if bodies == None:
            return

        # Go through the bodies and format the output for display
        bstr:str = f"{bodies[0].get('name')} - {bodies[0].get('subType')}\n\n"
        for b in bodies[1:]:
            indent:int = 0 if b.get('parents', None) == None else b.get('parents') * 4
            name:str = b.get('name')
            name = name.replace(systems[sysnum]['StarSystem'] + ' ', '')

            bstr += f"{' ' * indent}{name} - {b.get('subType')}"
            if b.get('distanceToArrival'):
                bstr += (f", {human_format(b.get('distanceToArrival'))}Ls")
            bstr += "\n"

            attrs:list = []
            if b.get('isLandable') == True: attrs.append(_('Landable'))
            if b.get('rotationalPeriodTidallyLocked') == True: attrs.append(_('Tidally Locked'))
            rings:list = []
            for r in b.get('rings', []):
                if r.get('type', None) != None: rings.append(r.get('type'))
            if len(rings):
                attrs.append(b.get('reserveLevel') + " " +_("rings") + ": " + ", ".join(rings))

            if b.get('type') == 'Planet':
                if b.get('terraformingState') == 'Terraformable': attrs.append(_("Terraformable"))
                if b.get('atmosphereType') != 'No atmosphere' or len(attrs):
                    astr:str = b.get('atmosphereType', 'No atmosphere')
                    if astr != 'No atmosphere': astr += " atmosphere"
                    attrs.append(astr)
                if b.get('volcanismType', 'No volcanism') != 'No volcanism': attrs.append(b.get('volcanismType'))

            if len(attrs) > 0:
                bstr += f"{' ' * (indent+8)}"
                bstr += ", ".join(attrs)
                bstr += "\n"
            bstr += "\n"

        text.insert(tk.END, bstr)


    @catch_exceptions
    def notes_popup(self, tabnum:int) -> None:
        ''' Show the notes popup window '''
        def savenotes(system:dict, text:tk.Text) -> None:
            ''' Save the notes and close the popup window '''
            if sysnum > len(self.plan_titles):
                Debug.logger.info(f"Saving notes invalid tab: {tabnum}")
                return

            notes:str = text.get("1.0", tk.END)
            system['Notes'] = notes.strip()
            self.colonisation.save("Notes popup close")
            self.notes_fr.destroy()
            self.notes_fr

        sysnum:int = tabnum -1
        systems:list = self.colonisation.get_all_systems()

        if self.notes_fr != None and self.notes_fr.winfo_exists():
            self.notes_fr.destroy()

        self.notes_fr = tk.Toplevel(self.bgstally.ui.frame)
        self.notes_fr.wm_title(_("{plugin_name} - Colonisation Notes for {system_name}").format(plugin_name=self.bgstally.plugin_name, system_name=systems[sysnum].get('Name', ''))) # LANG: Title of the notes popup window
        self.notes_fr.wm_attributes('-topmost', True)     # keeps popup above everything until closed.
        self.notes_fr.geometry("600x600")
        self.notes_fr.config(bd=2, relief=tk.FLAT)
        scr:tk.Scrollbar = tk.Scrollbar(self.notes_fr, orient=tk.VERTICAL)
        scr.pack(side=tk.RIGHT, fill=tk.Y)

        text:tk.Text = tk.Text(self.notes_fr, font=FONT_SMALL, yscrollcommand=scr.set)
        notes:str = systems[sysnum].get('Notes', '')
        text.insert(tk.END, notes)
        text.pack(fill=tk.BOTH, side=tk.TOP, expand=True, padx=5, pady=5)
        self.notes_fr.protocol("WM_DELETE_WINDOW", partial(savenotes, systems[sysnum], text))


    @catch_exceptions
    def legend_popup(self) -> None:
        ''' Show the legend popup window '''
        if self.legend_fr != None and self.legend_fr.winfo_exists():
            self.legend_fr.lift()
            return

        self.legend_fr = tk.Toplevel(self.bgstally.ui.frame)
        self.legend_fr.wm_title(_("{plugin_name} - Colonisation Legend").format(plugin_name=self.bgstally.plugin_name)) # LANG: Title of the legend popup window
        self.legend_fr.wm_attributes('-topmost', True)     # keeps popup above everything until closed.
        self.legend_fr.wm_attributes('-toolwindow', True) # makes it a tool window
        self.legend_fr.geometry(f"600x600")
        self.legend_fr.config(bd=2, relief=tk.FLAT)
        scr:tk.Scrollbar = tk.Scrollbar(self.legend_fr, orient=tk.VERTICAL)
        scr.pack(side=tk.RIGHT, fill=tk.Y)

        text:tk.Text = tk.Text(self.legend_fr, font=FONT_SMALL, yscrollcommand=scr.set)
        text.insert(tk.END, self._load_legend())
        text.pack(fill=tk.BOTH, side=tk.TOP, expand=True, padx=5, pady=5)


    @catch_exceptions
    def _create_table_frame(self, tabnum:int, tab:ttk.Frame, system:dict) -> None:
        ''' Create a unified table frame with both summary and builds in a single scrollable area '''
        # Main table frame
        table_frame:ttk.Frame = ttk.Frame(tab)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Configure the table frame to resize with the window
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        sheet:Sheet = Sheet(table_frame, cell_auto_resize_enabled=True, show_row_index=False, height=4096,
                            show_horizontal_grid=True, show_vertical_grid=False, show_top_left=False,
                            align="center", show_selected_cells_border=True, table_selected_cells_border_fg='',
                            show_dropdown_borders=False,
                            empty_vertical=15, empty_horizontal=0,
                            popup_menu_font=FONT_SMALL, font=FONT_SMALL, index_font=FONT_SMALL,
                            arrow_key_down_right_scroll_page=True,
                            show_header=False, set_all_heights_and_widths=True, default_row_height=int(19*self.scale))
        sheet.pack(fill=tk.BOTH, padx=0, pady=(0, 5))

        # Initial cell population
        data:list = []
        data.append(self._get_summary_header())
        data += self._build_summary(system)
        data.append(self._get_detail_header())
        data += self._build_detail(system)
        sheet.set_sheet_data(data)

        self._config_sheet(sheet, system)
        sheet.enable_bindings('single_select', 'drag_select', 'edit_cell', 'arrowkeys', 'right_click_popup_menu', 'copy', 'cut', 'paste', 'delete', 'undo')
        sheet.edit_validation(func=partial(self._validate_edits, sheet))
        sheet.extra_bindings(['all_modified_events', 'cell_select', 'ctrl_row_select', 'rc_delete_row', 'rc_insert_row'], func=partial(self.sheet_modified, sheet, tabnum))

        sheet.popup_menu_add_command(label="Insert build above", func=partial(self._row_modified, sheet, tabnum, 'InsAbove'), image=tk.PhotoImage(data=ICON_ADD), compound="left")
        sheet.popup_menu_add_command(label="Insert build below", func=partial(self._row_modified, sheet, tabnum, 'InsBelow'), image=tk.PhotoImage(data=ICON_ADD), compound="left")
        sheet.popup_menu_add_command(label="Delete build", func=partial(self._row_modified, sheet, tabnum, 'Delete'), image=tk.PhotoImage(data=ICON_DEL), compound="left")

        if len(self.sheets) < tabnum:
            self.sheets.append(sheet)
        else:
            self.sheets[tabnum-1] = sheet


    @catch_exceptions
    def _row_modified(self, sheet:Sheet, tabnum:int, action:str) -> None:
        """
        Function to display a custom popup menu at the event coordinates.
        """

        selected = sheet.get_currently_selected()
        row:int = selected.row - FIRST_BUILD_ROW                            # type: ignore
        if row < 0: return

        sysnum:int = tabnum -1
        systems:list = self.colonisation.get_all_systems()
        system:dict = systems[sysnum]

        match action:
            case 'InsAbove':
                self.colonisation.add_build(system, {'BuildType': '',
                                                     'Name': '',
                                                     'Row': row})
            case 'InsBelow':
                self.colonisation.add_build(system, {'BuildType': '',
                                                     'Name': '',
                                                     'Row': row+1})
            case 'Delete':
                self.colonisation.remove_build(system, row)
                sheet.del_row(row)
                self._config_sheet(self.sheets[sysnum], system)
        self.update_display()


    @catch_exceptions
    def _update_title(self, index:int, system:dict) -> None:
        ''' Update title with both display name and actual system name '''
        name:str = system.get('Name','') if system.get('Name',None) != None else system.get('StarSystem', _('Unknown')) # LANG: Default when we don't know the name
        sysname:str = system.get('StarSystem', '') if system.get('StarSystem') != '' else ''

        self.plan_titles[index]['Name']['text'] = name
        self.plan_titles[index]['System']['text'] = sysname

        # Hide the system name if it hasn't been set
        if sysname == None:
            self.plan_titles[index]['System'].pack_forget()


    @catch_exceptions
    def _config_sheet(self, sheet:Sheet, system:dict|None = None) -> None:
        ''' Initial sheet configuration. '''
        sheet.dehighlight_all()

        # Column widths
        for i, (name, value) in enumerate(self.detail_cols.items()):
            sheet.column_width(i, value.get('width', 100))

        # header lines
        sheet[SUMMARY_HEADER_ROW].highlight(bg='lightgrey')
        sheet['A2:G2'].highlight(bg=self._set_background('type', 'Planned', 1))
        sheet['A3:G3'].highlight(bg=self._set_background('type', 'Complete', 1))
        sheet[HEADER_ROW].highlight(bg='lightgrey')
        # Tracking checkboxes
        sheet[f"{num2alpha(self._detcol('Track'))}6:{num2alpha(self._detcol('Track'))}"].checkbox(state='normal', checked=False)

        # Base types
        sheet[f"{num2alpha(self._detcol('Base Type'))}5"].dropdown(values=[' '] + self.colonisation.get_base_types('Initial'))
        sheet[f"{num2alpha(self._detcol('Base Type'))}6:{num2alpha(self._detcol('Base Type'))}"].dropdown(values=[' '] + self.colonisation.get_base_types('All'))

        # Base layouts dropdown
        sheet[f"{num2alpha(self._detcol('Layout'))}5"].dropdown(values=[' '] + self.colonisation.get_base_layouts('Initial'))
        sheet[f"{num2alpha(self._detcol('Layout'))}6:{num2alpha(self._detcol('Layout'))}"].dropdown(values=[' '] + self.colonisation.get_base_layouts('All'))

        if system != None and 'Bodies' in system:
            bodies:list = self.colonisation.get_bodies(system)
            if len(bodies) > 0:
                sheet[f"{num2alpha(self._detcol('Body'))}5:{num2alpha(self._detcol('Body'))}"].dropdown(values=[' '] + bodies)

        # Make the sections readonly that users can't edit.
        sheet['A1:4'].readonly()
        sheet['B2'].readonly(False) # Except Architect

        sheet[f"{num2alpha(self._detcol('Body Type'))}4:{num2alpha(len(self.detail_cols.keys())-1)}"].readonly() # Build columns from Body onwards
        # track, types, layouts, and names left.
        sheet[f"A{FIRST_BUILD_ROW}:C"].align(align='left')
        sheet[f"E"].align(align='left')


    @catch_exceptions
    def _get_summary_header(self) -> list[str]:
        ''' Return the header row for the summary '''
        cols:list = []
        for c, v in self.summary_cols.items():
            cols.append(v.get('header', c) if v.get('hide') != True else ' ')
        return cols


    @catch_exceptions
    def _calc_totals(self, system:dict) -> dict[str, dict[str, int]]:
        ''' Build a summary of the system's builds and status. '''
        totals:dict = {'Planned': {}, 'Complete': {}}
        builds:list = system.get('Builds', [])
        required:dict = self.colonisation.get_required(builds)

        for name, col in self.summary_cols.items():
            if col.get('hide') == True:
                totals['Planned'][name] = ' '
                totals['Complete'][name] = ' '
                continue

            totals['Planned'][name] = 0
            totals['Complete'][name] = 0

            # Calculate summary values
            for row, build in enumerate(builds):
                bt:dict = self.colonisation.get_base_type(build.get('Base Type', ''))
                if bt == {}:
                    continue
                match name:
                    case 'Architect':
                        totals['Planned'][name] = system.get('Architect', _('Unknown'))
                        totals['Complete'][name] = ' '
                    case 'State':
                        totals['Planned'][name] = _("Planned")
                        totals['Complete'][name] = _("Complete")
                    case 'Total':
                        totals['Planned'][name] += 1
                        totals['Complete'][name] += 1 if self.is_build_complete(build) else 0
                    case 'Orbital'|'Surface' if bt.get('Location') == name:
                        totals['Planned'][name] += 1
                        totals['Complete'][name] += 1 if self.is_build_complete(build) else 0
                    case 'T2' | 'T3':
                        v:int = self._calc_points(name, builds, row)
                        totals['Planned'][name] += v
                        totals['Complete'][name] += v if self.is_build_started(build) and v < 1 else 0 # Need to substract points as soon as build starts as the points are nolonger available
                        totals['Complete'][name] += v if self.is_build_complete(build) else 0
                    case 'Population':
                        totals['Planned'][name] = ' '
                        totals['Complete'][name] = human_format(system.get('Population', 0))
                    case 'Development Level':
                        res:int = bt.get(name, 0)
                        totals['Planned'][name] += res
                        totals['Complete'][name] += res if self.is_build_complete(build) else 0
                    case 'Cost' if row < len(required):
                        res:int = sum(required[row].values())
                        totals['Planned'][name] += res
                        totals['Complete'][name] += res if self.is_build_complete(build) else 0
                    case 'Trips' if row < len(required):
                        trips:int = ceil(sum(required[row].values()) / self.colonisation.cargo_capacity)
                        totals['Planned'][name] += trips
                        totals['Complete'][name] += trips if self.is_build_complete(build) else 0
                    case _ if col.get('format') == 'int':
                        totals['Planned'][name] += bt.get(name, 0)
                        totals['Complete'][name] += bt.get(name, 0) if self.is_build_complete(build) else 0

        # Deal with the "if you have a starport (t2 orbital or higher) your tech level will be at least 35" rule
        starports:list = self.colonisation.get_base_types('Starport')
        min:int = 35 if len([1 for build in builds if build.get('Base Type') in starports]) > 0 else 0
        totals['Planned']['Technology Level'] = max(totals['Planned']['Technology Level'], min)
        min:int = 35 if len([1 for build in builds if build.get('Base Type') in starports and self.is_build_complete(build)]) > 0 else 0
        totals['Complete']['Technology Level'] = max(totals['Complete']['Technology Level'], min)

        return totals


    @catch_exceptions
    def _build_summary(self, system:dict) -> list[list]:
        ''' Return the summary section with current system data '''
        totals:dict = self._calc_totals(system)

        # Update the values in the cells.
        summary:list = []
        for i, r in enumerate(self.summary_rows.keys()):
            row:list = []
            for (name, col) in self.summary_cols.items():
                if col.get('hide', False) == True:
                    row.append(' ')
                    continue
                row.append(totals[r].get(name, 0))
            summary.append(row)

        return summary


    @catch_exceptions
    def _update_summary(self, srow:int, sheet:Sheet, system:dict) -> None:
        ''' Update the summary section with current system data '''
        scol:int = 0
        new:list = self._build_summary(system)

        for i, x in enumerate(self.summary_rows.keys()):
            for j, details in enumerate(self.summary_cols.values()):
                sheet[self._cell(i+srow,j)].data = ' ' if new[i][j] == 0 else f"{new[i][j]:,}" if details.get('format') == 'int' else new[i][j]
                if details.get('background') != None:
                    sheet[self._cell(i+srow,j+scol)].highlight(bg=self._set_background(details.get('background'), new[i][j], details.get('max', 1)))


    @catch_exceptions
    def _get_detail_header(self) -> list[str]:
        ''' Return the details header row '''
        cols:list = []
        for c, v in self.detail_cols.items():
            cols.append(v.get('header', c) if v.get('hide') != True else ' ')
        return cols


    @catch_exceptions
    def _build_detail(self, system:dict) -> list[list]:
        ''' Build a data cube of info to update the table '''
        details:list = []
        builds:list = system.get('Builds', [])
        reqs:dict = self.colonisation.get_required(builds)
        delivs:dict = self.colonisation.get_delivered(builds)

        for i, build in enumerate(builds):
            bt:dict = self.colonisation.get_base_type(build.get('Base Type', ' '))
            row:list = []
            for name, col in self.detail_cols.items():
                match col.get('format'):
                    case 'checkbox':
                        row.append(self.is_build_complete(build) != True and build.get(name, False) == True)

                    case 'int':
                        v:int = bt.get(name, 0)
                        if name in ['T2', 'T3']:
                            v = self._calc_points(name, builds, i)
                        if name == 'Cost' and i < len(reqs):
                            v = sum(reqs[i].values())
                        if name == 'Trips' and i < len(reqs):
                            v = ceil(sum(reqs[i].values()) / self.colonisation.cargo_capacity)
                        row.append(v if v != 0 else ' ')

                    case _:
                        match name:
                            case 'State':
                                match self.colonisation.get_build_state(build):
                                    case BuildState.PLANNED if build.get('Base Type', '') != '':
                                        row.append(_("Planned"))    # LANG: Planned (not started) state for a build
                                    case BuildState.PROGRESS if i < len(reqs) and build.get('MarketID', None) != None:
                                        # @TODO: Make this a progress bar, maybe?
                                        req = sum(reqs[i].values())
                                        deliv = sum(delivs[i].values())
                                        row.append(f"{int(deliv * 100 / req)}%" if req > 0 else 0)
                                    case BuildState.PROGRESS:
                                        row.append(_("Progress")) # LANG: In progress (building) state for a build
                                    case BuildState.COMPLETE:
                                        row.append(_("Complete")) # LANG: Complete (finished) state for a build
                                    case _:
                                        row.append(' ')
                                continue
                            case 'Body' if build.get('Body', None) != None and system.get('StarSystem', '') != '':
                                row.append(self.colonisation.body_name(system.get('StarSystem', ''), build.get('Body')))
                                continue
                            case 'Location':
                                row.append(bt.get(name, ' ')[0:1])
                                continue

                        row.append(build.get(name) if build.get(name, ' ') != ' ' else bt.get(name, ' '))

            details.append(row)

        # Is the last line an uncategorized base? If not add another
        if len(details) == 0 or details[-1][1] != ' ':
            row:list = [' '] * (len(list(self.detail_cols.keys())) -1)
            details.append(row)

        return details


    @catch_exceptions
    def _update_detail(self, srow:int, sheet:Sheet, system:dict) -> None:
        ''' Update the details section of the table '''
        new:list = self._build_detail(system)

        for i, build in enumerate(system.get('Builds', [])):
            for j, details in enumerate(self.detail_cols.values()):
                if i >= len(new) or j >= len(new[i]): continue # Just in case

                # Set or clear the data in the cell and the highlight
                sheet[self._cell(i+srow,j)].data = ' ' if new[i][j] == ' ' else f"{new[i][j]:,}" if details.get('format', '') == 'int' else new[i][j]
                sheet[self._cell(i+srow,j)].highlight(bg=self._set_background(details.get('background'), new[i][j], details.get('max', 1)))

            # Body type details
            if system != None and 'Bodies' in system and new[i][self._detcol('Body')] != ' ':
                desc:str = ' '
                b = self.colonisation.get_body(system, new[i][self._detcol('Body')])
                if b != None:
                    desc = b.get('subType', 'Unknown')
                    if b.get('type') == 'Star': desc = re.sub(r".*\((.+)\).*", r"\1", desc)
                    if 'gas giant' in b.get('subType').lower(): desc = _('Gas giant')
                    if b.get('subType') == 'High metal content world': desc = _('HMC world') # LANG: HMC World is a high metal content world
                    desc = str_truncate(desc, 16)
                sheet[self._cell(i+srow,self._detcol('Body Type'))].data = desc


            # Handle build states
            if new[i][self._detcol('State')] == BuildState.COMPLETE:
                # Tracking
                sheet[self._cell(i+srow,self._detcol('Track'))].checkbox(state='disabled', redraw=False)
                sheet[self._cell(i+srow,0)].data = ' '
                sheet[self._cell(i+srow,self._detcol('Track'))].readonly()

            if build.get('BuildID', '') != '' and new[i][self._detcol('Name')] != ' ' and new[i][self._detcol('Name')] != '' and \
                new[i][self._detcol('Layout')] != ' ' and new[i][self._detcol('Body')] != ' ' and new[i][self._detcol('State')] == BuildState.COMPLETE: # Mark complete builds as readonly
                # Base type
                if new[i][self._detcol('Base Type')] in self.colonisation.get_base_types(): # Base type has been set so make it readonly
                    for cell in ['Base Type', 'Layout']:
                        sheet[self._cell(i+srow,self._detcol(cell))].del_dropdown()
                        sheet[self._cell(i+srow,self._detcol(cell))].readonly()

                    # Base type background color
                    bt:dict = self.colonisation.get_base_type(new[i][self._detcol('Base Type')])
                    econ = bt.get('Economy Influence') if bt.get('Economy Influence', "") != "" else bt.get('Facility Economy')
                    sheet[self._cell(i+srow,self._detcol('Base Type'))].highlight(bg=self._set_background('type', econ if econ else 'None', 1), redraw=False)

                elif new[i][self._detcol('Base Type')] != ' ' or new[i][self._detcol('Name')] != ' ': # Base type is invalid or not set & name is set
                    for cell in ['Base Type', 'Layout']:
                        sheet[self._cell(i+srow,self._detcol(cell))].highlight(bg='OrangeRed3', redraw=False)

                for cell in ['Base Type', 'Layout']:
                    sheet[self._cell(i+srow,self._detcol(cell))].align(align='left', redraw=False)

                # Base name
                if new[i][self._detcol('Name')] != ' ':
                    sheet[self._cell(i+srow,self._detcol('Name'))].readonly()
                    sheet[self._cell(i+srow,self._detcol('Name'))].align(align='left', redraw=False)

                # Body
                if new[i][self._detcol('Body')] != ' ':
                    sheet[self._cell(i+srow,self._detcol('Body'))].del_dropdown()
                    sheet[self._cell(i+srow,self._detcol('Body'))].readonly()
                continue

            #  Tracking
            if new[i][self._detcol('State')] != BuildState.COMPLETE:
                sheet[self._cell(i+srow,self._detcol('Track'))].checkbox(state='normal', redraw=False)
                sheet[self._cell(i+srow,self._detcol('Track'))].data = ' '
                sheet[self._cell(i+srow,self._detcol('Track'))].readonly(False)

            # Base type & Layout
            sheet[self._cell(i+srow,self._detcol('Base Type'))].dropdown(values=[' '] + self.colonisation.get_base_types('All' if i > 0 else 'Initial'), redraw=False)
            if new[i][self._detcol('Base Type')] != ' ':
                # Base type background color
                bt:dict = self.colonisation.get_base_type(new[i][self._detcol('Base Type')])
                econ = bt.get('Economy Influence') if bt.get('Economy Influence', "") != "" else bt.get('Facility Economy')
                sheet[self._cell(i+srow,self._detcol('Base Type'))].highlight(bg=self._set_background('type', econ if econ else 'None', 1), redraw=False)

                sheet[self._cell(i+srow,self._detcol('Layout'))].dropdown(values=[' '] + self.colonisation.get_base_layouts(new[i][self._detcol('Base Type')]), redraw=False)

                # Layout must be valid for base type
                if new[i][self._detcol('Layout')] not in self.colonisation.get_base_layouts(new[i][self._detcol('Base Type')]):
                    sheet[self._cell(i+srow,self._detcol('Layout'))].highlight(bg='OrangeRed3')

            else:
                sheet[self._cell(i+srow,self._detcol('Layout'))].dropdown(values=[' '] + self.colonisation.get_base_layouts('All' if i > 0 else 'Initial'), redraw=False)

            for cell in ['Base Type', 'Layout']:
                sheet[self._cell(i+srow,self._detcol(cell))].align(align='left', redraw=False)
                sheet[self._cell(i+srow,self._detcol(cell))].readonly(False)
                sheet[self._cell(i+srow,self._detcol(cell))].data = new[i][self._detcol(cell)]

            # Base name
            sheet[self._cell(i+srow,self._detcol('Name'))].readonly(False)
            sheet[self._cell(i+srow,self._detcol('Name'))].align(align='left', redraw=False)

            # Body
            if system != None and 'Bodies' in system:
                bodies:list = self.colonisation.get_bodies(system)
                if new[i][self._detcol('Base Type')] != ' ':
                    bt:dict = self.colonisation.get_base_type(new[i][self._detcol('Base Type')])
                    bodies = self.colonisation.get_bodies(system, bt.get('Location'))

                if len(bodies) > 0:
                    sheet[self._cell(i+srow,self._detcol('Body'))].dropdown(values=[' '] + bodies, redraw=False)
            sheet[self._cell(i+srow,self._detcol('Body'))].readonly(False)
            sheet[self._cell(i+srow,self._detcol('Body'))].data = new[i][self._detcol('Body')]

        # Clear the highlights on the empty last row
        if len(new) > len(system.get('Builds', [])):
            for j, details in enumerate(self.detail_cols.values()):
                sheet[self._cell(len(new)+srow-1,j)].highlight(bg=None, redraw=False)
            sheet[self._cell(len(new)+srow-1,self._detcol('State'))].data = ' '

        sheet.set_all_row_heights(height=int(19*self.scale), redraw=False)
        sheet.set_all_column_widths(width=None, only_set_if_too_small=True, redraw=True, recreate_selection_boxes=True)


    @catch_exceptions
    def update_display(self) -> None:
        ''' Update the display with current system data '''

        systems:list = self.colonisation.get_all_systems()
        for i, tab in enumerate(self.sheets):
            system = systems[i]
            self._update_title(i, system)
            self._update_summary(FIRST_SUMMARY_ROW, self.sheets[i], system)
            self._update_detail(FIRST_BUILD_ROW, self.sheets[i], system)
            # Not our system? Then it's readonly
            if system.get('RCSync', False) == True and self.colonisation.cmdr != None and self.colonisation.cmdr != system.get('Architect', None):
                Debug.logger.debug(f"Setting readonly due to {self.colonisation.cmdr} != {system.get('Architect', None)}")
                self.sheets[i]['B1:Z'].readonly()


    @catch_exceptions
    def _validate_edits(self, sheet:Sheet, event = None) -> str|None:
        ''' Validate edits to the sheet. This just prevents the user from deleting the primary base type. '''
        row:int = event.row - FIRST_BUILD_ROW; col:int = event.column; val = event.value
        fields:list = list(self.detail_cols.keys())
        field:str = fields[col]

        if field == 'Base Type' and val == ' ' and row == 0:
            # Don't delete the primary base or let it have no type
            return None

        # Can't do this to builds that aren't in planned state
        if field in ['Base Type', 'Layout'] and sheet.get_cell_data(event.row, self._detcol('State')) not in [' ', BuildState.PLANNED]:
            Debug.logger.debug(f"Denied: {field} [{sheet.get_cell_data(event.row, self._detcol('State'))}]")
            return None

        return event.value


    @catch_exceptions
    def sheet_modified(self, sheet:Sheet, tabnum:int, event = None) -> None:
        ''' Handle edits to the sheet. This is where we update the system data. '''

        sysnum:int = tabnum -1
        systems:list = self.colonisation.get_all_systems()
        system:dict = systems[sysnum]

        if event.eventname == 'select' and len(event.selected) == 6:
            # No editing the summary/headers
            if event.selected.row < FIRST_BUILD_ROW: return

            row:int = event.selected.row - FIRST_BUILD_ROW; col:int = event.selected.column
            fields:list = list(self.detail_cols.keys()); field:str = fields[col]

            # If the user clicks on the state column, toggle the state between planned and complete.
            # If it's in progress we'll update to that on our next delivery
            if field == 'State' and row < len(system['Builds']):
                r:int = event.selected.row

                if system['Builds'][row].get('Base Type', '') in self.colonisation.get_base_types('All'):
                    match system['Builds'][row].get('State', ''):
                        case BuildState.PLANNED: newstate = BuildState.PROGRESS
                        case BuildState.PROGRESS: newstate = BuildState.COMPLETE
                        case BuildState.COMPLETE: newstate = BuildState.PLANNED
                    self.colonisation.modify_build(system, row, {'State': newstate})

#                if system['Builds'][row]['State'] == BuildState.COMPLETE or \
#                    'Base Type' not in systems[sysnum]['Builds'][row] or \
#                    systems[sysnum]['Builds'][row]['Base Type'] == ' ':
                    #self.colonisation.modify_build(system, row, {'State': BuildState.COMPLETE})
                #else:
                #    self.colonisation.modify_build(system, row, {'State': BuildState.PLANNED})

                self.update_display()

        if system.get('RCSync', False) == True and self.colonisation.cmdr != None and self.colonisation.cmdr != system.get('Architect', None):
            Debug.logger.info(f"Not our system, ignoring edit: {system.get('Architect', None)} != {self.colonisation.cmdr}")
            return

        if event.eventname.endswith('move_rows'):
            Debug.logger.debug(f"Row move {event}")
            return

        # We only deal with edits.
        if not event.eventname.endswith('edit_table'):
            return

        # In the summary
        if event.row < FIRST_BUILD_ROW:
            field:str = list(self.summary_cols.keys())[event.column]
            if event.row == 1 and field == 'Architect':
                self.colonisation.modify_system(system, {field: event.value})
            return

        field:str = list(self.detail_cols.keys())[event.column]
        row:int = event.row - FIRST_BUILD_ROW; val = event.value

        data:dict = {}
        match field:
            case 'Base Type' | 'Layout' if val == ' ':
                # If they set the base type to empty remove the build
                if row > 0 and row < len(system['Builds']):
                    self.colonisation.remove_build(system, row)
                else:
                    self.colonisation.set_base_type(system, row, val)

                sdata:list = self.sheets[sysnum].data
                sdata.pop(row + FIRST_BUILD_ROW)
                self.sheets[sysnum].set_sheet_data(sdata, redraw=False)
                self._config_sheet(self.sheets[sysnum], system)

            case 'Base Type' | 'Layout' if val != ' ':
                self.colonisation.set_base_type(system, row, val)

                # Initial cell population
                sdata:list = []
                sdata.append(self._get_summary_header())
                sdata += self._build_summary(system)

                sdata.append(self._get_detail_header())
                sdata += self._build_detail(system)

                self.sheets[sysnum].set_sheet_data(sdata, redraw=False)
                self._config_sheet(self.sheets[sysnum], system)

            case 'Body':
                # If the body is set, update the build data
                data[field] = val
                if val == ' ':
                    data['BodyNum'] = None
                else:
                    body:dict = self.colonisation.get_body(system, val)
                    if body != None: data['BodyNum'] = body.get('bodyId', None)

            case _:
                # Any other fields, just update the build data
                data[field] = val.strip() if isinstance(val, str) else val

        # Add the data to the build
        if data != {}:
            if row >= len(system.get('Builds', [])):
                self.colonisation.add_build(system, data)
            else:
                self.colonisation.modify_build(system, row, data)

        self.update_display()


    @catch_exceptions
    def add_system_dialog(self) -> tk.Frame:
        ''' Show dialog to add a new system '''
        dialog:tk.Frame = tk.Frame(self.tabbar)
        dialog.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)

        add:tk.Frame = tk.Frame(dialog)
        add.grid(row=0, column=0, sticky=tk.W)
        # System name
        row:int = 0
        ttk.Label(add, text=_("Add Plan"), font=FONT_HEADING_2).grid(row=row, column=0, padx=10, pady=10, sticky=tk.W) # LANG: add plan
        row += 1

        ttk.Label(add, text=_("Plan Name")+":").grid(row=row, column=0, padx=10, pady=0, sticky=tk.W) # LANG: the name you want to give your plan
        plan_name_var:tk.StringVar = tk.StringVar()
        plan_name_entry:ttk.Entry = ttk.Entry(add, textvariable=plan_name_var, width=30)
        plan_name_entry.grid(row=row, column=1, padx=10, pady=0, sticky=tk.W)
        row += 1

        # Display name
        syslabel:str = _("System Name") # LANG: Label for the system's name field in the UI
        optionlabel:str = _("optional and case sensitive") # LANG: Indicates the field is optional and case-sensitive
        ttk.Label(add, text=f"{syslabel}\n({optionlabel}):").grid(row=row, column=0, padx=10, pady=10, sticky=tk.W)
        system_name_var:tk.StringVar = tk.StringVar()
        system_name_entry:ttk.Entry = ttk.Entry(add, textvariable=system_name_var, width=30)
        system_name_entry.grid(row=row, column=1, padx=10, pady=0, sticky=tk.W)
        row += 1

        prepop_var = tk.BooleanVar()
        chk = tk.Checkbutton(add, text=_("Pre-fill bases"), variable=prepop_var, onvalue=True, offvalue=False) # LANG: Label for checkbox to pre-populate bases
        chk.grid(row=row, column=1, padx=10, pady=0, sticky=tk.W)
        row += 1

        rcsync_var = tk.BooleanVar()
        chk = tk.Checkbutton(add, text=_("Sync with RavenColonial"), variable=rcsync_var, onvalue=True, offvalue=False) # LANG: Label for checkbox to sync data with RavenColonial
        chk.grid(row=row, column=1, padx=10, pady=0, sticky=tk.W)
        row += 1

        lbl = ttk.Label(add, text=_("When planning your system the first base is special, make sure that it is the first on the list.")) # LANG: Notice about the first base being special
        lbl.grid(row=row, column=0, columnspan=2, padx=10, pady=0, sticky=tk.W)
        row += 1
        lbl = ttk.Label(add, text=str(wrap(_("Pre-filling requires a system name, can have mixed results, and will likely require manual base type selection. Use with caution!"), 70))) # LANG: Notice about prepopulation being challenging
        lbl.grid(row=row, column=0, columnspan=2, padx=10, pady=0, sticky=tk.W)
        row += 1

        # Add button
        add_button:ttk.Button = ttk.Button(
            add,
            text=_("Add"), # LANG: Add/create a new system
            command=lambda: self._add_system(plan_name_var.get(), system_name_var.get(), prepop_var.get(), rcsync_var.get())
        )
        add_button.grid(row=row, column=1, padx=10, pady=10, sticky=tk.W)
        row += 1

        return dialog


    @catch_exceptions
    def update_react_dialog(self) -> None:
        if self.react is not None:
            self.react.destroy()

        self.react = tk.Frame(self.add_dialog)
        self.react.grid(row=0, column=1, sticky=tk.NW)

        row = 0
        col = 0
        ttk.Label(self.react, text=_("Reactivate Plan"), font=FONT_HEADING_2).grid(row=row, column=col, padx=10, pady=10, sticky=tk.W) # LANG: reactivate plans
        row +=1

        for ind, system in enumerate(self.colonisation.get_all_systems()):
            if system.get('Hidden', False) == True:
                lbl = ttk.Label(self.react, text=system.get("Name"))
                lbl.grid(row=row, column=col, columnspan=2, padx=10, pady=0, sticky=tk.W)
                activate_button:ttk.Button = ttk.Button(
                    self.react,
                    text=_("Reactivate"), # LANG: Reactivate system
                    command=partial(self._reactivate_system, ind)
                )
                activate_button.grid(row=row, column=col+1, padx=10, pady=0, sticky=tk.W)
                row += 1


    @catch_exceptions
    def _reactivate_system(self, sysnum:int) -> None:
            Debug.logger.debug("Reactivating system: {sysnum}")
            self.colonisation.modify_system(sysnum, {'Hidden':False})
            self.tabbar.notebookTab.tab(sysnum+1, state='normal')
            self.update_react_dialog()


    @catch_exceptions
    def _add_system(self, plan_name:str, system_name:str, prepop:int = False, rcsync:int = False) -> None:
        ''' Add the new system from the dialog '''
        if not plan_name:
            messagebox.showerror(_("Error"), _("Plan name is required")) # LANG: Error when no plan name is given
            return

        # Add the system
        system:dict = self.colonisation.add_system({'Name':plan_name, 'StarSystem':system_name}, prepop, rcsync)
        if system == False:
            messagebox.showerror(_("Error"), _("Unable to create system")) # LANG: General failure to create system error
            return

        systems:list = self.colonisation.get_all_systems()
        self._create_system_tab(len(systems), system)
        self.update_display()


    @catch_exceptions
    def edit_system_dialog(self, tabnum:int, btn:ttk.Button) -> None:
        ''' Show dialog to edit a system '''

        sysnum:int = tabnum -1
        systems:list = self.colonisation.get_all_systems()
        if sysnum > len(systems):
            Debug.logger.info(f"Invalid tab {tabnum} {sysnum}")

        system:dict = systems[sysnum]
        dialog:tk.Toplevel = tk.Toplevel(btn)
        dialog.wm_attributes('-topmost', True)     # keeps popup above everything until closed.
        dialog.wm_attributes('-toolwindow', True) # makes it a tool window

        dialog.title(_("Edit System")) # LANG: Rename a system
        dialog.minsize(500, 250)
        dialog.geometry(f"{int(500*self.scale)}x{int(250*self.scale)}+{btn.winfo_x()-100}+{self.window.winfo_y()+50}")
        #dialog.transient(self.window)
        dialog.config(bd=2, relief=tk.FLAT)
        dialog.grab_set()

        row:int = 0
        # System name
        ttk.Label(dialog, text=_("Plan Name")+":").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W) # LANG: the name you want to give your plan
        plan_name_var:tk.StringVar = tk.StringVar(value=system.get('Name', ''))
        plan_name_entry:ttk.Entry = ttk.Entry(dialog, textvariable=plan_name_var, width=30)
        plan_name_entry.grid(row=row, column=1, padx=10, pady=(10,5), sticky=tk.W)
        row += 1

        # Display name
        ttk.Label(dialog, text=_("System Name") + "\n(" + _("optional and case sensitive") + "):").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W) # LANG: Elite dangerous system name
        system_name_var:tk.StringVar = tk.StringVar(value=system.get('StarSystem', ''))
        system_name_entry:ttk.Entry = ttk.Entry(dialog, textvariable=system_name_var, width=30)
        system_name_entry.grid(row=row, column=1, padx=10, pady=(5,10), sticky=tk.W)
        row += 1

        rcsync_var = tk.BooleanVar()
        rcsync_var.set(True if system.get('RCSync', 0) != 0 else False)
        chk = tk.Checkbutton(dialog, text=_("Sync with RavenColonial"), variable=rcsync_var, onvalue=True, offvalue=False) # LANG: Label for checkbox to sync data with RavenColonial
        chk.grid(row=row, column=1, padx=10, pady=(0,0), sticky=tk.W)
        row += 1

        hide_var = tk.BooleanVar()
        hide_var.set(system.get('Hide', False))
        chk = tk.Checkbutton(dialog, text=_("Deactivate (hide) this plan"), variable=hide_var, onvalue=True, offvalue=False) # LANG: Label for checkbox to remove a plan from the tab list
        chk.grid(row=row, column=1, padx=10, pady=(0,10), sticky=tk.W)
        row += 1

        # Buttons
        button_frame:ttk.Frame = ttk.Frame(dialog)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)
        row += 1

        # Save button
        save_button:ttk.Button = ttk.Button(
            button_frame,
            text=_("Save"), # LANG: Save button
            command=lambda: self._edit_system(tabnum, plan_name_var.get(), system_name_var.get(), rcsync_var.get(), hide_var.get(), dialog)
        ) # LANG: Rename button
        save_button.pack(side=tk.LEFT, padx=5)

        # Cancel button
        cancel_button:ttk.Button = ttk.Button(
            button_frame,
            text=_("Cancel"), # LANG: Cancel button
            command=dialog.destroy
        ) # LANG: Cancel button
        cancel_button.pack(side=tk.LEFT, padx=5)

        # Focus on display name entry
        system_name_entry.focus_set()


    @catch_exceptions
    def _edit_system(self, tabnum:int, name:str, sysname:str, rcsync:bool, hide:bool, dialog:tk.Toplevel) -> None:
        ''' Edit a system's plan, name and sync state '''
        sysnum:int = tabnum -1

        if not name:
            messagebox.showerror(_("Error"), _("Plan name is required"))
            return

        data:dict = {
            'Name': name,
            'StarSystem': sysname,
            'RCSync': rcsync,
            'Hidden' : hide
        }
        if hide == True:
            self.tabbar.hide(tabnum)

        self.colonisation.modify_system(sysnum, data)
        self.tabbar.notebookTab.tab(tabnum, text=name)
        self.update_react_dialog()

        dialog.destroy()
        self.update_display()


    @catch_exceptions
    def delete_system(self, tabnum:int, tab: ttk.Frame) -> None:
        ''' Remove the current system '''
        sysnum:int = tabnum -1
        # Confirm removal
        if not messagebox.askyesno(
            _("Confirm Removal"),
            _("Are you sure you want to remove this system?")
        ): # LANG: request system removal confirmation
            return

        if sysnum > len(self.colonisation.get_all_systems()):
            Debug.logger.info(f"Invalid tab {tabnum} {sysnum}")

        Debug.logger.info(f"Deleting system {tabnum}")
        tabs:list = self.tabbar.tabs()
        self.tabbar.forget(tabs[tabnum])
        del self.sheets[sysnum]
        del self.plan_titles[sysnum]
        self.colonisation.remove_system(sysnum)

        self.update_display()


    @catch_exceptions
    def _rc_refresh_system(self, tabnum:int) -> None:
        ''' Reload the current system from RavenColonial '''
        sysnum:int = tabnum -1
        systems:list = self.colonisation.get_all_systems()
        if sysnum > len(systems):
            Debug.logger.info(f"Invalid tab {tabnum} {sysnum}")

        system:dict = systems[sysnum]
        if system.get('RCSync', 0) == 0:
            return

        # Refresh the RC data when the window is opened/created
        Debug.logger.debug(f"Reloading system {system.get('StarSystem', 'Unknown')} from {system.get('SystemAddress')}")
        RavenColonial(self.colonisation).load_system(system.get('SystemAddress', ''), system.get('Rev', ''))

        if self.bgstally.fleet_carrier.available() == True:
            RavenColonial(self.colonisation).update_carrier(self.bgstally.fleet_carrier.carrier_id, self.colonisation.carrier_cargo)

        # @TODO: Create a proper project sync process.
        #for b in system['Builds']:
        #    if b.get('State') == BuildState.PROGRESS and b.get('BuildID', None) != None:
        #        self.rc.load_project()
        self.update_display()


    @catch_exceptions
    def close(self) -> None:
        ''' Close the window and any popups and clean up'''
        if self.window: self.window.destroy()
        if self.legend_fr: self.legend_fr.destroy()
        if self.notes_fr: self.notes_fr.destroy()
        if self.bases_fr: self.bases_fr.destroy()
        if self.bodies_fr: self.bodies_fr.destroy()

        # UI components
        self.tabbar:ScrollableNotebook
        self.sheets:list = []
        self.plan_titles:list = []
        self.colonisation.save("Colonisation window close")


    @catch_exceptions
    def _calc_points(self, type:str, builds:list, row:int) -> int:
        ''' Calculate the T2 or T3 base point cost/reward. It depends on the type of base and what's planned/built so far '''
        bt:dict = self.colonisation.get_base_type(builds[row].get('Base Type', ''))
        reward:int = bt.get(type+' Reward', 0)
        cost:int = bt.get(type + ' Cost', 0)

        # If it's the first base or there is no cost skip the complicated cost calculation
        if row == 0: return reward
        if cost == 0: return reward - cost

        # Do the increasing point costs for ports
        if bt.get('Type') in self.colonisation.get_base_types('Ports'):
            # sp is the number of ports built (after the initial starport/outpost) minus one
            sp:int = max(len([b for b in builds[1:row] if b.get('Base Type') in self.colonisation.get_base_types('Ports')])-1, 0)
            # T2 ports cost the base cost plus 2 * sp, T3 ports cost the base cost + 2 * cost
            cost += (2 * sp) if type == 'T2' else (cost * sp)

        return reward - cost


    @catch_exceptions
    def _set_weight(self, item, wght:str = 'bold') -> None:
        ''' Set font weight '''
        fnt = tkFont.Font(font=item['font']).actual()
        item.configure(font=(fnt['family'], fnt['size'], wght))


    @catch_exceptions
    def is_build_complete(self, build:list[dict]) -> bool:
        ''' Check if a build is complete '''
        return (self.colonisation.get_build_state(build) == BuildState.COMPLETE)


    @catch_exceptions
    def is_build_started(self, build:list[dict]) -> bool:
        ''' Check if a build is in progress '''
        return (self.colonisation.get_build_state(build) == BuildState.PROGRESS)


    @catch_exceptions
    def _load_legend(self) -> str:
        ''' Load the legend text from the language appropriate file '''
        filepath: str | None = get_localised_filepath(FILENAME_LEGEND, path.join(self.bgstally.plugin_dir, FOLDER_DATA))

        if filepath:
            try:
                with open(filepath, encoding='utf-8') as stream:
                    return stream.read()
            except Exception as e:
                Debug.logger.warning(f"Unable to load legend {filepath}")
                Debug.logger.error(traceback.format_exc())
        return ""


    @catch_exceptions
    def _set_background(self, type: str|None, value: str, limit:int = 1) -> str|None:
        ''' Return the appropriate background '''
        match type:
            case False|None:
                return None
            case 'gyr' | 'rwg':
                return None if value == ' ' else self._get_color(int(value), int(limit), type)
            case 'type':
                return self.colors.get(str(value), None)
            case _:
                return type


    @catch_exceptions
    def _get_color(self, value:int, limit:int = 1, color:str = 'rwg') -> str:
        ''' Get a color based on the value and its range. '''
        if not isinstance(value, int) and not value.isdigit():
            return "#7A007A"

        # Scale it to a sensible range
        if limit > 25:
            value = int(value * 25 / limit)
            limit = 25
        value = min(value, limit)

        # Red, White, Green or Green, Yellow, Red
        if color == 'rwg':
            gradient:list = self._create_gradient(limit, 'rwg')
            value = min(max(int(value), -limit), limit)
            return gradient[int(value + limit)]

        # keep it within the limits
        gradient:list = self._create_gradient(limit, 'gyr')
        if value < len(gradient):
            return gradient[int(value)]

        return "#7A007A"


    @catch_exceptions
    def _create_gradient(self, steps:int, type:str = 'rwg') -> list[str]:
        ''' Generates a list of RGB color tuples representing a gradient. '''
        # Green, Yellow, Red (0:steps)
        s:tuple = (150, 200, 150) # start
        m:tuple = (230, 230, 125) # middle
        e:tuple = (190, 30, 100) # end

        # Red, White, Green (-steps:steps)
        if type == 'rwg':
            steps *= 2
            # Define RGB values
            s = (200, 125, 100)
            m = (255, 255, 255)
            e = (75, 175, 75)

        # Define gradient parameters
        gradient_colors:list = []

        # Calculate interpolation steps
        r_step_1:int = round((m[0] - s[0]) / steps)
        g_step_1:int = round((m[1] - s[1]) / steps)
        b_step_1:int = round((m[2] - s[2]) / steps)

        r_step_2:int = round((e[0] - m[0]) / steps)
        g_step_2:int = round((e[1] - m[1]) / steps)
        b_step_2:int = round((e[2] - m[2]) / steps)

        # Iterate and interpolate
        for i in range(steps+1):
            # Between start and middle
            cr:int = min(max(s[0] + r_step_1 * i, 0), 255)
            cg:int = min(max(s[1] + g_step_1 * i, 0), 255)
            cb:int = min(max(s[2] + b_step_1 * i, 0), 255)

            if i >= steps/2: # Interpolate between middle and end
                cr = min(max(m[0] + r_step_2 * (i - steps/2), 0), 255)
                cg = min(max(m[1] + g_step_2 * (i - steps/2), 0), 255)
                cb = min(max(m[2] + b_step_2 * (i - steps/2), 0), 255)

            # Add the interpolated color to the gradient
            gradient_colors.append(f"#{int(cr):02x}{int(cg):02x}{int(cb):02x}")

        return gradient_colors


    @catch_exceptions
    def _detcol(self, col:str) -> int:
        ''' Macro to shorten references to detail columns '''
        return list(self.detail_cols.keys()).index(col)


    @catch_exceptions
    def _cell(self, row:int, col:int) -> str:
        ''' Macro to shorten cell references '''
        return f"{num2alpha(col)}{row+1}"