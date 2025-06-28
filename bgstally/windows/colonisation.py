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
from thirdparty.ScrollableNotebook import ScrollableNotebook
from thirdparty.tksheet import Sheet
from thirdparty.Tooltip import ToolTip
from bgstally.constants import FONT_HEADING_1, COLOUR_HEADING_1, FONT_SMALL, FONT_TEXT, FOLDER_DATA, FOLDER_ASSETS, BuildState
from bgstally.debug import Debug
from bgstally.utils import _, human_format

FILENAME = "colonisation_legend.txt" # LANG: Not sure how we handle file localistion.
SUMMARY_HEADER_ROW = 0
FIRST_SUMMARY_ROW = 1
FIRST_SUMMARY_COLUMN = 3
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
            'Name' : {'header': _("Base Name"), 'background': None, 'format': 'dropdown', 'width': 225}, # LANG: name of the base
            'Body': {'header': _("Body"), 'background': None, 'format': 'string', 'width': 115}, # LANG: Body the base is on or around
            'Prerequisites': {'header': _("Type"), 'background': None, 'format': 'string', 'width': 115}, # LANG: body type details
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
            if self.window is not None and self.window.winfo_exists():
                self.window.lift()
                return

            # We do this once because it seems to get lost over time
            if self.scale == 0:
                self.scale = self.bgstally.ui.frame.tk.call('tk', 'scaling') - 0.6

            self.colonisation = self.bgstally.colonisation
            self.window:tk.Toplevel = tk.Toplevel(self.bgstally.ui.frame)
            self.window.title(_("BGS-Tally - Colonisation")) # LANG: window title

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
            self.add_system_dialog()

            # Add tabs for each system
            systems:list = self.colonisation.get_all_systems()

            if len(systems) == 0:
                Debug.logger.info(f"No systems so not creating colonisation section")
                return

            for sysnum, system in enumerate(systems):
                # Create a frame for the sytem
                tabnum = sysnum +1
                self._create_system_tab(tabnum, system)

            # Select the first tab
            if tabnum > 0:
                self.tabbar.select(1)

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
        self._set_system_progress(tabnum, system)


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
        name_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.plan_titles[sysnum]['Name'] = name_label

        sys_label:ttk.Label = ttk.Label(title_frame, text="", cursor="hand2")
        sys_label.pack(side=tk.LEFT, padx=5, pady=5)
        self._set_weight(sys_label)
        sys_label.bind("<Button-1>", partial(self.system_click, tabnum))
        self.plan_titles[sysnum]['System'] = sys_label

        sys_copy:ttk.Label = ttk.Label(title_frame, text='⮺   ', cursor='hand2')
        sys_copy.pack(side=tk.LEFT, padx=(0,10), pady=5)
        self._set_weight(sys_copy)
        sys_copy.bind("<Button-1>", partial(self.ctc, tabnum))
        ToolTip(sys_copy, text=_("Copy system name to clipboard")) # LANG: tooltip for the copy to clipboard icon

        if systems[sysnum].get('Bodies', None) != None and len(systems[sysnum]['Bodies']) > 0:
            bodies = str(len(systems[sysnum]['Bodies'])) + " " + _("Bodies") # LANG: bodies in the system
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
        btn.pack(side=tk.RIGHT, padx=5, pady=5)
        ToolTip(btn, text=_("Show legend window")) # LANG: tooltip for the show legend button

        btn:ttk.Button = ttk.Button(title_frame, text=_("Delete"), cursor="hand2", command=lambda: self.delete_system(tabnum, tab)) # LANG: Delete button
        ToolTip(btn, text=_("Delete system plan")) # LANG: tooltip for the delete system button
        btn.pack(side=tk.RIGHT, padx=5, pady=5)

        btn:ttk.Button = ttk.Button(title_frame, text=_("Rename"), cursor="hand2", command=lambda: self.rename_system_dialog(tabnum, tab)) # LANG: Rename button
        ToolTip(btn, text=_("Rename system plan")) # LANG: tooltip for the rename system button
        btn.pack(side=tk.RIGHT, padx=5, pady=5)

        if systems[sysnum].get('Bodies', None) != None and len(systems[sysnum]['Bodies']) > 0:
            btn:ttk.Button = ttk.Button(title_frame, text="🌐", width=3, cursor="hand2", command=lambda: self.bodies_popup())
            btn.pack(side=tk.RIGHT, padx=5, pady=5)
            ToolTip(btn, text=_("Show system bodies window")) # LANG: tooltip for the show bodies window

        btn:ttk.Button = ttk.Button(title_frame, text="🔍", width=3, cursor="hand2", command=lambda: self.bases_popup())
        btn.pack(side=tk.RIGHT, padx=5, pady=5)
        ToolTip(btn, text=_("Show base types window")) # LANG: tooltip for the show bases button

        btn:ttk.Button = ttk.Button(title_frame, text=_("📓"), cursor="hand2", width=3, command=partial(self.notes_popup, tabnum))
        btn.pack(side=tk.RIGHT, padx=5, pady=5)
        ToolTip(btn, text=_("Show system notes window")) # LANG: tooltip for the show notes window


    def ctc(self, tabnum:int, event) -> None:
        ''' Copy to clipboard '''
        try:
            systems:list = self.colonisation.get_all_systems()
            self.window.clipboard_clear()
            self.window.clipboard_append(systems[tabnum-1].get('StarSystem', ''))
        except Exception as e:
            Debug.logger.error(f"Error in ctc() {e}")
            Debug.logger.error(traceback.format_exc())


    def system_click(self, tabnum:int, event) -> None:
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
            if self.bases_fr is not None and self.bases_fr.winfo_exists():
                self.bases_fr.lift()
                return

            self.bases_fr = tk.Toplevel(self.bgstally.ui.frame)
            self.bases_fr.wm_title(_("BGS-Tally - Colonisation Base Types")) # LANG: Title of the base type popup window
            self.bases_fr.geometry(f"{int(1000*self.scale)}x{int(500*self.scale)}")
            self.bases_fr.protocol("WM_DELETE_WINDOW", self.bases_fr.destroy)
            self.bases_fr.config(bd=2, relief=tk.FLAT)
            sheet:Sheet = Sheet(self.bases_fr, show_row_index=False, cell_auto_resize_enabled=True, height=4096,
                            show_horizontal_grid=True, show_vertical_grid=True, show_top_left=False,
                            align="center", show_selected_cells_border=True, table_selected_cells_border_fg=None,
                            show_dropdown_borders=False, header_bg='lightgrey',
                            empty_vertical=0, empty_horizontal=0, header_font=FONT_SMALL, font=FONT_SMALL, arrow_key_down_right_scroll_page=True,
                            show_header=True, set_all_heights_and_widths=True) #, default_row_height=21)
            sheet.pack(fill=tk.BOTH, padx=0, pady=0)

            data:list = [[0 for _ in range(len(self.bases.keys()))] for _ in range(len(self.colonisation.get_base_types()))]
            sheet.set_header_data([h['header'] for h in self.bases.values()])
            sheet.set_sheet_data(data)
            sheet["A1:A100"].align(align='left')
            sheet["E1:F100"].align(align='left')
            sheet["T1:V100"].align(align='left')

            for i, bt in enumerate(self.colonisation.base_types.values()):
                for j, (name, col) in enumerate(self.bases.items()):
                    sheet.column_width(j, int(col.get('width', 100) * self.scale))
                    match col.get('format'):
                        case 'int':
                            v = bt.get(name, 0)
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

        except Exception as e:
            Debug.logger.error(f"Error in bases_popup(): {e}")
            Debug.logger.error(traceback.format_exc())


    def bodies_popup(self, tabnum:int, event) -> None:
        ''' Show a popup with details of all the bodies in the system '''
        try:
            if self.bodies_fr is not None and self.bodies_fr.winfo_exists():
                self.bodies_fr.destroy()

            self.bodies_fr = tk.Toplevel(self.bgstally.ui.frame)
            self.bodies_fr.wm_title(_("BGS-Tally - Colonisation Bodies")) # LANG: Title of the bodies popup window
            self.bodies_fr.wm_attributes('-toolwindow', True) # makes it a tool window
            self.bodies_fr.geometry("600x600")
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
                if b.get('isLandable') == True: attrs.append(f"{_('Landable')}")
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
        sheet.extra_bindings('all_modified_events', func=partial(self.sheet_modified, tabnum))
        sheet.extra_bindings('cell_select', func=partial(self.sheet_modified, tabnum))

        if len(self.sheets) < tabnum:
            self.sheets.append(sheet)
        else:
            self.sheets[tabnum-1] = sheet


    def _update_title(self, index:int, system:dict) -> None:
        ''' Update title with both display name and actual system name '''
        name:str = system.get('Name') if system.get('Name') != None else system.get('StarSystem', _('Unknown')) # LANG: Default when we don't know the name
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
            sheet.column_width(i, int(value.get('width', 100) * self.scale))

        # header lines
        sheet[SUMMARY_HEADER_ROW].highlight(bg='lightgrey')
        sheet['A2:F2'].highlight(bg=self._set_background('type', 'Complete', 1))
        sheet['A3:F3'].highlight(bg=self._set_background('type', 'Planned', 1))
        sheet[HEADER_ROW].highlight(bg='lightgrey')

        # Tracking checkboxes
        sheet['A5:A'].checkbox(state='normal', checked=False)

        # Base types
        sheet['B5'].dropdown(values=[' '] + self.colonisation.get_base_types('Initial'))
        sheet['B6:B'].dropdown(values=[' '] + self.colonisation.get_base_types('All'))
        if system != None and 'Bodies' in system:
            bodies:list = self.colonisation.get_bodies(system)
            if len(bodies) > 0:
                sheet['D5:D'].dropdown(values=[' '] + bodies)

        # Make the sections readonly that users can't edit.
        s3 = sheet.span('A1:4', type_='readonly')
        sheet.named_span(s3)
        s4 = sheet.span('E4:T', type_='readonly')
        sheet.named_span(s4)

        # track, types and names left.
        sheet[f"A{FIRST_BUILD_ROW}:C"].align(align='left')


    def _get_summary_header(self) -> list[str]:
        ''' Return the header row for the summary '''
        cols:list = [' ', ' ', ' ']
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
        min:int = 35 if len([1 for build in builds if build.get('Base Type') in starports and self.colonisation.get_build_state(build) == BuildState.COMPLETE]) > 0 else 0
        totals['Complete']['Technology Level'] = max(totals['Complete']['Technology Level'], min)

        return totals


    def _build_summary(self, system:dict) -> list[list]:
        ''' Return the summary section with current system data '''
        totals:dict = self._calc_totals(system)

        # Update the values in the cells.
        summary:list = []
        for i, r in enumerate(self.summary_rows.keys()):
            row:list = [' ', ' ', r]
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
                j += FIRST_SUMMARY_COLUMN
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
                            row.append(build.get('Body').replace(system.get('StarSystem') + ' ', ''))
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
            if system != None and 'Bodies' in system and new[i][3] != ' ':
                b = self.colonisation.get_body(system, new[i][3])
                desc:str = b.get('subType', 'Unknown')
                if b.get('type') == 'Star': desc = re.sub(r".*\((.+)\).*", r"\1", desc)
                if b.get('subType') == 'High metal content world': desc = _('HMC World') # LANG: HMC World is a high metal content world

                #attrs:list = []
                #if b.get('terraformingState', 'Not terraformable') != 'Not terraformable': attrs.append("T")
                #if b.get('volcanismType', 'None') != 'None': attrs.append("V")
                #if len(attrs) > 0:
                #    desc += " (" + ", ".join(attrs) + ")"
                sheet[i+srow,4].data = desc
                #sheet[i+srow,4].align(align='left')

            # Handle build states
            if new[i][5] == BuildState.COMPLETE: # Mark complete builds as readonly
                # Tracking
                sheet[i+srow,0].del_checkbox()
                sheet[i+srow,0].data = ' 🢅' #⇒
                #sheet[i+srow,0].checkbox(state='disabled'); sheet[i+srow,0].data = ' ';
                sheet[i+srow,0].readonly()
                sheet[i+srow,0].align(align='left')

                # Base type
                if new[i][1] in self.colonisation.get_base_types(): # Base type has been set so make it readonly
                    sheet[i+srow,1].del_dropdown()
                    sheet[i+srow,1].readonly()
                    sheet[i+srow,1].highlight(bg=None)
                elif new[i][1] != ' ' or new[i][2] != ' ': # Base type is invalid or not set & name is set
                    sheet[i+srow,1].highlight(bg='red2')
                sheet[i+srow,1].align(align='left')

                # Base name
                sheet[i+srow,2].readonly()
                sheet[i+srow,2].align(align='left')

                # Body
                sheet[i+srow,3].del_dropdown()
                sheet[i+srow,3].readonly()
                continue

            #if isinstance(new[i][5], int):
            #    sheet.create_progress_bar(row=i+srow, column=5, bg='red', fg='green', percent=new[i][5], name=f"{i}")
            #    Debug.logger.debug("Creating progress bar {sheet[i+srow,5]}")

            #  Tracking
            sheet[i+srow,0].checkbox(state='normal'); sheet[i+srow,0].data = ' '; sheet[i+srow,0].readonly(False)

            # Base type
            sheet[i+srow,1].dropdown(values=[' '] + self.colonisation.get_base_types('All' if i > 0 else 'Initial'))
            sheet[i+srow,1].align(align='left')
            sheet[i+srow,1].readonly(False)
            sheet[i+srow,1].data = new[i][1]

            # Base name
            sheet[i+srow,2].readonly(False)

            # Body
            if system != None and 'Bodies' in system:
                bodies:list = self.colonisation.get_bodies(system)
                if len(bodies) > 0:
                    sheet[i+srow,3].dropdown(values=[' '] + bodies)
            sheet[i+srow,3].readonly(False)
            sheet[i+srow,3].data = new[i][3]

        # Clear the highlights on the empty last row
        if len(new) > len(system.get('Builds', [])):
            for j, details in enumerate(self.detail_cols.values()):
                sheet[len(new)+srow-1,j].highlight(bg=None)
            sheet[len(new)+srow-1,5].data = ' '


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


    def validate_edits(self, event):
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


    def sheet_modified(self, tabnum:int, event) -> None:
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
                        systems[sysnum]['Builds'][row]['State'] = BuildState.PLANNED
                    else:
                        systems[sysnum]['Builds'][row]['State'] = BuildState.COMPLETE

                    self.colonisation.dirty = True
                    self.colonisation.save()
                    self.update_display()

                #if field in ['Name', 'Base Type'] and row < len(systems[sysnum]['Builds']) and systems[sysnum]['Builds'][row]['State'] == BuildState.COMPLETE:
                if field in ['Track'] and row < len(systems[sysnum]['Builds']) and systems[sysnum]['Builds'][row]['State'] == BuildState.COMPLETE:
                    opener:str = plug.invoke(config.get_str('station_provider'), 'EDSM', 'station_url', systems[sysnum]['StarSystem'], systems[sysnum]['Builds'][row]['Name'])
                    if opener:
                        return webbrowser.open(opener)
                return

            # We only deal with edits.
            if not event.eventname.endswith('edit_table'):
                return

            fields:list = list(self.detail_cols.keys())
            field:str = fields[event.column]
            row:int = event.row - FIRST_BUILD_ROW; val = event.value

            match field:
                case 'Base Type' if val == ' ':
                    # If they set the base type to empty remove the build
                    if row < len(systems[sysnum]['Builds']):
                        self.colonisation.remove_build(systems[sysnum], row)
                    else:
                        systems[sysnum]['Builds'][row][field] = val
                    data:list = self.sheets[sysnum].data
                    data.pop(row + FIRST_BUILD_ROW)
                    self.sheets[sysnum].set_sheet_data(data)
                    self._config_sheet(self.sheets[sysnum], systems[sysnum])

                case 'Base Type' if val != ' ':
                    if row >= len(systems[sysnum]['Builds']):
                        self.colonisation.add_build(systems[sysnum])
                        systems[sysnum]['Builds'][row][field] = val

                    # Initial cell population
                    data:list = []
                    data.append(self._get_summary_header())
                    data += self._build_summary(systems[sysnum])

                    data.append(self._get_detail_header())
                    data += self._build_detail(systems[sysnum])

                    self.sheets[sysnum].set_sheet_data(data)
                    self._config_sheet(self.sheets[sysnum], systems[sysnum])

                    systems[sysnum]['Builds'][row][field] = val

                case 'Track':
                    # Toggle the tracked status.
                    # Make sure the plan name is up to date as the progress view uses it.
                    self.colonisation.update_build_tracking(systems[sysnum]['Builds'][row], val)

                case _:
                    # Any other fields, just update the build data
                    if row >= len(systems[sysnum]['Builds']):
                        self.colonisation.add_build(systems[sysnum])
                    systems[sysnum]['Builds'][row][field] = val

            self.colonisation.dirty = True
            self.colonisation.save()
            self.update_display()

        except Exception as e:
            Debug.logger.error(f"Error in sheet_modified(): {e}")
            Debug.logger.error(traceback.format_exc())


    def add_system_dialog(self) -> None:
        ''' Show dialog to add a new system '''
        dialog:tk.Frame = tk.Frame(self.tabbar)
        dialog.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)

        # System name
        row:int = 0
        ttk.Label(dialog, text=_("Plan Name")+":").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W) # LANG: the name you want to give your plan
        plan_name_var:tk.StringVar = tk.StringVar()
        plan_name_entry:ttk.Entry = ttk.Entry(dialog, textvariable=plan_name_var, width=30)
        plan_name_entry.grid(row=row, column=1, padx=10, pady=10, sticky=tk.W)
        row += 1

        # Display name
        syslabel:str = _("System Name") # LANG: Label for the system's name field in the UI
        optionlabel:str = _("optional and case sensitive") # LANG: Indicates the field is optional and case-sensitive
        ttk.Label(dialog, text=f"{syslabel} ({optionlabel}):").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        system_name_var:tk.StringVar = tk.StringVar()
        system_name_entry:ttk.Entry = ttk.Entry(dialog, textvariable=system_name_var, width=30)
        system_name_entry.grid(row=row, column=1, padx=10, pady=10, sticky=tk.W)
        row += 1

        prepop_var = tk.IntVar()
        chk = tk.Checkbutton(dialog, text=_("Pre-fill bases from EDSM"), variable=prepop_var, onvalue=True, offvalue=False) # LANG: Label for checkbox to pre-populate bases from EDSM
        chk.grid(row=row, column=1, padx=10, pady=10, sticky=tk.W)
        row += 1

        lbl = ttk.Label(dialog, text=_("When planning your system the first base is special, make sure that it is the first on the list.")) # LANG: Notice about the first base being special
        lbl.grid(row=row, column=0, columnspan=2, padx=10, pady=(10,0), sticky=tk.W)
        row += 1
        lbl = ttk.Label(dialog, text=_("Pre-filling requires a system name, can have mixed results, and will likely require manual base type selection. Use with caution!")) # LANG: Notice about prepopulation being challenging
        lbl.grid(row=row, column=0, columnspan=2, padx=10, pady=(0,10), sticky=tk.W)
        row += 1

        # Buttons
        button_frame:ttk.Frame = ttk.Frame(dialog)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        # Add button
        add_button:ttk.Button = ttk.Button(
            button_frame,
            text=_("Add"), # LANG: Add/create a new system
            command=lambda: self._add_system(plan_name_var.get(), system_name_var.get(), prepop_var.get())
        )
        add_button.pack(side=tk.LEFT, padx=5)
        self.tabbar.add(dialog, text='+')


    def _add_system(self, plan_name:str, system_name:str, prepop:bool = False) -> None:
        ''' Add the new system from the dialog '''
        try:
            if not plan_name:
                messagebox.showerror(_("Error"), _("Plan name is required")) # LANG: Error when no plan name is given
                return

            # Add the system
            system:dict = self.colonisation.add_system(plan_name, system_name, system_name, prepop)
            if system == False:
                messagebox.showerror(_("Error"), _("Unable to create system")) # LANG: General failure to create system error
                return

            systems:list = self.colonisation.get_all_systems()
            self._create_system_tab(len(systems), system)
            self.update_display()

        except Exception as e:
            Debug.logger.error(f"Error in add_system: {e}")
            Debug.logger.error(traceback.format_exc())


    def rename_system_dialog(self, tabnum:int, tab:ttk.Frame) -> None:
        ''' Show dialog to rename a system '''
        try:
            sysnum:int = tabnum -1
            systems:list = self.colonisation.get_all_systems()
            if sysnum > len(systems):
                Debug.logger.info(f"Invalid tab {tabnum} {sysnum}")

            system:dict = systems[sysnum]
            dialog:tk.Toplevel = tk.Toplevel(self.window)
            dialog.title(_("Rename System")) # LANG: Rename a system
            dialog.geometry("500x150")
            dialog.transient(self.window)
            dialog.grab_set()

            # System name
            ttk.Label(dialog, text=_("Plan Name")+":").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W) # LANG: the name you want to give your plan
            plan_name_var:tk.StringVar = tk.StringVar(value=system.get('Name', ''))
            plan_name_entry:ttk.Entr = ttk.Entry(dialog, textvariable=plan_name_var, width=30)
            plan_name_entry.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)

            # Display name
            ttk.Label(dialog, text=_("System Name") + " ()" + _("optional and case sensitive") + "):").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W) # LANG: Elite dangerous system name
            system_name_var:tk.StringVar = tk.StringVar(value=system.get('StarSystem', ''))
            system_name_entry:ttk.Entry = ttk.Entry(dialog, textvariable=system_name_var, width=30)
            system_name_entry.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)

            # Buttons
            button_frame:ttk.Frame = ttk.Frame(dialog)
            button_frame.grid(row=2, column=0, columnspan=2, pady=10)

            # Rename button
            rename_button:ttk.Button = ttk.Button(
                button_frame,
                text=_("Rename"), # LANG: Rename system button
                command=lambda: self._rename_system(tabnum, tab, plan_name_var.get(), system_name_var.get(), dialog)
            ) # LANG: Rename button
            rename_button.pack(side=tk.LEFT, padx=5)

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


    def _rename_system(self, tabnum:int, tab:ttk.Frame, name:str, sysname:str, dialog:tk.Toplevel) -> None:
        ''' Rename a system '''
        try:
            sysnum:int = tabnum -1
            systems:list = self.colonisation.get_all_systems()
            if sysnum > len(systems):
                Debug.logger.info(f"Invalid tab {tabnum} {sysnum}")

            system:dict = systems[sysnum]
            system['Name'] = name
            system['StarSystem'] = sysname

            self.tabbar.notebookTab.tab(tabnum, text=name)

            self.colonisation.dirty = True
            self.colonisation.save()
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


    def close(self) -> None:
        ''' Close the window and any popups and clean up'''
        try:
            if self.window: self.window.destroy()
            if self.legend_fr: self.legend_fr.destroy()
            if self.notes_fr: self.notes_fr.destroy()
            if self.bases_fr: self.bases_fr.destroy()
            if self.bodies_fr: self.bodies_fr.destroy()

            # UI components
            self.tabbar:ScrollableNotebook = None
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


    def _set_weight(self, item:tuple, wght:str = 'bold') -> None:
        ''' Set font weight '''
        fnt:tkFont = tkFont.Font(font=item['font']).actual()
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
                with open(file) as file:
                    legend:str = file.read()
                return legend

            return f"Unable to load {file}"

        except Exception as e:
            Debug.logger.warning(f"Unable to load legend {file}")
            Debug.logger.error(traceback.format_exc())


    def legend_popup(self) -> None:
        ''' Show the legend popup window '''
        try:
            if self.legend_fr is not None and self.legend_fr.winfo_exists():
                self.legend_fr.lift()
                return

            self.legend_fr = tk.Toplevel(self.bgstally.ui.frame)
            self.legend_fr.wm_title(_("BGS-Tally - Colonisation Legend")) # LANG: Title of the legend popup window
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
                self.notes_fr = None

            sysnum:int = tabnum -1
            systems:list = self.colonisation.get_all_systems()

            if self.notes_fr is not None and self.notes_fr.winfo_exists():
                self.notes_fr.destroy()

            self.notes_fr = tk.Toplevel(self.bgstally.ui.frame)
            self.notes_fr.wm_title(_("BGS-Tally - Colonisation Notes for ") + systems[sysnum].get('Name', '')) # LANG: Title of the notes popup window
            self.notes_fr.wm_attributes('-topmost', True)     # keeps popup above everything until closed.
            self.notes_fr.geometry("600x600")
            self.notes_fr.protocol("WM_DELETE_WINDOW", self.notes_fr.destroy)
            self.notes_fr.config(bd=2, relief=tk.FLAT)
            scr:tk.Scrollbar = tk.Scrollbar(self.notes_fr, orient=tk.VERTICAL)
            scr.pack(side=tk.RIGHT, fill=tk.Y)

            text:tk.Text = tk.Text(self.notes_fr, font=FONT_SMALL, yscrollcommand=scr.set)
            notes:str = systems[sysnum].get('Notes', '')
            text.insert(tk.END, notes)
            text.pack(fill=tk.BOTH, side=tk.TOP, expand=True, padx=5, pady=5)

            # Save button
            save:ttk.Button = ttk.Button(self.notes_fr, text=_("Save"), command=partial(savenotes, systems[sysnum], text)) # LANG: Save notes button
            save.pack(side=tk.RIGHT, padx=5)

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
            value:int = min(value, limit)

            # Red, White, Green or Green, Yellow, Red
            if color == 'rwg':
                gradient:list = self._create_gradient(limit, 'rwg')
                value = min(max(int(value), -limit), limit)
                return gradient[int(value + limit)]

            # keep it within the limits
            gradient:list = self._create_gradient(limit, 'gyr')
            if value < len(gradient):
                return gradient[int(value)]

            return ["#7A007A"]

        except Exception as e:
            Debug.logger.error(f"Error in get_color: {e}")
            Debug.logger.error(traceback.format_exc())
            return ["#7A007A"]


    def _create_gradient(self, steps:int, type:str = 'rwg') -> list[str]:
        ''' Generates a list of RGB color tuples representing a gradient. '''
        try:
            # Green, Yellow, Red (0:steps)
            s:int = (150, 200, 150) # start
            m:int = (230, 230, 125) # middle
            e:int = (190, 30, 100) # end

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
