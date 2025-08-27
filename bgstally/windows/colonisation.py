from os import path
from math import ceil
import traceback
import re
from functools import partial
import webbrowser
from config import config
import plug
import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk, messagebox, PhotoImage
from urllib.parse import quote
from thirdparty.ScrollableNotebook import ScrollableNotebook
from thirdparty.tksheet import Sheet
from thirdparty.Tooltip import ToolTip
from bgstally.constants import FONT_HEADING_1, COLOUR_HEADING_1, FONT_HEADING_2, FONT_SMALL, FONT_TEXT, FOLDER_DATA, FOLDER_ASSETS, BuildState
from bgstally.debug import Debug
from bgstally.utils import _, human_format, str_truncate
from bgstally.ravencolonial import RavenColonial

FILENAME = "colonisation_legend.txt" # LANG: Not sure how we handle file localistion.
SUMMARY_HEADER_ROW = 0
FIRST_SUMMARY_ROW = 1
FIRST_SUMMARY_COLUMN = 4
HEADER_ROW = 3
FIRST_BUILD_ROW = 4

class ColonisationWindow:
    '''
    Window for managing colonisation plans.

    This window allows users to view and manage colonisation plans for different systems. It creates a tab for each system,
    and uses a sheet to display both summary and detailed information about the builds in that system.

    It can create popup windows for showing base types, system notes, and system bodies.
    '''
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.colonisation = None
        self.image_tab_complete:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_enabled.png"))
        self.image_tab_progress:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_part_enabled.png"))
        self.image_tab_planned:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_disabled.png"))

        self.summary_rows:dict = {
            'Complete': _("Complete"), # LANG: Row heading of build totals i.e. ones that are done
            'Planned': _("Planned") # LANG: Row heading of planned build totals i.e. ones that aren't complete
        }

        # Table has two sections: summary and builds. This dict defines attributes for each summary column
        self.summary_cols:dict = {
            'Track': {'header': "", 'background': None, 'hide': True, 'format': 'hidden'},
            'Architect': {'header': _("Architect"), 'background': None, 'hide': False},
            'Layout': {'header': "", 'background': None, 'hide': True, 'format': 'hidden'},
            'State': {'header': "", 'background': None},
            'Total': {'header': _("Total"), 'background': None, 'format': 'int'}, # LANG: Total number of builds
            'Orbital': {'header': _("Orbital"), 'background': None, 'format': 'int'}, # LANG: Number of orbital/space builds
            'Surface': {'header': _("Surface"), 'background': None, 'format': 'int'}, # LANG: Number of ground/surface builds
            'T2': {'header': _("T2"), 'background': 'rwg', 'format': 'int', 'max': 1}, # LANG: Tier 2 points
            'T3': {'header': _("T3"), 'background': 'rwg', 'format': 'int', 'max': 1}, # LANG: Tier 3 points
            'Cost': {'header': _("Cost"), 'background': 'gyr', 'format': 'int', 'max': 200000}, # LANG: Cost in tonnes of cargo
            'Trips': {'header': _("Loads"), 'background': 'gyr', 'format': 'int', 'max': 260}, # LANG: Number of loads of cargo
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
            'Layouts' : {'header': _("Building Layouts"), 'background': None, 'format': 'string', 'width': 200}, # LANG: Building layout types
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
            'Planned' : '#ffe5a0', 'Progress' : '#f5b60d', 'Complete' : '#d4edbc' #'#5a3286',
        }

        # UI components
        self.window:tk.Toplevel = None
        self.tabbar:ScrollableNotebook = None
        self.add_dialog:tk.Frame = None
        self.react:Tk.Frame = None
        self.sheets:list = []
        self.plan_titles:list = []
        self.legend_fr:tk.Toplevel = None
        self.notes_fr:tk.Toplevel = None
        self.bases_fr:tk.Toplevel = None
        self.bodies_fr:tk.Toplevel = None
        self.scale:float = 0


    def show(self) -> None:
        ''' Create and display the colonisation window. Called by ui.py when the colonisation icon is clicked. '''
        try:
            if self.window != None and self.window.winfo_exists():
                self.window.lift()
                return

            # We do this once because it seems to get lost over time
            if self.scale == 0:
                self.scale = self.bgstally.ui.frame.tk.call('tk', 'scaling') - 0.6

            self.colonisation = self.bgstally.colonisation
            self.window:tk.Toplevel = tk.Toplevel(self.bgstally.ui.frame)
            self.window.title(_("{plugin_name} - Colonisation").format(plugin_name=self.bgstally.plugin_name)) # LANG: window title

            self.window.minsize(400, 100)
            self.window.geometry(f"{int(1500*self.scale)}x{int(500*self.scale)}")
            self.window.protocol("WM_DELETE_WINDOW", self.close)
            self._create_frames()   # Create main frames
            self.update_display()   # Populate them

        except Exception as e:
            Debug.logger.error(f"Error in colonisation.show(): {e}")
            Debug.logger.error(traceback.format_exc())


    def _create_frames(self) -> None:
        ''' Create the system frame notebook and tabs for each system '''
        try:
            # Create system tabs notebook
            self.tabbar = ScrollableNotebook(self.window, wheelscroll=True, tabmenu=True)
            self.tabbar.pack(fill=tk.BOTH, side=tk.TOP, expand=True, padx=5, pady=5)
            self.add_dialog:tk.Frame = self.add_system_dialog()
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

            if tabnum > 0: self.tabbar.select(1) # Select the first system tab

        except Exception as e:
            Debug.logger.error(f"Error in create_frames(): {e}")
            Debug.logger.error(traceback.format_exc())


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

    def _set_system_progress(self, tabnum:int, system:dict) -> None:
        ''' Update the tab image based on the system's progress '''
        state:BuildState = BuildState.COMPLETE
        for b in system['Builds']:
            build_state = self.colonisation.get_build_state(b)
            if build_state == BuildState.PLANNED and state != BuildState.PROGRESS:
                state = BuildState.PLANNED
            if build_state == BuildState.PROGRESS:
                state = BuildState.PROGRESS

        match state:
            case BuildState.COMPLETE:
                self.tabbar.notebookTab.tab(tabnum, image=self.image_tab_complete)
            case BuildState.PROGRESS:
                self.tabbar.notebookTab.tab(tabnum, image=self.image_tab_progress)
            case BuildState.PLANNED:
                self.tabbar.notebookTab.tab(tabnum, image=self.image_tab_planned)


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
        if systems[sysnum].get('RCSync', 0) == 1:
            name_label = ttk.Label(title_frame, text="", font=FONT_HEADING_1, foreground="#0078d4", cursor="hand2")
            name_label.bind("<Button-1>", partial(self.system_click, tabnum, 'RavenColonial'))
            ToolTip(name_label, text=_("Link to RavenColonial")) # LANG: tooltip for ravencolonial link
        name_label.pack(side=tk.LEFT, padx=10, pady=5)
        self.plan_titles[sysnum]['Name'] = name_label

        sysname:str = systems[sysnum].get('StarSystem', '') + ' ⤴' if systems[sysnum].get('StarSystem') != '' else ''
        sys_label:ttk.Label = ttk.Label(title_frame, text=sysname, cursor="hand2")
        sys_label.pack(side=tk.LEFT, padx=5, pady=5)
        self._set_weight(sys_label)
        sys_label.bind("<Button-1>", partial(self.system_click, tabnum, 'inara'))
        ToolTip(sys_label, text=_("Link to Inara")) # LANG: tooltip for inara link
        self.plan_titles[sysnum]['System'] = sys_label

        sys_copy:ttk.Label = ttk.Label(title_frame, text='⮺   ', cursor='hand2')
        sys_copy.pack(side=tk.LEFT, padx=(0,10), pady=5)
        self._set_weight(sys_copy)
        sys_copy.bind("<Button-1>", partial(self.ctc, tabnum))
        ToolTip(sys_copy, text=_("Copy system name to clipboard")) # LANG: tooltip for the copy to clipboard icon

        if systems[sysnum].get('Bodies', None) != None and len(systems[sysnum]['Bodies']) > 0:
            bodies:str = str(len(systems[sysnum]['Bodies'])) + " " + _("Bodies") # LANG: bodies in the system
            sys_bodies:ttk.Label = ttk.Label(title_frame, text=bodies, cursor="hand2")
            sys_bodies.pack(side=tk.LEFT, padx=10, pady=5)
            ToolTip(sys_bodies, text=_("Show system bodies window")) # LANG: tooltip for the show bodies window
            self._set_weight(sys_bodies)
            sys_bodies.bind("<Button-1>", partial(self.bodies_popup, tabnum))

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

        btn:ttk.Button = ttk.Button(title_frame, text=_("📝"), width=3, cursor="hand2", command=lambda: self.edit_system_dialog(tabnum, tab)) # LANG: Rename button
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

        if systems[sysnum].get('RCSync', 0) == 1:
            #🔄 ⟳
            btn:ttk.Button = ttk.Button(title_frame, text=_("🔄"), cursor="hand2", width=3, command=partial(self._rc_refresh_system, tabnum))
            btn.pack(side=tk.RIGHT, padx=5, pady=5)
            ToolTip(btn, text=_("Refresh from RavenColonial")) # LANG: tooltip for ravencolonial refresh button


    def ctc(self, tabnum:int, event = None) -> None:
        ''' Copy to clipboard '''
        try:
            systems:list = self.colonisation.get_all_systems()
            self.window.clipboard_clear()
            self.window.clipboard_append(systems[tabnum-1].get('StarSystem', ''))
        except Exception as e:
            Debug.logger.error(f"Error in ctc() {e}")
            Debug.logger.error(traceback.format_exc())


    def system_click(self, tabnum:int, type:str = '', event = None) -> None:
        ''' Execute the click event for the system link '''
        try:
            sysnum:int = tabnum -1
            systems:list = self.colonisation.get_all_systems()
            if sysnum > len(systems):
                Debug.logger.info(f"on_system_click invalid tab: {tabnum}")
                return
            star:str = systems[sysnum]['StarSystem']

            # Can't use this because the stupid function overrides the passed in system name in favor of the local one. FFS
            #opener = plug.invoke(config.get_str('system_provider'), 'EDSM', 'system_url', star)
            #if opener:
            #    Debug.logger.debug(f"{opener}")
            #    return webbrowser.open(opener)
            #else:

            if type == 'RavenColonial':
                webbrowser.open(f"https://ravencolonial.com/#sys={quote(star)}")
                return

            match config.get_str('system_provider'):
                case 'Inara':
                    webbrowser.open(f"https://inara.cz/elite/starsystem/search/?search={star}")
                case 'spansh':
                    webbrowser.open(f"https://www.spansh.co.uk/search/{star}")
                case _:
                    webbrowser.open(f"https://www.edsm.net/en/system?systemName={star}")

        except Exception as e:
            Debug.logger.error(f"Error in system_click() {e}")
            Debug.logger.error(traceback.format_exc())


    def bases_popup(self) -> None:
        ''' Show a popup with details of all the base types '''
        try:
            if self.bases_fr != None and self.bases_fr.winfo_exists():
                self.bases_fr.lift()
                return

            self.bases_fr = tk.Toplevel(self.bgstally.ui.frame)
            self.bases_fr.wm_title(_("{plugin_name} - Colonisation Base Types").format(plugin_name=self.bgstally.plugin_name)) # LANG: Title of the base type popup window
            self.bases_fr.geometry(f"{int(1000*self.scale)}x{int(500*self.scale)}")
            self.bases_fr.protocol("WM_DELETE_WINDOW", self.bases_fr.destroy)
            self.bases_fr.config(bd=2, relief=tk.FLAT)
            sheet:Sheet = Sheet(self.bases_fr, show_row_index=False, cell_auto_resize_enabled=True, height=4096,
                            show_horizontal_grid=True, show_vertical_grid=True, show_top_left=False,
                            align="center", show_selected_cells_border=True, table_selected_cells_border_fg=None,
                            show_dropdown_borders=False, header_bg='lightgrey', header_selected_cells_bg='lightgrey',
                            empty_vertical=0, empty_horizontal=0, header_font=FONT_SMALL, font=FONT_SMALL, arrow_key_down_right_scroll_page=True,
                            show_header=True)
            sheet.pack(fill=tk.BOTH, padx=0, pady=0)
            sheet.enable_bindings('single_select')
            sheet.extra_bindings('cell_select', func=partial(self.base_clicked, sheet))
            data:list = [[0 for _ in range(len(self.bases.keys()))] for _ in range(len(self.colonisation.get_base_types()))]
            sheet.set_header_data([h['header'] for h in self.bases.values()])
            sheet.set_sheet_data(data)
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
                            sheet[i,j].data = ' ' if v == 0 else f"{v:,}"
                            sheet[i,j].highlight(bg=self._set_background(col.get('background'), v, col.get('max')))
                        case _:
                            sheet[i,j].data = bt.get(name) if bt.get(name, ' ') != ' ' else bt.get(name, ' ')
                            if name == 'Type': # Special case.
                                econ = bt.get('Economy Influence') if bt.get('Economy Influence') != "" else bt.get('Facility Economy')
                                sheet[i,j].highlight(bg=self._set_background(col.get('background'), econ if econ else 'None'))
                            else:
                                sheet[i,j].highlight(bg=self._set_background(col.get('background'), bt.get(name, ' ')))
            sheet.set_all_column_widths(width=None, only_set_if_too_small=True, redraw=True, recreate_selection_boxes=True)

        except Exception as e:
            Debug.logger.error(f"Error in bases_popup(): {e}")
            Debug.logger.error(traceback.format_exc())


    def base_clicked(self, sheet:Sheet, event = None) -> None:
        try:
            sheet.toggle_select_cell(event['selected'].row, event['selected'].column, False)
            sheet.toggle_select_row(event['selected'].row, False, True)
            Debug.logger.debug(f"Clicked: {sheet[event['selected'].row, 20].data}")
            #layout = sheet[event['selected'].row, 20].data.split(', ')[0]
            #webbrowser.open(f"https://ravencolonial.com/#vis={layout.strip().lower().replace(' ', '_')}")
        except Exception as e:
            Debug.logger.error(f"Error in base_clicked(): {e}")
            Debug.logger.error(traceback.format_exc())



    def bodies_popup(self, tabnum:int, event = None) -> None:
        ''' Show a popup with details of all the bodies in the system '''
        try:
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

        except Exception as e:
            Debug.logger.error(f"Error in bodies_popup(): {e}")
            Debug.logger.error(traceback.format_exc())


    def _create_table_frame(self, tabnum:int, tab:ttk.Frame, system:dict) -> None:
        ''' Create a unified table frame with both summary and builds in a single scrollable area '''
        # Main table frame
        table_frame:ttk.Frame = ttk.Frame(tab)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Configure the table frame to resize with the window
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        sheet:Sheet = Sheet(table_frame, show_row_index=False, cell_auto_resize_enabled=True, height=4096,
                            show_horizontal_grid=True, show_vertical_grid=False, show_top_left=False,
                            align="center", show_selected_cells_border=True, table_selected_cells_border_fg=None,
                            show_dropdown_borders=False,
                            empty_vertical=15, empty_horizontal=0, font=FONT_SMALL, arrow_key_down_right_scroll_page=True,
                            show_header=False, set_all_heights_and_widths=True) #, default_row_height=21)
        sheet.pack(fill=tk.BOTH, padx=0, pady=(0, 5))

        # Initial cell population
        data:list = []
        data.append(self._get_summary_header())
        data += self._build_summary(system)

        data.append(self._get_detail_header())
        data += self._build_detail(system)

        sheet.set_sheet_data(data)
        self._config_sheet(sheet, system)
        sheet.enable_bindings('single_select', 'edit_cell', 'up', 'down', 'left', 'right', 'copy', 'paste')
        sheet.edit_validation(self.validate_edits)
        sheet.extra_bindings('all_modified_events', func=partial(self.sheet_modified, sheet, tabnum))
        sheet.extra_bindings('cell_select', func=partial(self.sheet_modified, sheet, tabnum))

        if len(self.sheets) < tabnum:
            self.sheets.append(sheet)
        else:
            self.sheets[tabnum-1] = sheet


    def _update_title(self, index:int, system:dict) -> None:
        ''' Update title with both display name and actual system name '''
        name:str = system.get('Name','') if system.get('Name',None) != None else system.get('StarSystem', _('Unknown')) # LANG: Default when we don't know the name
        sysname:str = system.get('StarSystem', '') + ' ⤴' if system.get('StarSystem') != '' else ''

        self.plan_titles[index]['Name']['text'] = name
        self.plan_titles[index]['System']['text'] = sysname

        # Hide the system name if it hasn't been set
        if sysname == None:
            self.plan_titles[index]['System'].pack_forget()


    def _config_sheet(self, sheet:Sheet, system:dict = None) -> None:
        ''' Initial sheet configuration. '''
        sheet.dehighlight_all()

        # Column widths
        for i, (name, value) in enumerate(self.detail_cols.items()):
            sheet.column_width(i, value.get('width', 100))

        # header lines
        sheet[SUMMARY_HEADER_ROW].highlight(bg='lightgrey')
        sheet['A2:G2'].highlight(bg=self._set_background('type', 'Complete', 1))
        sheet['A3:G3'].highlight(bg=self._set_background('type', 'Planned', 1))
        sheet[HEADER_ROW].highlight(bg='lightgrey')
        # Tracking checkboxes
        sheet['A5:A'].checkbox(state='normal', checked=False)

        # Base types
        sheet['B5'].dropdown(values=[' '] + self.colonisation.get_base_types('Initial'))
        sheet['B6:B'].dropdown(values=[' '] + self.colonisation.get_base_types('All'))

        # Base layouts dropdown
        sheet['C5'].dropdown(values=[' '] + self.colonisation.get_base_layouts('Initial'))
        sheet['C6:C'].dropdown(values=[' '] + self.colonisation.get_base_layouts('All'))

        if system != None and 'Bodies' in system:
            bodies:list = self.colonisation.get_bodies(system)
            if len(bodies) > 0:
                sheet['E5:E'].dropdown(values=[' '] + bodies)

        # Make the sections readonly that users can't edit.
        sheet.span('A1:4', type_='readonly') # Headers and summary
        sheet['B2'].readonly(False) # Except Architect

        sheet.span('F4:T', type_='readonly') # Build columns from Body onwards
        # track, types, layouts, and names left.
        sheet[f"A{FIRST_BUILD_ROW}:D"].align(align='left')


    def _get_summary_header(self) -> list[str]:
        ''' Return the header row for the summary '''
        cols:list = []
        for c, v in self.summary_cols.items():
            cols.append(v.get('header', c) if v.get('hide') != True else ' ')
        return cols


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
                        totals['Planned'][name] = ' '
                        totals['Complete'][name] = system.get('Architect', _('Unknown'))
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


    def _update_summary(self, srow:int, sheet:Sheet, system:dict) -> None:
        ''' Update the summary section with current system data '''
        scol:int = 0
        new:list = self._build_summary(system)

        for i, x in enumerate(self.summary_rows.keys()):
            for j, details in enumerate(self.summary_cols.values()):
                #j += FIRST_SUMMARY_COLUMN
                sheet[i+srow,j].data = ' ' if new[i][j] == 0 else f"{new[i][j]:,}" if details.get('format') == 'int' else new[i][j]
                if details.get('background') != None:
                    sheet[i+srow,j+scol].highlight(bg=self._set_background(details.get('background'), new[i][j], details.get('max', 1)))


    def _get_detail_header(self) -> list[str]:
        ''' Return the details header row '''
        cols:list = []
        for c, v in self.detail_cols.items():
            cols.append(v.get('header', c) if v.get('hide') != True else ' ')
        return cols


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
                        if name == 'State':
                            # @TODO: Make this a progress bar
                            if self.colonisation.get_build_state(build) == BuildState.PROGRESS and i < len(reqs):
                                req = sum(reqs[i].values())
                                deliv = sum(delivs[i].values())
                                row.append(f"{int(deliv * 100 / req)}%" if req > 0 else 0)
                            elif self.colonisation.get_build_state(build) == BuildState.COMPLETE:
                                row.append('Complete')
                            elif build.get('Base Type', '') != '':
                                row.append('Planned')
                            continue

                        if name == 'Body' and build.get('Body', None) != None and system.get('StarSystem', '') != '':
                            row.append(build.get('Body').replace(system.get('StarSystem','') + ' ', ''))
                            continue

                        row.append(build.get(name) if build.get(name, ' ') != ' ' else bt.get(name, ' '))

            details.append(row)

        # Is the last line an uncategorized base? If not add another
        if len(details) == 0 or details[-1][1] != ' ':
            row:list = [' '] * (len(list(self.detail_cols.keys())) -1)
            details.append(row)

        return details


    def _update_detail(self, srow:int, sheet:Sheet, system:dict) -> None:
        ''' Update the details section of the table '''
        new:list = self._build_detail(system)

        for i, build in enumerate(system.get('Builds', [])):
            for j, details in enumerate(self.detail_cols.values()):
                if i >= len(new) or j >= len(new[i]): continue # Just in case

                # Set or clear the data in the cell and the highlight
                sheet[i+srow,j].data = ' ' if new[i][j] == ' ' else f"{new[i][j]:,}" if details.get('format') == 'int' else new[i][j]
                sheet[i+srow,j].highlight(bg=self._set_background(details.get('background'), new[i][j], details.get('max', 1)))

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
                sheet[i+srow,self._detcol('Body Type')].data = desc

            # Handle build states
            if new[i][self._detcol('State')] == BuildState.COMPLETE:
                # Tracking
                sheet[i+srow,self._detcol('Track')].checkbox(state='disabled'); sheet[i+srow,0].data = ' '
                sheet[i+srow,self._detcol('Track')].readonly()

            if build.get('BuildID', '') != '' and new[i][self._detcol('Name')] != ' ' and new[i][self._detcol('Layout')] != ' ' and new[i][self._detcol('Name')] != '' and new[i][self._detcol('State')] == BuildState.COMPLETE: # Mark complete builds as readonly
                # Base type
                if new[i][self._detcol('Base Type')] in self.colonisation.get_base_types(): # Base type has been set so make it readonly
                    sheet[i+srow,self._detcol('Base Type')].del_dropdown()
                    sheet[i+srow,self._detcol('Base Type')].readonly()
                    sheet[i+srow,self._detcol('Base Type')].highlight(bg=None)
                elif new[i][self._detcol('Base Type')] != ' ' or new[i][self._detcol('Name')] != ' ': # Base type is invalid or not set & name is set
                    sheet[i+srow,self._detcol('Base Type')].highlight(bg='red2')
                    sheet[i+srow,self._detcol('Layout')].highlight(bg='red2')
                sheet[i+srow,self._detcol('Base Type')].align(align='left')
                sheet[i+srow,self._detcol('Layout')].align(align='left')

                # Base name
                sheet[i+srow,self._detcol('Name')].readonly()
                sheet[i+srow,self._detcol('Name')].align(align='left')

                # Body
                sheet[i+srow,self._detcol('Body')].del_dropdown()
                sheet[i+srow,self._detcol('Body')].readonly()
                continue

            #  Tracking
            if new[i][self._detcol('State')] != BuildState.COMPLETE:
                sheet[i+srow,self._detcol('Track')].checkbox(state='normal')
                sheet[i+srow,self._detcol('Track')].data = ' '
                sheet[i+srow,self._detcol('Track')].readonly(False)

            # Base type
            sheet[i+srow,self._detcol('Base Type')].dropdown(values=[' '] + self.colonisation.get_base_types('All' if i > 0 else 'Initial'))
            sheet[i+srow,self._detcol('Base Type')].align(align='left')
            sheet[i+srow,self._detcol('Base Type')].readonly(False)
            sheet[i+srow,self._detcol('Base Type')].data = new[i][self._detcol('Base Type')]

            # Base Layout
            cat:str = new[i][self._detcol('Base Type')] if new[i][self._detcol('Base Type')] != ' ' else 'All'
            if i == 0 and cat == 'All': cat = 'Initial'
            layouts:list = self.colonisation.get_base_layouts(cat)
            sheet[i+srow,self._detcol('Layout')].dropdown(values=[' '] + layouts)
            sheet[i+srow,self._detcol('Layout')].align(align='left')
            sheet[i+srow,self._detcol('Layout')].readonly(False)
            sheet[i+srow,self._detcol('Layout')].data = new[i][self._detcol('Layout')]

            # Base name
            sheet[i+srow,self._detcol('Name')].readonly(False)
            sheet[i+srow,self._detcol('Name')].align(align='left')

            # Body
            if system != None and 'Bodies' in system:
                bodies:dict = self.colonisation.get_bodies(system)
                if new[i][self._detcol('Base Type')] != ' ':
                    basetype:dict = self.colonisation.get_base_type(new[i][self._detcol('Base Type')])
                    bodies = self.colonisation.get_bodies(system, basetype.get('Location'))

                if len(bodies) > 0:
                    sheet[i+srow,self._detcol('Body')].dropdown(values=[' '] + bodies)
            sheet[i+srow,self._detcol('Body')].readonly(False)
            sheet[i+srow,self._detcol('Body')].data = new[i][self._detcol('Body')]

        # Clear the highlights on the empty last row
        if len(new) > len(system.get('Builds', [])):
            for j, details in enumerate(self.detail_cols.values()):
                sheet[len(new)+srow-1,j].highlight(bg=None)
            sheet[len(new)+srow-1,self._detcol('State')].data = ' '

        sheet.set_all_column_widths(width=None, only_set_if_too_small=True, redraw=True, recreate_selection_boxes=True)


    def update_display(self) -> None:
        ''' Update the display with current system data '''
        try:
            systems:list = self.colonisation.get_all_systems()
            for i, tab in enumerate(self.sheets):
                system = systems[i]
                self._update_title(i, system)
                self._update_summary(FIRST_SUMMARY_ROW, self.sheets[i], system)
                self._update_detail(FIRST_BUILD_ROW, self.sheets[i], system)
        except Exception as e:
            Debug.logger.error(f"Error in update_display(): {e}")
            Debug.logger.error(traceback.format_exc())


    def validate_edits(self, event = None) -> str|None:
        ''' Validate edits to the sheet. This just prevents the user from deleting the primary base type. '''
        try:
            row:int = event.row - FIRST_BUILD_ROW; col:int = event.column; val = event.value
            fields:list = list(self.detail_cols.keys())
            field:str = fields[col]

            if field == 'Base Type' and val == ' ' and row == 0:
                # Don't delete the primary base or let it have no type
                return None

            return event.value

        except Exception as e:
            Debug.logger.error(f"Error in validate_edits(): {e}")
            Debug.logger.error(traceback.format_exc())


    def sheet_modified(self, sheet:Sheet, tabnum:int, event = None) -> None:
        ''' Handle edits to the sheet. This is where we update the system data. '''
        try:
            sysnum:int = tabnum -1
            systems:list = self.colonisation.get_all_systems()

            if event.eventname == 'select' and len(event.selected) == 6:
                # No editing the summary/headers
                if event.selected.row < FIRST_BUILD_ROW: return

                row:int = event.selected.row - FIRST_BUILD_ROW; col:int = event.selected.column
                fields:list = list(self.detail_cols.keys()); field:str = fields[col]

                # If the user clicks on the state column, toggle the state between planned and complete.
                # If it's in progress we'll update to that on our next delivery
                if field == 'State' and row < len(systems[sysnum]['Builds']):
                    if systems[sysnum]['Builds'][row]['State'] == BuildState.COMPLETE or \
                        'Base Type' not in systems[sysnum]['Builds'][row] or \
                        systems[sysnum]['Builds'][row]['Base Type'] == ' ':
                        self.colonisation.modify_build(systems[sysnum], row, {'State': BuildState.PLANNED})
                    else:
                        self.colonisation.modify_build(systems[sysnum], row, {'State': BuildState.COMPLETE})

                    self.update_display()
                return

            # We only deal with edits.
            if not event.eventname.endswith('edit_table'):
                return

            # In the summary
            if event.row < FIRST_BUILD_ROW:
                field:str = list(self.summary_cols.keys())[event.column]
                if event.row == 1 and field == 'Architect':
                    self.colonisation.modify_system(sysnum, {field: event.value})
                return

            field:str = list(self.detail_cols.keys())[event.column]
            row:int = event.row - FIRST_BUILD_ROW; val = event.value

            data:dict = {}
            match field:
                case 'Base Type' | 'Layout' if val == ' ':
                    # If they set the base type to empty remove the build
                    if row > 0 and row < len(systems[sysnum]['Builds']):
                        self.colonisation.remove_build(sysnum, row)
                    else:
                        self.colonisation.set_base_type(systems[sysnum], row, val)

                    sdata:list = self.sheets[sysnum].data
                    sdata.pop(row + FIRST_BUILD_ROW)
                    self.sheets[sysnum].set_sheet_data(sdata)
                    self._config_sheet(self.sheets[sysnum], systems[sysnum])

                case 'Base Type' | 'Layout' if val != ' ':
                    self.colonisation.set_base_type(systems[sysnum], row, val)

                    # Initial cell population
                    sdata:list = []
                    sdata.append(self._get_summary_header())
                    sdata += self._build_summary(systems[sysnum])

                    sdata.append(self._get_detail_header())
                    sdata += self._build_detail(systems[sysnum])

                    self.sheets[sysnum].set_sheet_data(sdata)
                    self._config_sheet(self.sheets[sysnum], systems[sysnum])

                case 'Body':
                    # If the body is set, update the build data
                    data[field] = val
                    if val == ' ':
                        data['BodyNum'] = None
                    else:
                        body:dict = self.colonisation.get_body(systems[sysnum], val)
                        if body != None: data['BodyNum'] = body.get('bodyId', None)

                case _:
                    # Any other fields, just update the build data
                    data[field] = val.strip() if isinstance(val, str) else val

            # Add the data to the build
            if data != {}:
                if row >= len(systems[sysnum].get('Builds', [])):
                    self.colonisation.add_build(sysnum, data)
                else:
                    self.colonisation.modify_build(sysnum, row, data)

            self.update_display()

        except Exception as e:
            Debug.logger.error(f"Error in sheet_modified(): {e}")
            Debug.logger.error(traceback.format_exc())


    def add_system_dialog(self) -> tk.Frame:
        ''' Show dialog to add a new system '''
        try:
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

            prepop_var = tk.IntVar()
            chk = tk.Checkbutton(add, text=_("Pre-fill bases"), variable=prepop_var, onvalue=True, offvalue=False) # LANG: Label for checkbox to pre-populate bases
            chk.grid(row=row, column=1, padx=10, pady=0, sticky=tk.W)
            row += 1

            rcsync_var = tk.IntVar()
            chk = tk.Checkbutton(add, text=_("Sync with RavenColonial"), variable=rcsync_var, onvalue=True, offvalue=False) # LANG: Label for checkbox to sync data with RavenColonial
            chk.grid(row=row, column=1, padx=10, pady=0, sticky=tk.W)
            row += 1

            lbl = ttk.Label(add, text=_("When planning your system the first base is special, make sure that it is the first on the list.")) # LANG: Notice about the first base being special
            lbl.grid(row=row, column=0, columnspan=2, padx=10, pady=0, sticky=tk.W)
            row += 1
            lbl = ttk.Label(add, text=_("Pre-filling requires a system name, can have mixed results, and will likely require manual\nbase type selection. Use with caution!")) # LANG: Notice about prepopulation being challenging
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

        except Exception as e:
            Debug.logger.error(f"Error in add_system: {e}")
            Debug.logger.error(traceback.format_exc())


    def update_react_dialog(self) -> None:
        try:
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
            return

        except Exception as e:
            Debug.logger.error(f"Error in update_react_dialog: {e}")
            Debug.logger.error(traceback.format_exc())


    def _reactivate_system(self, sysnum:int) -> None:
        try:
            Debug.logger.debug("Reactivating system: {sysnum}")
            self.colonisation.modify_system(sysnum, {'Hidden':False})
            Debug.logger.debug(f"{self.tabbar.tabs()}")
            self.tabbar.notebookTab.tab(sysnum+1, state='normal')
            self.update_react_dialog()
            return

        except Exception as e:
            Debug.logger.error(f"Error in reactivate_system: {e}")
            Debug.logger.error(traceback.format_exc())


    def _add_system(self, plan_name:str, system_name:str, prepop:int = False, rcsync:int = False) -> None:
        ''' Add the new system from the dialog '''
        try:
            if not plan_name:
                messagebox.showerror(_("Error"), _("Plan name is required")) # LANG: Error when no plan name is given
                return

            # Add the system
            system:dict = self.colonisation.add_system(plan_name, system_name, None, prepop, rcsync)
            if system == False:
                messagebox.showerror(_("Error"), _("Unable to create system")) # LANG: General failure to create system error
                return

            systems:list = self.colonisation.get_all_systems()
            self._create_system_tab(len(systems), system)
            self.update_display()

        except Exception as e:
            Debug.logger.error(f"Error in add_system: {e}")
            Debug.logger.error(traceback.format_exc())


    def edit_system_dialog(self, tabnum:int, tab:ttk.Frame) -> None:
        ''' Show dialog to edit a system '''
        try:
            sysnum:int = tabnum -1
            systems:list = self.colonisation.get_all_systems()
            if sysnum > len(systems):
                Debug.logger.info(f"Invalid tab {tabnum} {sysnum}")

            system:dict = systems[sysnum]
            dialog:tk.Toplevel = tk.Toplevel(self.window)
            dialog.title(_("Edit System")) # LANG: Rename a system
            dialog.minsize(500, 250)
            dialog.geometry(f"{int(500*self.scale)}x{int(250*self.scale)}")
            dialog.transient(self.window)
            dialog.grab_set()

            row:int = 0
            # System name
            ttk.Label(dialog, text=_("Plan Name")+":").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W) # LANG: the name you want to give your plan
            plan_name_var:tk.StringVar = tk.StringVar(value=system.get('Name', ''))
            plan_name_entry:ttk.Entr = ttk.Entry(dialog, textvariable=plan_name_var, width=30)
            plan_name_entry.grid(row=row, column=1, padx=10, pady=(10,5), sticky=tk.W)
            row += 1

            # Display name
            ttk.Label(dialog, text=_("System Name") + "\n(" + _("optional and case sensitive") + "):").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W) # LANG: Elite dangerous system name
            system_name_var:tk.StringVar = tk.StringVar(value=system.get('StarSystem', ''))
            system_name_entry:ttk.Entry = ttk.Entry(dialog, textvariable=system_name_var, width=30)
            system_name_entry.grid(row=row, column=1, padx=10, pady=(5,10), sticky=tk.W)
            row += 1

            rcsync_var = tk.IntVar()
            rcsync_var.set(True if system.get('RCSync', 0) != 0 else False)
            chk = tk.Checkbutton(dialog, text=_("Sync with RavenColonial"), variable=rcsync_var, onvalue=True, offvalue=False) # LANG: Label for checkbox to sync data with RavenColonial
            chk.grid(row=row, column=1, padx=10, pady=(0,0), sticky=tk.W)
            row += 1

            hide_var = tk.IntVar()
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
                command=lambda: self._edit_system(tabnum, tab, plan_name_var.get(), system_name_var.get(), rcsync_var.get(), hide_var.get(), dialog)
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

        except Exception as e:
            Debug.logger.error(f"Error in rename_system_dialog(): {e}")
            Debug.logger.error(traceback.format_exc())


    def _edit_system(self, tabnum:int, tab:ttk.Frame, name:str, sysname:str, rcsync:bool, hide:bool, dialog:tk.Toplevel) -> None:
        ''' Edit a system's plan, name and sync state '''
        try:
            sysnum:int = tabnum -1

            if not name:
                messagebox.showerror(_("Error"), _("Plan name is required"))
                return

            data:dict = {
                'Name': name,
                'StarSystem': sysname,
                'RCSync': 1 if rcsync == True else 0,
                'Hidden' : hide
            }
            if hide == True:
                self.tabbar.hide(tabnum)

            self.colonisation.modify_system(sysnum, data)
            self.tabbar.notebookTab.tab(tabnum, text=name)
            self.update_react_dialog()

            dialog.destroy()
            self.update_display()

        except Exception as e:
            Debug.logger.error(f"Error in rename_system(): {e}")
            Debug.logger.error(traceback.format_exc())


    def delete_system(self, tabnum:int, tab: ttk.Frame) -> None:
        ''' Remove the current system '''
        try:
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

        except Exception as e:
            Debug.logger.error(f"Error in delete_system(): {e}")
            Debug.logger.error(traceback.format_exc())


    def _rc_refresh_system(self, tabnum:int) -> None:
        ''' Reload the current system from RavenColonial '''
        try:
            sysnum:int = tabnum -1
            systems:list = self.colonisation.get_all_systems()
            if sysnum > len(systems):
                Debug.logger.info(f"Invalid tab {tabnum} {sysnum}")

            system:dict = systems[sysnum]
            if system.get('RCSync', 0) == 0:
                return

            # Refresh the RC data when the window is opened/created
            Debug.logger.debug(f"Reloading system {system.get('StarSystem', 'Unknown')} from ID64 {system.get('ID64')}")
            if self.colonisation.rc == None: self.rc = RavenColonial(self)
            if system.get('ID64', None) == None:
                Debug.logger.debug(f"Calling add_system")
                self.colonisation.rc.add_system(system.get('StarSystem'))
            else:
                Debug.logger.debug(f"Calling load_system")
                self.colonisation.rc.load_system(system.get('ID64'), system.get('Rev', None))

            if self.bgstally.fleet_carrier.available() == True:
                self.colonisation.rc.update_carrier(self.bgstally.fleet_carrier.carrier_id, self.colonisation.carrier_cargo)

            # @TODO: Create a proper project sync process.
            #for b in system['Builds']:
            #    if b.get('State') == BuildState.PROGRESS and b.get('BuildID', None) != None:
            #        self.rc.load_project()
            self.update_display()

        except Exception as e:
            Debug.logger.error(f"Error in _rc_refresh_system(): {e}")
            Debug.logger.error(traceback.format_exc())


    def close(self) -> None:
        ''' Close the window and any popups and clean up'''
        try:
            if self.window: self.window.destroy()
            if self.legend_fr: self.legend_fr.destroy()
            if self.notes_fr: self.notes_fr.destroy()
            if self.bases_fr: self.bases_fr.destroy()
            if self.bodies_fr: self.bodies_fr.destroy()

            # UI components
            self.tabbar:ScrollableNotebook
            self.sheets:list = []
            self.plan_titles:list = []
            self.colonisation.save()

        except Exception as e:
            Debug.logger.error(f"Error in close(): {e}")
            Debug.logger.error(traceback.format_exc())


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


    def _set_weight(self, item, wght:str = 'bold') -> None:
        ''' Set font weight '''
        fnt = tkFont.Font(font=item['font']).actual()
        item.configure(font=(fnt['family'], fnt['size'], wght))


    def is_build_complete(self, build:list[dict]) -> bool:
        ''' Check if a build is complete '''
        return (self.colonisation.get_build_state(build) == BuildState.COMPLETE)


    def is_build_started(self, build:list[dict]) -> bool:
        ''' Check if a build is in progress '''
        return (self.colonisation.get_build_state(build) == BuildState.PROGRESS)


    def _load_legend(self) -> str:
        ''' Load the legend text from the language appropriate file '''
        try:
            file:str = path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)
            lang:str = config.get_str('language')
            if lang and lang != 'en':
                file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, "L10n", f"{lang}.{FILENAME}")

            if not path.exists(file):
                Debug.logger.info(f"Missing translation {file} for {lang}, using default legend file")
                file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)

            if path.exists(file):
                with open(file) as fh:
                    legend:str = fh.read()
                return legend

            return f"Unable to load {file}"

        except Exception as e:
            Debug.logger.warning(f"Unable to load legend {file}")
            Debug.logger.error(traceback.format_exc())
            return ''

    def legend_popup(self) -> None:
        ''' Show the legend popup window '''
        try:
            if self.legend_fr != None and self.legend_fr.winfo_exists():
                self.legend_fr.lift()
                return

            self.legend_fr = tk.Toplevel(self.bgstally.ui.frame)
            self.legend_fr.wm_title(_("{plugin_name} - Colonisation Legend").format(plugin_name=self.bgstally.plugin_name)) # LANG: Title of the legend popup window
            self.legend_fr.wm_attributes('-topmost', True)     # keeps popup above everything until closed.
            self.legend_fr.wm_attributes('-toolwindow', True) # makes it a tool window
            self.legend_fr.geometry("600x600")
            self.legend_fr.config(bd=2, relief=tk.FLAT)
            scr:tk.Scrollbar = tk.Scrollbar(self.legend_fr, orient=tk.VERTICAL)
            scr.pack(side=tk.RIGHT, fill=tk.Y)

            text:tk.Text = tk.Text(self.legend_fr, font=FONT_SMALL, yscrollcommand=scr.set)
            text.insert(tk.END, self._load_legend())
            text.pack(fill=tk.BOTH, side=tk.TOP, expand=True, padx=5, pady=5)

        except Exception as e:
            Debug.logger.error(f"Error in legend_popup(): {e}")
            Debug.logger.error(traceback.format_exc())


    def notes_popup(self, tabnum:int) -> None:
        ''' Show the notes popup window '''
        try:
            def savenotes(system:dict, text:tk.Text) -> None:
                ''' Save the notes and close the popup window '''
                if sysnum > len(self.plan_titles):
                    Debug.logger.info(f"Saving notes invalid tab: {tabnum}")
                    return

                notes:str = text.get("1.0", tk.END)
                system['Notes'] = notes
                self.colonisation.save()
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

        except Exception as e:
            Debug.logger.error(f"Error in notes_popup(): {e}")
            Debug.logger.error(traceback.format_exc())


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


    def _get_color(self, value:int, limit:int = 1, color:str = 'rwg') -> str:
        ''' Get a color based on the value and its range. '''
        try:
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

        except Exception as e:
            Debug.logger.error(f"Error in get_color: {e}")
            Debug.logger.error(traceback.format_exc())
            return "#7A007A"


    def _create_gradient(self, steps:int, type:str = 'rwg') -> list[str]:
        ''' Generates a list of RGB color tuples representing a gradient. '''
        try:
            # Green, Yellow, Red (0:steps)
            s = (150, 200, 150) # start
            m = (230, 230, 125) # middle
            e = (190, 30, 100) # end

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
            r_step_1:int = (m[0] - s[0]) / steps
            g_step_1:int = (m[1] - s[1]) / steps
            b_step_1:int = (m[2] - s[2]) / steps

            r_step_2:int = (e[0] - m[0]) / steps
            g_step_2:int = (e[1] - m[1]) / steps
            b_step_2:int = (e[2] - m[2]) / steps

            # Iterate and interpolate
            for i in range(steps+1):
                # Interpolate between start and middle
                if i < steps/2:
                    cr = min(max(s[0] + r_step_1 * i, 0), 255)
                    cg = min(max(s[1] + g_step_1 * i, 0), 255)
                    cb = min(max(s[2] + b_step_1 * i, 0), 255)
                else: # Interpolate between middle and end
                    cr = min(max(m[0] + r_step_2 * (i - steps/2), 0), 255)
                    cg = min(max(m[1] + g_step_2 * (i - steps/2), 0), 255)
                    cb = min(max(m[2] + b_step_2 * (i - steps/2), 0), 255)

                # Add the interpolated color to the gradient
                gradient_colors.append(f"#{int(cr):02x}{int(cg):02x}{int(cb):02x}")

            return gradient_colors

        except Exception as e:
            Debug.logger.error(f"Error in gradient: {e}")
            Debug.logger.error(traceback.format_exc())
            return ["#7A007A"]


    def _detcol(self, col:str) -> int:
        ''' Macro to shorten references to detail columns '''
        #cols:list = list(self.detail_cols.keys())
        return list(self.detail_cols.keys()).index(col)