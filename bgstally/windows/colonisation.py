import tkinter as tk
import tkinter.font as tkFont
from os import path
from math import ceil
import traceback
from functools import partial
from tkinter import ttk, messagebox, PhotoImage
import webbrowser
from config import config
import plug
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
    ''' Window for managing colonisation plans. '''
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.colonisation = None
        self.window:tk.Toplevel = None
        self.image_tab_complete:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_enabled.png"))
        self.image_tab_progress:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_part_enabled.png"))
        self.image_tab_planned:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_disabled.png"))

        self.summary_rows:dict = {
            'Planned': _("Planned"), # LANG: Row heading of planned build totals i.e. ones that aren't completed
            'Completed': _("Completed") # LANG: Row heading of build totals i.e. ones that are done
        }

        # Table has two sections: summary and builds. This dict defines attributes for each summary column
        self.summary_cols:dict = {
            'Total': {'header': _("Total"), 'background': 'lightgoldenrod', 'format': 'int'}, # LANG: Total number of builds
            'Orbital': {'header': _("Orbital"), 'background': 'lightgoldenrod', 'format': 'int'}, # LANG: Number of orbital/space builds
            'Surface': {'header': _("Surface"), 'background': 'lightgoldenrod', 'format': 'int'}, # LANG: Number of ground/surface builds
            'T2': {'header': _("T2"), 'background': 'rwg', 'format': 'int', 'max': 1}, # LANG: Tier 2 points
            'T3': {'header': _("T3"), 'background': 'rwg', 'format': 'int', 'max': 1}, # LANG: Tier 3 points
            'Cost': {'header': _("Cost"), 'background': 'gyr', 'format': 'int', 'max': 200000}, # LANG: Cost in tonnes of cargo
            'Trips': {'header': _("Loads"), 'background': 'gyr', 'format': 'int', 'max': 260}, # LANG: Number of loads of cargo
            'Population': {'header': _("Pop"), 'background': False, 'hide': True, 'format': 'hidden'},
            'Economy': {'header': _("Economy"), 'background': False, 'hide': True, 'format': 'hidden'},
            'Pop Inc': {'header': _("Pop Inc"), 'background': 'rwg', 'format': 'int', 'max': 20}, # LANG: Population increase
            'Pop Max': {'header': _("Pop Max"), 'background': 'rwg', 'format': 'int', 'max': 20}, # LANG: Population Maximum
            'Economy Influence': {'header': _("Econ Inf"), 'background': False, 'hide': True, 'format': 'hidden'}, # LANG: Economy influence
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
            'Name' : {'header': _("Base Name"), 'background': None, 'format': 'dropdown', 'width': 200}, # LANG: name of the base
            'Body': {'header': _("Body"), 'background': None, 'format': 'string', 'width': 100}, # LANG: Body the base is on or around
            'Prerequisites': {'header': _("Requirements"), 'background': None, 'format': 'string', 'width': 100}, # LANG: any prerequisites for the base
            'State': {'header': _("State"), 'background': None, 'format': 'string', 'width': 100}, # LANG: Current build state
            'T2': {'header': _("T2"), 'background': 'rwg', 'format': 'int', 'max':1, 'width': 30}, # LANG: Tier 2 points
            'T3': {'header': _("T3"), 'background': 'rwg', 'format': 'int', 'min':-1, 'max':1, 'width': 30}, # LANG: Tier 3
            'Cost': {'header': _("Cost"), 'background': 'gyr', 'format': 'int', 'max':100000, 'width': 75}, # LANG: As above
            'Trips':{'header': _("Loads"), 'background': 'gyr', 'format': 'int', 'max':120, 'width': 50}, # LANG: As above
            'Pad': {'header': _("Pad"), 'background': None, 'format': 'string', 'width': 55}, # LANG: Landing pad size
            'Facility Economy': {'header': _("Economy"), 'background': None, 'format': 'string', 'width': 80}, # LANG: facility economy
            'Pop Inc': {'header': _("Pop Inc"), 'background': 'rwg', 'format': 'int', 'max':5, 'width': 65}, # LANG: As above
            'Pop Max': {'header': _("Pop Max"), 'background': 'rwg', 'format': 'int', 'max':5, 'width': 65}, # LANG: As above
            'Economy Influence': {'header': _("Econ Inf"), 'background': None, 'format': 'string', 'width': 80}, # LANG: economy influence
            'Security': {'header': _("Security"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 65}, # LANG: As above
            'Technology Level': {'header': _("Tech Lvl"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 65}, # LANG: As above
            'Wealth': {'header': _("Wealth"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 65}, # LANG: As above
            'Standard of Living': {'header': _("SoL"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 65}, # LANG: As above
            'Development Level': {'header': _("Dev Lvl"), 'background': 'rwg', 'format': 'int', 'max':8, 'width': 65} # LANG: As above
        }

        # UI components
        self.window:tk.Toplevel = None
        self.tabbar:ScrollableNotebook = None
        self.sheets:list = []
        self.plan_titles:list = []


    def show(self) -> None:
        ''' Create and display the colonisation window '''
        try:
            if self.window is not None and self.window.winfo_exists():
                self.window.lift()
                return
            self.colonisation = self.bgstally.colonisation
            self.window = tk.Toplevel(self.bgstally.ui.frame)
            self.window.title(_("BGS-Tally - Colonisation")) # LANG: window title
            self.window.minsize(400, 100)
            self.window.geometry("1400x600")
            self.window.protocol("WM_DELETE_WINDOW", self.close)

            self.create_frames()    # Create main frames
            self.update_display()   # Populate them

        except Exception as e:
            Debug.logger.error(f"Error in colonisation.show(): {e}")
            Debug.logger.error(traceback.format_exc())


    def create_frames(self) -> None:
        ''' Create the system tabs '''
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
                self.create_system_tab(tabnum, system)

            # Select the first tab
            if tabnum > 0:
                self.tabbar.select(1)

        except Exception as e:
            Debug.logger.error(f"Error in create_frames(): {e}")
            Debug.logger.error(traceback.format_exc())


    def create_system_tab(self, tabnum:int, system:dict) -> None:
        ''' Create the frame, title, and sheet for a system '''
        tab:ttk.Frame = ttk.Frame(self.tabbar)
        tab.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)

        self.create_title_frame(tabnum, tab)
        self.create_table_frame(tabnum, tab, system)
        self.tabbar.add(tab, text=system['Name'], compound='right', image=self.image_tab_planned)
        self.set_system_progress(tabnum, system)


    def set_system_progress(self, tabnum:int, system:dict) -> None:
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


    def create_title_frame(self, tabnum:int, tab:ttk.Frame) -> None:
        ''' Create the title frame with system name and tick info '''
        sysnum = tabnum -1
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
        self.weight(sys_label)
        sys_label.bind("<Button-1>", partial(self.system_click, tabnum))
        self.plan_titles[sysnum]['System'] = sys_label

        sys_copy:ttk.Label = ttk.Label(title_frame, text='⮺   ', cursor='hand2')
        sys_copy.pack(side=tk.LEFT, padx=(0,10), pady=5)
        self.weight(sys_copy)
        sys_copy.bind("<Button-1>", partial(self.ctc, tabnum))
        ToolTip(sys_copy, text=_("Copy system name to clipboard")) # LANG: tooltip for the copy to clipboard icon

        if systems[sysnum].get('Bodies', None) != None and len(systems[sysnum]['Bodies']) > 0:
            bodies = str(len(systems[sysnum]['Bodies'])) + " " + _("Bodies") # LANG: bodies in the system
            sys_bodies:ttk.Label = ttk.Label(title_frame, text=bodies, cursor="hand2")
            sys_bodies.pack(side=tk.LEFT, padx=10, pady=5)
            ToolTip(sys_bodies, text=_("Show system bodies window")) # LANG: tooltip for the show notes window
            self.weight(sys_bodies)
            sys_bodies.bind("<Button-1>", partial(self.bodies_popup, tabnum))

        attrs = []
        for attr in ['Population', 'Economy', 'Security']:
            if systems[sysnum].get(attr, '') != '':
                if isinstance(systems[sysnum].get(attr), int):
                    attrs.append(f"{human_format(systems[sysnum].get(attr))} {_(attr)}")
                else:
                    attrs.append(f"{systems[sysnum].get(attr)} {_(attr)}")
        details:ttk.Label = ttk.Label(title_frame, text="   ".join(attrs))
        self.weight(details)
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
            sysnum = tabnum -1
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


    def bodies_popup(self, tabnum:int, event) -> None:
        ''' Show the bodies popup window '''
        try:
            popup:tk.Tk = tk.Tk()

            def leavemini():
                popup.destroy()

            popup.wm_title(_("BGS-Tally - Colonisation Bodies")) # LANG: Title of the legend popup window
            popup.wm_attributes('-topmost', True)     # keeps popup above everything until closed.
            popup.wm_attributes('-toolwindow', True) # makes it a tool window
            popup.geometry("600x600")
            popup.config(bd=2, relief=tk.FLAT)
            scr:tk.Scrollbar = tk.Scrollbar(popup, orient=tk.VERTICAL)
            scr.pack(side=tk.RIGHT, fill=tk.Y)
            text:tk.Text = tk.Text(popup, font=FONT_SMALL, yscrollcommand=scr.set)
            text.pack(fill=tk.BOTH, side=tk.TOP, expand=True, padx=5, pady=5)

            sysnum:int = tabnum -1
            systems:list = self.colonisation.get_all_systems()

            bodies:list = systems[sysnum].get('Bodies', None)
            if bodies == None:
                return

            bstr:str = ""
            first:bool = True
            for b in bodies:
                indent:int = 0 if b.get('parents', None) == None else b.get('parents') * 4
                name:str = b.get('name')
                if first != True:
                    name = name.replace(systems[sysnum]['StarSystem'] + ' ', '')
                else:
                    first = False

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
            Debug.logger.error(f"Error in colonisation.show(): {e}")
            Debug.logger.error(traceback.format_exc())


    def create_table_frame(self, tabnum:int, tab:ttk.Frame, system:dict) -> None:
        ''' Create a unified table frame with both summary and builds in a single scrollable area '''
        # Main table frame
        table_frame:ttk.Frame = ttk.Frame(tab)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Configure the table frame to resize with the window
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        sheet:Sheet = Sheet(table_frame, show_row_index=False, cell_auto_resize_enabled=True, height=600,
                            show_horizontal_grid=True, show_vertical_grid=False, show_top_left=False,
                            align="center", show_selected_cells_border=True, table_selected_cells_border_fg=None,
                            show_dropdown_borders=False,
                            empty_vertical=15, empty_horizontal=0, font=FONT_SMALL, arrow_key_down_right_scroll_page=True,
                            show_header=False, set_all_heights_and_widths=True) #, default_row_height=21)
        sheet.pack(fill=tk.BOTH, padx=0, pady=(0, 5))

        # Initial cell population
        data:list = []
        data.append(self.get_summary_header())
        data += self._build_summary(system)

        data.append(self.get_detail_header())
        data += self._build_detail(system)

        sheet.set_sheet_data(data)
        self.config_sheet(sheet, system)
        sheet.enable_bindings('single_select', 'edit_cell', 'up', 'down', 'left', 'right', 'copy', 'paste')
        sheet.edit_validation(self.validate_edits)
        sheet.extra_bindings('all_modified_events', func=partial(self.sheet_modified, tabnum))
        sheet.extra_bindings('cell_select', func=partial(self.sheet_modified, tabnum))

        if len(self.sheets) < tabnum:
            self.sheets.append(sheet)
        else:
            self.sheets[tabnum-1] = sheet


    def update_title(self, index:int, system:dict) -> None:
        ''' Update title with both display name and actual system name '''
        name:str = system.get('Name') if system.get('Name') != None else system.get('StarSystem', _('Unknown')) # LANG: Default when we don't know the name
        sysname:str = system.get('StarSystem', '') + ' ⤴' if system.get('StarSystem') != '' else ''

        self.plan_titles[index]['Name']['text'] = name
        self.plan_titles[index]['System']['text'] = sysname

        # Hide the system name if it is unknown
        if sysname == None:
            self.plan_titles[index]['System'].pack_forget()


    def config_sheet(self, sheet:Sheet, system:dict = None) -> None:
        ''' Initial sheet configuration. '''
        sheet.dehighlight_all()

        # Column widths
        scale = self.bgstally.ui.frame.tk.call('tk', 'scaling') - 0.6 # Don't know why there's an extra .6
        for i, (name, value) in enumerate(self.detail_cols.items()):
            sheet.column_width(i, int(value.get('width', 100) * scale))

        # header lines
        sheet[SUMMARY_HEADER_ROW].highlight(bg='lightgrey')
        sheet['A2:C3'].highlight(bg='paleturquoise1')
        sheet['K2:L3'].highlight(bg='paleturquoise1')
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


    def get_summary_header(self) -> list[str]:
        ''' Return the header row for the summary '''
        cols:list = [' ', ' ', ' ']
        for c, v in self.summary_cols.items():
            cols.append(v.get('header', c) if v.get('hide') != True else ' ')
        return cols


    def calc_totals(self, system:dict) -> dict[str, dict[str, int]]:
        ''' Build a summary of the system's builds and status. '''
        totals:dict = {'Planned': {}, 'Completed': {}}
        builds:list = system.get('Builds', [])
        required:dict = self.colonisation.get_required(builds)

        for name, col in self.summary_cols.items():
            if col.get('hide') == True:
                totals['Planned'][name] = ' '
                totals['Completed'][name] = ' '
                continue

            totals['Planned'][name] = 0
            totals['Completed'][name] = 0

            # Calculate summary values
            for row, build in enumerate(builds):
                bt:dict = self.colonisation.get_base_type(build.get('Base Type', ''))
                if bt == {}:
                    continue
                match name:
                    case 'Total':
                        totals['Planned'][name] += 1
                        totals['Completed'][name] += 1 if self.is_build_completed(build) else 0
                    case 'Orbital'|'Surface' if bt.get('Location') == name:
                            totals['Planned'][name] += 1
                            totals['Completed'][name] += 1 if self.is_build_completed(build) else 0
                    case 'T2' | 'T3':
                        v = self.calc_points(name, builds, row)
                        totals['Planned'][name] += v
                        totals['Completed'][name] += v if self.is_build_completed(build) else 0
                    case 'Population':
                        totals['Planned'][name] = ' '
                        totals['Completed'][name] = human_format(system.get('Population', 0))
                    case 'Development Level':
                        res = bt.get(name, 0)
                        totals['Planned'][name] += res
                        totals['Completed'][name] += res if self.is_build_completed(build) else 0
                    case 'Cost' if row < len(required):
                        res = sum(required[row].values())
                        totals['Planned'][name] += res
                        totals['Completed'][name] += res if self.is_build_completed(build) else 0
                    case 'Trips' if row < len(required):
                        trips = ceil(sum(required[row].values()) / self.colonisation.cargo_capacity)
                        totals['Planned'][name] += trips
                        totals['Completed'][name] += trips if self.is_build_completed(build) else 0
                    case _ if col.get('format') == 'int':
                        totals['Planned'][name] += bt.get(name, 0)
                        totals['Completed'][name] += bt.get(name, 0) if self.is_build_completed(build) else 0

        # Deal with the "if you have a starport (t2 orbital) your tech level will be at least 35" rule
        starports = self.colonisation.get_base_types('Starport')
        min = 35 if len([1 for build in builds if build.get('Base Type') in starports]) > 0 else 0
        totals['Planned']['Technology Level'] = max(totals['Planned']['Technology Level'], min)
        min = 35 if len([1 for build in builds if build.get('Base Type') in starports and self.colonisation.get_build_state(build) == BuildState.COMPLETE]) > 0 else 0
        totals['Completed']['Technology Level'] = max(totals['Completed']['Technology Level'], min)

        return totals


    def _build_summary(self, system:dict) -> list[list]:
        ''' Return the summary section with current system data '''
        totals:dict = self.calc_totals(system)

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


    def update_summary(self, srow:int, sheet:Sheet, system:dict) -> None:
        ''' Update the summary section with current system data '''
        scol = 0
        new = self._build_summary(system)

        for i, x in enumerate(self.summary_rows.keys()):
            for j, details in enumerate(self.summary_cols.values()):
                j += FIRST_SUMMARY_COLUMN
                sheet[i+srow,j].data = ' ' if new[i][j] == 0 else f"{new[i][j]:,}" if details.get('format') == 'int' else new[i][j]

                if new[i][j] and new[i][j] != ' ' and new[i][j] != 0:
                    if details.get('background') in('rwg','gyr'):
                        color = self.get_color(new[i][j], details.get('max', 1), details.get('background'))
                        sheet[i+srow,j+scol].highlight(bg=color)
                        if color != '':
                            sheet[i+srow,j+scol].highlight(bg=color)
                    elif details.get('background') != False:
                        sheet[i+srow,j+scol].highlight(bg=details.get('background'))
                    else:
                        sheet[i+srow,j+scol].highlight(bg=None)


    def get_detail_header(self) -> list[str]:
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
            #if bt == {}:
            #    continue
            row:list = []
            for name, col in self.detail_cols.items():
                match col.get('format'):
                    case 'checkbox':
                        row.append(self.is_build_completed(build) != True and build.get(name, False) == True)

                    case 'int':
                        v = bt.get(name, 0)
                        if name in ['T2', 'T3']:
                            v = self.calc_points(name, builds, i)
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
                            else:
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


    def update_detail(self, srow:int, sheet:Sheet, system:dict) -> None:
        ''' update the details section of the table '''
        new = self._build_detail(system)

        for i, build in enumerate(system.get('Builds', [])):
            for j, details in enumerate(self.detail_cols.values()):
                if i >= len(new) or j >= len(new[i]):
                    continue

                # Set or clear the cell value
                sheet[i+srow,j].data = ' ' if new[i][j] == ' ' else f"{new[i][j]:,}" if details.get('format') == 'int' else new[i][j]

                # Clear the highlight
                if sheet[i+srow,j].data != new[i][j]:
                    sheet[i+srow,j].highlight(bg=None)

                    if details.get('background') in ('rwg', 'gyr') and new[i][j] != ' ':
                        color = self.get_color(new[i][j], details.get('max', 1), details.get('background'))
                        sheet[i+srow,j].highlight(bg=color)

            # Handle build states
            if new[i][5] == BuildState.COMPLETE: # Mark completed builds as readonly
                # Tracking
                sheet[i+srow,0].del_checkbox()
                sheet[i+srow,0].data = ' ⇒' #' 🔍'
                sheet[i+srow,0].align(align='left')
                #sheet[i+srow,0].checkbox(state='disabled'); sheet[i+srow,0].data = ' ';
                sheet[i+srow,0].readonly()

                # Base tyoe
                if new[i][1] != ' ': # Base type has been set so make it readonly
                    sheet[i+srow,1].del_dropdown()
                    sheet[i+srow,1].align(align='left')
                    sheet[i+srow,1].readonly()

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

            # Base tyoe
            if new[i][1] != ' ': # Base type has been set so make it readonly
                sheet[i+srow,1].dropdown(values=[' '] + self.colonisation.get_base_types('All'))
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
                self.update_title(i, system)
                self.update_summary(FIRST_SUMMARY_ROW, self.sheets[i], system)
                self.update_detail(FIRST_BUILD_ROW, self.sheets[i], system)
        except Exception as e:
            Debug.logger.error(f"Error in update_display(): {e}")
            Debug.logger.error(traceback.format_exc())


    def validate_edits(self, event) ->bool|dict:
        ''' Validate edits to the sheet. This just prevents the user from deleting the primary base type. '''
        try:
            row:int = event.row - FIRST_BUILD_ROW; col:inr = event.column; val = event.value
            fields:list = list(self.detail_cols.keys())
            field:str = fields[col]

            if field == 'Base Type' and val == ' ' and row == 0:
                # Don't delete the primary base or let it have no type
                Debug.logger.debug(f"returning none")
                return None
            return event.value

        except Exception as e:
            Debug.logger.error(f"Error in validate_edits(): {e}")
            Debug.logger.error(traceback.format_exc())


    def sheet_modified(self, tabnum:int, event) -> None:
        ''' Handle edits to the sheet. This is where we update the system data. '''
        try:
            sysnum:int = tabnum -1

            if event.eventname == 'select' and len(event.selected) == 6:
                # No editing the summary/headers
                if event.selected.row < FIRST_BUILD_ROW:
                    return

                row:int = event.selected.row - FIRST_BUILD_ROW; col:int = event.selected.column
                fields:list = list(self.detail_cols.keys()); field:str = fields[col]
                systems:list = self.colonisation.get_all_systems()

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
            systems:list = self.colonisation.get_all_systems()
            row:int = event.row - FIRST_BUILD_ROW; val = event.value

            match field:
                case 'Base Type' if val == ' ':
                    # If they set the base type to empty remove the build
                    if row < len(systems[sysnum]['Builds']):
                        self.colonisation.remove_build(systems[sysnum], row)
                    else:
                        systems[sysnum]['Builds'][row][field] = val
                    data = self.sheets[sysnum].data
                    data.pop(row + FIRST_BUILD_ROW)
                    self.sheets[sysnum].set_sheet_data(data)
                    self.config_sheet(self.sheets[sysnum], systems[sysnum])

                case 'Base Type' if val != ' ':
                    Debug.logger.debug(f"Setting base type")

                    if row >= len(systems[sysnum]['Builds']):
                        self.colonisation.add_build(systems[sysnum])
                        systems[sysnum]['Builds'][row][field] = val

                    # Initial cell population
                    data:list = []
                    data.append(self.get_summary_header())
                    data += self._build_summary(systems[sysnum])

                    data.append(self.get_detail_header())
                    data += self._build_detail(systems[sysnum])

                    self.sheets[sysnum].set_sheet_data(data)
                    self.config_sheet(self.sheets[sysnum], systems[sysnum])

                    systems[sysnum]['Builds'][row][field] = val

                case 'Track':
                    # Toggle the tracked status.
                    # Make sure the plan name is up to date.
                    systems[sysnum]['Builds'][row]['Plan'] = systems[sysnum].get('Name')
                    self.colonisation.update_build_tracking(systems[sysnum]['Builds'][row], val)

                case _:
                    # Any other fields, just update the build data
                    systems[sysnum]['Builds'][row][field] = val

            self.colonisation.dirty = True
            self.colonisation.save()
            self.update_display()
            return

        except Exception as e:
            Debug.logger.error(f"Error in sheet_modified(): {e}")
            Debug.logger.error(traceback.format_exc())



    def add_system_dialog(self) -> None:
        ''' Show dialog to add a new system '''
        dialog:tk.Frame = tk.Frame(self.tabbar)
        dialog.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)

        # System name
        ttk.Label(dialog, text=_("Plan Name")+":").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W) # LANG: the name you want to give your plan
        plan_name_var:tk.StringVar = tk.StringVar()
        plan_name_entry:ttk.Entry = ttk.Entry(dialog, textvariable=plan_name_var, width=30)
        plan_name_entry.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)

        # Display name
        syslabel:str = _("System Name") # LANG: Label for the system's name field in the UI
        optionlabel:str = _("optional") # LANG: Indicates the field is optional
        ttk.Label(dialog, text=f"{syslabel} ({optionlabel}):").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        system_name_var:tk.StringVar = tk.StringVar()
        system_name_entry:ttk.Entry = ttk.Entry(dialog, textvariable=system_name_var, width=30)
        system_name_entry.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)

        ttk.Label(dialog, text=_("When planning your system the first base is special, make sure that it is the first on the list.")).grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky=tk.W) # LANG: Notice about the first base being special

        # Buttons
        button_frame:ttk.Frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        # Add button
        add_button:ttk.Button = ttk.Button(
            button_frame,
            text=_("Add"), # LANG: Add/create a new system
            command=lambda: self.add_system(plan_name_var.get(), system_name_var.get())
        )
        add_button.pack(side=tk.LEFT, padx=5)
        self.tabbar.add(dialog, text='+')


    def add_system(self, plan_name:str, system_name:str) -> None:
        ''' Add the new system from the dialog '''
        try:
            if not plan_name:
                messagebox.showerror(_("Error"), _("Plan name is required")) # LANG: Error when no plan name is given
                return

            # Add the system
            system:dict = self.colonisation.add_system(plan_name, system_name)
            if system == False:
                messagebox.showerror(_("Error"), _("Unable to create system")) # LANG: General failure to create system error
                return

            systems:list = self.colonisation.get_all_systems()
            self.create_system_tab(len(systems), system)
            self.update_display()

        except Exception as e:
            Debug.logger.error(f"Error in add_system: {e}")
            Debug.logger.error(traceback.format_exc())
            return


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
            ttk.Label(dialog, text=_("System Name (optional)"+":")).grid(row=1, column=0, padx=10, pady=10, sticky=tk.W) # LANG: Elite dangerous system name
            system_name_var:tk.StringVar = tk.StringVar(value=system.get('StarSystem', ''))
            system_name_entry:ttk.Entry = ttk.Entry(dialog, textvariable=system_name_var, width=30)
            system_name_entry.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)

            # Buttons
            button_frame:ttk.Frame = ttk.Frame(dialog)
            button_frame.grid(row=2, column=0, columnspan=2, pady=10)

            # Rename button
            rename_button:ttk.Button = ttk.Button(
                button_frame,
                text=_("Rename"),
                command=lambda: self.rename_system(tabnum, tab, plan_name_var.get(), system_name_var.get(), dialog)
            ) # LANG: Rename button
            rename_button.pack(side=tk.LEFT, padx=5)

            # Cancel button
            cancel_button:ttk.Button = ttk.Button(
                button_frame,
                text=_("Cancel"),
                command=dialog.destroy
            ) # LANG: Cancel button
            cancel_button.pack(side=tk.LEFT, padx=5)

            # Focus on display name entry
            system_name_entry.focus_set()

        except Exception as e:
            Debug.logger.error(f"Error in rename_system_dialog(): {e}")
            Debug.logger.error(traceback.format_exc())


    def rename_system(self, tabnum:int, tab:ttk.Frame, name:str, sysname:str, dialog:tk.Toplevel) -> None:
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
            Debug.logger.error(f"Error in rename_system_dialog(): {e}")
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


    def close(self):
        ''' Close the window '''
        if self.window:
            self.window.destroy()
            self.window = None

        # UI components
        self.tabbar:ScrollableNotebook = None
        self.sheets:list = []
        self.plan_titles:list = []
        self.colonisation.save()


    def calc_points(self, type:str, builds:list, row:int) -> int:
        ''' Calculate the T2 or T3 base point cost/reward. It depends on the type of base and what's planned/built so far '''
        bt:dict = self.colonisation.get_base_type(builds[row].get('Base Type', ''))
        val:int = bt.get(type+' Reward', 0)
        cost:int = bt.get(type + ' Cost', 0)
        if row > 0:
            if bt.get('Category') == 'Starport': # Increasing point costs for starports
                sp:int = max(self.count_starports(builds[1:row])-1, 0)
                cost += (2 * sp) if type == 'T2' else (cost * sp)
            val -= cost

        return val


    def weight(self, item:tuple, wght:str = 'bold') -> None:
        ''' Set font weight '''
        fnt = tkFont.Font(font=item['font']).actual()
        item.configure(font=(fnt['family'], fnt['size'], wght))


    def count_starports(self, builds:list[dict]) -> int:
        ''' We need to know how many startports have been built already to calculate the T2/T3 cost of the next one. '''
        return len([b for b in builds if b.get('Base Type') in self.colonisation.get_base_types('Initial')])


    def is_build_completed(self, build:list[dict]) -> bool:
        ''' Check if a build is completed '''
        return (self.colonisation.get_build_state(build) == BuildState.COMPLETE)


    def load_legend(self) -> str:
        ''' Load the legend text from the file '''
        # @TODO: Need to modify this to check the user's language and look for a translated file
        file:str = path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)
        lang:str = config.get_str('language')
        if lang and lang != 'en':
            file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, "L10n", f"{lang}.{FILENAME}")

        if not path.exists(file):
            Debug.logger.debug(f"Missing translation {file} for {lang}, using default legend file")
            file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)

        if path.exists(file):
            try:
                with open(file) as file:
                    legend:str = file.read()
                return legend
            except Exception as e:
                Debug.logger.warning(f"Unable to load {file}")
                Debug.logger.error(traceback.format_exc())

        return f"Unable to load {file}"


    def legend_popup(self) -> None:
        ''' Show the legend popup window '''
        try:
            popup:tk.Tk = tk.Tk()

            def leavemini():
                popup.destroy()

            popup.wm_title(_("BGS-Tally - Colonisation Legend")) # LANG: Title of the legend popup window
            popup.wm_attributes('-topmost', True)     # keeps popup above everything until closed.
            popup.wm_attributes('-toolwindow', True) # makes it a tool window
            popup.geometry("600x600")
            popup.config(bd=2, relief=tk.FLAT)
            scr:tk.Scrollbar = tk.Scrollbar(popup, orient=tk.VERTICAL)
            scr.pack(side=tk.RIGHT, fill=tk.Y)

            text:tk.Text = tk.Text(popup, font=FONT_SMALL, yscrollcommand=scr.set)
            text.insert(tk.END, self.load_legend())
            text.pack(fill=tk.BOTH, side=tk.TOP, expand=True, padx=5, pady=5)

        except Exception as e:
            Debug.logger.error(f"Error in colonisation.show(): {e}")
            Debug.logger.error(traceback.format_exc())


    def notes_popup(self, tabnum:int) -> None:
        ''' Show the notes popup window '''
        try:
            def leavemini(system:dict, text:tk.Text):
                if sysnum > len(self.plan_titles):
                    Debug.logger.info(f"Saving notes invalid tab: {tabnum}")
                    return
                notes:str = text.get("1.0", tk.END)
                system['Notes'] = notes
                self.colonisation.save()
                popup.destroy()

            sysnum:int = tabnum -1
            systems:list = self.colonisation.get_all_systems()

            popup:tk.Tk = tk.Tk()
            popup.wm_title(_("BGS-Tally - Colonisation Notes for ") + systems[sysnum].get('Name', '')) # LANG: Title of the notes popup window
            popup.wm_attributes('-topmost', True)     # keeps popup above everything until closed.
            popup.wm_attributes('-toolwindow', True) # makes it a tool window
            popup.geometry("600x600")
            popup.config(bd=2, relief=tk.FLAT)
            scr:tk.Scrollbar = tk.Scrollbar(popup, orient=tk.VERTICAL)
            scr.pack(side=tk.RIGHT, fill=tk.Y)

            text:tk.Text = tk.Text(popup, font=FONT_SMALL, yscrollcommand=scr.set)
            notes:str = systems[sysnum].get('Notes', '')
            text.insert(tk.END, notes)
            text.pack(fill=tk.BOTH, side=tk.TOP, expand=True, padx=5, pady=5)

            # Save button
            save = ttk.Button(popup, text=_("Save"), command=partial(leavemini, systems[sysnum], text)) # LANG: Save notes button
            save.pack(side=tk.RIGHT, padx=5)

        except Exception as e:
            Debug.logger.error(f"Error in notes_popup(): {e}")
            Debug.logger.error(traceback.format_exc())


    def get_color(self, value:int, limit:int = 1, color:str = 'rwg') -> str:
        ''' Get a color based on the value and its range. '''
        try:
            if not isinstance(value, int) and not value.isdigit():
                return '#550055'

            # Scale it to a sensible range
            if limit > 50:
                value = int(value * 50 / limit)
                limit = 50
            value = min(value, limit)

            # Red, White, Green or Green, Yellow, Red
            if color == 'rwg':
                gradient:list = self.create_gradient(limit)
                value:int = min(max(int(value), -limit), limit)
                return gradient[int(value + limit)]
            else:
                # keep it within the limits
                gradient:list = self.create_gradient2(limit)
                if value < len(gradient):
                    return gradient[int(value)]
                else:
                    return ["#ccccff"]

        except Exception as e:
            Debug.logger.error(f"Error in gradient: {e}")
            Debug.logger.error(traceback.format_exc())
            return ["#CCCCCC"]


    def create_gradient(self, steps:int) -> list[str]:
        ''' Generates a list of RGB color tuples representing a gradient from red (-steps) to white (0) to green (+steps) '''
        try:
            hbase:int = 220 # larger = stronger color, less range
            base:int = 190 # smaller = overall darker
            scale:int = 255 - hbase # larger = wider range (light to dark)
            multi:float = 0.01 # Smaller = more intense
            gradient:list = []
            for i in range(steps+1): # zero up (white to green)
                r = max(min(base - (i * scale / steps), 255), 0)
                g = max(min(hbase - (i * scale * multi / steps), 255), 0)
                b = max(min(base - (i * scale / steps), 255), 0)
                gradient.append(f"#{int(r):02x}{int(g):02x}{int(b):02x}")
            for i in range(1, steps+1): # -1 down (white to red)
                r = max(min(hbase - (i * scale * multi / steps), 255), 0)
                g = max(min(base - (i * scale / steps), 255), 0)
                b = max(min(base - (i * scale / steps), 255), 0)
                gradient.insert(0, f"#{int(r):02x}{int(g):02x}{int(b):02x}")

            return gradient

        except Exception as e:
            Debug.logger.error(f"Error in gradient: {e}")
            Debug.logger.error(traceback.format_exc())
            return ["#CCCCCC"]


    def create_gradient2(self, steps:int) -> list[str]:
        ''' Generates a list of RGB color tuples representing a gradient from green (0) to red (steps). '''
        try:
            # Define RGB values
            g = (150, 200, 150) #1
            y = (230, 230, 125) #2
            r = (190, 30, 100) #3

            # Define gradient parameters
            gradient_colors = []

            # Calculate interpolation steps
            r_step_1 = (y[0] - g[0]) / steps
            g_step_1 = (y[1] - g[1]) / steps
            b_step_1 = (y[2] - g[2]) / steps

            r_step_2 = (r[0] - y[0]) / steps
            g_step_2 = (r[1] - y[1]) / steps
            b_step_2 = (r[2] - y[2]) / steps

            # Iterate and interpolate
            for i in range(steps+1):
                # Interpolate between pastel green and yellow
                if i < steps/2:
                    cr = min(max(g[0] + r_step_1 * i, 0), 255)
                    cg = min(max(g[1] + g_step_1 * i, 0), 255)
                    cb = min(max(g[2] + b_step_1 * i, 0), 255)
                else: # Interpolate between yellow and red
                    cr = min(max(y[0] + r_step_2 * (i - steps/2), 0), 255)
                    cg = min(max(y[1] + g_step_2 * (i - steps/2), 0), 255)
                    cb = min(max(y[2] + b_step_2 * (i - steps/2), 0), 255)

                # Add the interpolated color to the gradient
                gradient_colors.append(f"#{int(cr):02x}{int(cg):02x}{int(cb):02x}")

            return gradient_colors

        except Exception as e:
            Debug.logger.error(f"Error in gradient: {e}")
            Debug.logger.error(traceback.format_exc())
            return ["#CCCCCC"]
