import tkinter as tk
import tkinter.font as tkFont
from os import path
from math import ceil
import traceback
from functools import partial
from tkinter import ttk, messagebox, PhotoImage
import webbrowser
from typing import Dict, List, Optional
from thirdparty.ScrollableNotebook import ScrollableNotebook
from thirdparty.tksheet import Sheet

from bgstally.constants import FONT_HEADING_1, COLOUR_HEADING_1, FONT_SMALL, FONT_TEXT, FOLDER_ASSETS, BuildState
from bgstally.debug import Debug
from bgstally.utils import _

FIRST_SUMMARY_INDEX = 1
FIRST_SUMMARY_COLUMN = 3
FIRST_BUILD_INDEX = 4

class ColonisationWindow:
    """
    Window for managing colonisation plans.
    """
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.colonisation = None
        self.window = None
        self.image_tab_complete: PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_enabled.png"))
        self.image_tab_progress: PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_part_enabled.png"))
        self.image_tab_planned: PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_disabled.png"))

        # Table has two sections: summary and builds. This dict defines attributes for each summary column
        self.summary_cols = {
            'Total': {'header': _("Total"), 'background': False, 'format': 'int'},
            'Orbital': {'header': _("Orbital"), 'background': False, 'format': 'int'},
            'Surface': {'header': _("Surface"), 'background': False, 'format': 'int'},
            'T2': {'header': _("T2"), 'background': True, 'format': 'int', 'max': 1},
            'T3': {'header': _("T3"), 'background': True, 'format': 'int', 'max': 1},
            'Cost': {'header': _("Cost"), 'background': False, 'format': 'int'},
            'Trips': {'header': _("Trips"), 'background': False, 'format': 'int'},
            'Pad': {'header': _("Pad"), 'background': False, 'hide': True, 'format': 'hidden'},
            'Facility Economy': {'header': _("Econ"), 'background': False, 'hide': True, 'format': 'hidden'},
            'Pop Inc': {'header': _("Pop Inc"), 'background': True, 'format': 'int', 'max': 20},
            'Pop Max': {'header': _("Pop Max"), 'background': True, 'format': 'int', 'max': 20},
            'Economy Inf': {'header': _("Econ Inf"), 'background': True, 'hide': True},
            'Security': {'header': _("Security"), 'background': True, 'format': 'int', 'max': 20},
            'Technology Level' : {'header': _("Tech Lvl"), 'background': True, 'format': 'int', 'max': 20},
            'Wealth' : {'header': _("Wealth"), 'background': True, 'format': 'int', 'max': 20},
            'Standard of Living' : {'header': _("SoL"), 'background': True, 'format': 'int', 'max': 20},
            'Development Level' : {'header': _("Dev Lvl"), 'background': True, 'format': 'int', 'max': 20}
        }
        self.detail_cols = {
            "Track": {'header': _("Track"), 'background': None, 'format': 'checkbox', 'width':50},
            "Base Type" : {'header': _("Base Type"), 'background': None, 'format': 'dropdown', 'width': 205},
            "Name" : {'header': _("Base Name"), 'background': None, 'format': 'string', 'width': 175},
            "Body": {'header': _("Body"), 'background': None, 'format': 'string', 'width': 100},
            "Prerequisites": {'header': _("Requirements"), 'background': None, 'format': 'string', 'width': 100},
            "State": {'header': _("State"), 'background': None, 'format': 'string', 'width': 100},
            "T2": {'header': _("T2"), 'background': True, 'format': 'int', 'max':1, 'width': 30},
            "T3": {'header': _("T3"), 'background': True, 'format': 'int', 'min':-1, 'max':1, 'width': 30},
            "Cost": {'header': _("Cost"), 'background': False, 'format': 'int', 'max':200000, 'width': 75},
            "Trips":{'header': _("Trips"), 'background': False, 'format': 'int', 'max':100, 'width': 40},
            "Pad": {'header': _("Pad"), 'background': None, 'format': 'string', 'width': 55},
            "Facility Economy": {'header': _("Economy"), 'background': None, 'format': 'string', 'width': 80},
            "Pop Inc": {'header': _("Pop Inc"), 'background': True, 'format': 'int', 'max':5, 'width': 60},
            "Pop Max": {'header': _("Pop Max"), 'background': True, 'format': 'int', 'max':5, 'width': 60},
            "Economy Influence": {'header': _("Econ Inf"), 'background': None, 'format': 'string', 'width': 80},
            "Security": {'header': _("Security"), 'background': True, 'format': 'int', 'max':8, 'width': 60},
            "Technology Level": {'header': _("Tech Lvl"), 'background': True, 'format': 'int', 'max':8, 'width': 60},
            "Wealth": {'header': _("Wealth"), 'background': True, 'format': 'int', 'max':8, 'width': 60},
            "Standard of Living": {'header': _("SoL"), 'background': True, 'format': 'int', 'max':8, 'width': 60},
            "Development Level": {'header': _("Dev Lvl"), 'background': True, 'format': 'int', 'max':8, 'width': 60}
        }
        self.checkall = None
        self.current_system = None
        self.current_tab = 0

        # UI components
        self.tabbar = None
        self.tabs = []
        self.sheets = []
        self.content_frames = []
        self.plan_titles = []


    def show(self) -> None:
        """
        Create the colonisation window
        """
        try:
            if self.window is not None and self.window.winfo_exists():
                self.window.lift()
                return
            self.colonisation = self.bgstally.colonisation
            self.window = tk.Toplevel(self.bgstally.ui.frame)
            self.window.title(_("Elite Dangerous Colonisation"))
            self.window.minsize(400, 100)
            self.window.geometry("1200x600")
            self.window.protocol("WM_DELETE_WINDOW", self.close)

            self.create_frames()    # Create main frames
            self.update_display()   # Populate them

        except Exception as e:
            Debug.logger.error(f"Error in colonisation.show(): {e}")
            Debug.logger.error(traceback.format_exc())
            messagebox.showerror(_("Error"), f"Error in colonisation.show(): {e}\n{traceback.format_exc()}")return


    def create_frames(self) -> None:
        """
        Create the system tabs
        """
        try:
            # Create system tabs notebook
            self.tabbar = ScrollableNotebook(self.window, wheelscroll=True, tabmenu=True)
            self.tabbar.pack(fill=tk.BOTH, side=tk.TOP, expand=True, padx=5, pady=5)
            self.add_system_dialog()

            # Add tabs for each system
            systems = self.colonisation.get_all_systems()
            if len(systems) == 0:
                return

            for i, system in enumerate(systems):
                # Create a frame for the sytem
                self.create_system_tab(i, system)

            # Select the first tab
            if i > 0:
                self.tabbar.select(1)
                self.current_tab = 1
                self.current_system = self.colonisation.get_system('Name', systems[0]['Name'])

        except Exception as e:
            Debug.logger.error(f"Error in colonisation.show(): {e}")
            Debug.logger.error(traceback.format_exc())


    def create_system_tab(self, tabnum:int, system: Dict) -> None:
        """
        Create the frame, title, and sheet for a system
        """
        tab = ttk.Frame(self.tabbar)
        tab.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)

        self.create_title_frame(tabnum, tab)
        self.create_table_frame(tabnum, tab, system)
        self.tabbar.add(tab, text=system['Name'], compound='right', image=self.image_tab_planned)
        self.set_system_progress(tabnum, system)


    def set_system_progress(self, tabnum:int, system:Dict) -> None:
        """
        Update the tab image based on the system's progress
        """
        state = BuildState.COMPLETE
        for b in system['Builds']:
            if b.get('State') == BuildState.PLANNED and state != BuildState.PROGRESS:
                state = BuildState.PLANNED
            if b.get('State') == BuildState.PROGRESS:
                state = BuildState.PROGRESS

        match state:
            case BuildState.COMPLETE:
                Debug.logger.debug(f"{tabnum} {state} {self.image_tab_complete}")
                self.tabbar.notebookTab.tab(tabnum+1, image=self.image_tab_complete)
            case BuildState.PROGRESS:
                Debug.logger.debug(f"{tabnum} {state} {self.image_tab_progress}")
                self.tabbar.notebookTab.tab(tabnum+1, image=self.image_tab_progress)
            case BuildState.PLANNED:
                self.tabbar.notebookTab.tab(tabnum+1, image=self.image_tab_planned)
                Debug.logger.debug(f"{tabnum} {state} {self.image_tab_planned}")


    def create_title_frame(self, tabnum:int, tab:ttk.Frame) -> None:
        """
        Create the title frame with system name and tick info
        """
    
        #Debug.logger.debug(f"Creating title frame for tab {tabnum}")
        title_frame = ttk.Frame(tab, style="Title.TFrame")
        title_frame.pack(fill=tk.X, padx=0, pady=(0, 5))

        # Configure style for title frame
        style = ttk.Style()
        style.configure("Title.TFrame")

        # System name label
        while len(self.plan_titles) <= tabnum:
            self.plan_titles.append({})

        name_label = ttk.Label(title_frame, text="", font=FONT_HEADING_1, foreground=COLOUR_HEADING_1)
        name_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.plan_titles[tabnum]['Name'] = name_label

        sys_label = ttk.Label(title_frame, text="")
        sys_label.pack(side=tk.LEFT, padx=10, pady=5)
        self.weight(sys_label)

        self.plan_titles[tabnum]['System'] = sys_label

        inara = ttk.Label(
            title_frame,
            text="Inara ⤴",
            font=FONT_TEXT,
            foreground="blue",
            cursor="hand2"
        )
        inara.pack(side=tk.LEFT, padx=10, pady=5)
        inara.bind("<Button-1>", partial(self.inara_click, tabnum))
        self.plan_titles[tabnum]['Inara'] = inara

        btn = ttk.Button(title_frame, text=_("Delete"), command=lambda: self.delete_system(tabnum, tab))
        btn.pack(side=tk.RIGHT, padx=10, pady=5)


    def inara_click(event, tabnum) -> None:
        '''
        Execute the click event for the Inara link
        '''
        try:
            if tabnum >= len(self.plan_titles):
                Debug.logger.info(f"on_inara_click invalid tab: {tab}")
                return
            star = self.plan_titles[tab]['System']['text']
            webbrowser.open(f"https://inara.cz/elite/starsystem/search/?search={star}")
            
        except Exception as e:
            Debug.logger.error(f"Error in create_title_frame() {e}")
            Debug.logger.error(traceback.format_exc())


    def create_table_frame(self, tabnum:int, tab:ttk.Frame, system:Dict) -> None:
        """
        Create a unified table frame with both summary and builds in a single scrollable area
        """
        # Main table frame
        table_frame = ttk.Frame(tab)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Configure the table frame to resize with the window
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        sheet:Sheet = Sheet(table_frame, show_row_index=False, cell_auto_resize_enabled=True, height=600,
                            show_horizontal_grid=True, show_vertical_grid=False, show_top_left=False,
                            align="center", table_selected_cells_border_fg=None, show_dropdown_borders=False,
                            empty_vertical=15, empty_horizontal=0, font=FONT_SMALL, arrow_key_down_right_scroll_page=True,
                            show_header=False, set_all_heights_and_widths=True, default_row_height=21)
        sheet.pack(fill=tk.BOTH, padx=0, pady=(0, 5))

        # Initial cell population
        data = []
        h = self.get_summary_header()
        data.append(h)
        data += self.get_summary(system)
        data.append(self.get_detail_header())
        data += self.get_detail(system)
        sheet.set_sheet_data(data)
        self.config_sheet(sheet)
        sheet.enable_bindings('single_select', 'edit_cell', 'up', 'down', 'left', 'right', 'copy', 'paste')
        sheet.extra_bindings('all_modified_events', func=partial(self.sheet_modified, tabnum))

        if len(self.sheets) <= tabnum:
            self.sheets.append(sheet)
        else:
            self.sheets[tabnum] = sheet


    def _on_canvas_configure(self, event):
        """
        Handle canvas resize event to update the window width
        """
        for frame in self.content_frames:
            frame.configure(width=event.width, height=event.height)


    def update_title(self, t, system):
            '''
            Update title with both display name and actual system name
            '''
            name = system.get('Name', '')
            sysname = system.get('StarSystem', '')
            if name == '': name = sysname
            if sysname == '': sysname = '(Unknown)'

            self.plan_titles[t]['Name']['text'] = name
            self.plan_titles[t]['System']['text'] = sysname

            # Hide the system name if it is the same as the display name
            if name == sysname:
                self.plan_titles[t]['System'].pack_forget()
            else:
                self.plan_titles[t]['System'].pack()

            if sysname == '(Unknown)':
                self.plan_titles[t]['System'].pack_forget()
                self.plan_titles[t]['Inara'].pack_forget()
            else:
                self.plan_titles[t]['Inara'].pack()


    def config_sheet(self, sheet:Sheet) -> None:
        '''
        Initial sheet configuration.
        '''
        # Column widths
        for i, (name, value) in enumerate(self.detail_cols.items()):
            sheet.column_width(i, value.get('width', 100))

        # header lines
        sheet['1'].highlight(bg='lightgrey')
        sheet['4'].highlight(bg='lightgrey')

        # Tracking checkboxes
        sheet['A5:A'].checkbox(state='normal', checked=False)

        # Base types
        sheet['B5'].dropdown(values=[' '] + self.colonisation.get_base_types('Initial'))
        sheet['B6:B'].dropdown(values=[' '] + self.colonisation.get_base_types('All'))

        # Make the sections readonly that users can't edit.
        s3 = sheet.span('A1:4', type_='readonly')
        sheet.named_span(s3)
        s4 = sheet.span('E4:T', type_='readonly')
        sheet.named_span(s4)

        # types, names and prerequisites left.
        sheet['B5:C'].align(align='left')
        sheet['E5:E'].align(align='left')


    def get_summary_header(self):
        cols: list = [' ', ' ', ' ']
        for c, v in self.summary_cols.items():
            cols.append(v.get('header', c) if v.get('hide') != True else ' ')
        return cols


    def calc_totals(self, system:Dict) -> Dict[str, Dict[str, int]]:
        '''
        Build a summary of the system's builds and status.
        '''
        
        totals = {'Planned': {}, 'Completed': {}}
        builds = system.get('Builds', [])
        required = self.colonisation.get_required(builds)
        for name, col in self.summary_cols.items():
            if col.get('hide') == True:
                totals['Planned'][name] = ' '
                totals['Completed'][name] = ' '
                continue

            totals['Planned'][name] = 0
            totals['Completed'][name] = 0
            # Calculate summary values
            for row, build in enumerate(builds):
                bt = self.colonisation.get_base_type(build.get('Base Type', ''))
                match name:
                    case 'Total':
                        totals['Planned'][name] += 1
                        totals['Completed'][name] += 1 if self.is_build_completed(build) else 0
                    case 'Orbital'|'Surface':
                        if bt.get('Location') == name:
                            totals['Planned'][name] += 1
                            totals['Completed'][name] += 1 if self.is_build_completed(build) else 0
                    case 'T2' | 'T3':
                        v = self.calc_points(name, builds, row)
                        totals['Planned'][name] += v
                        totals['Completed'][name] += v if self.is_build_completed(build) else 0
                    case 'Cost':
                        if row >= len(required):
                            Debug.logger.debug(f" No required commodities for summary {row} {build}")
                            continue
                        res = required[row]
                        res = sum(res.values())
                        totals['Planned'][name] += res
                        totals['Completed'][name] += res if self.is_build_completed(build) else 0
                    case 'Trips':
                        if row >= len(required):
                            continue
                        res = required[row]
                        trips = ceil(sum(res.values()) / self.colonisation.cargo_capacity)
                        totals['Planned'][name] += trips
                        totals['Completed'][name] += trips if self.is_build_completed(build) else 0
                    case _ if col.get('format') == 'int':
                        totals['Planned'][name] += bt.get(name, 0)
                        totals['Completed'][name] += bt.get(name, 0) if self.is_build_completed(build) else 0

        return totals


    def get_summary(self, system:Dict) -> List[List[Optional[str]]]:
        """
        Return the summary section with current system data
        """
        totals = self.calc_totals(system)

        # Update the values in the cells.
        summary:list = []
        for i, r in enumerate(['Planned', 'Completed']):
            row:list = [' ', ' ', r]
            for (name, col) in self.summary_cols.items():
                if col.get('hide', False) == True:
                    row.append(' ')
                    continue
                row.append(totals[r].get(name, 0))
            summary.append(row)

        return summary


    def update_summary(self, srow:int, tab:ttk.Frame, system:Dict) -> None:
        '''
        Update the summary section with current system data
        '''
        scol = 0
        new = self.get_summary(system)

        for i in enumerate(['Completed', 'Planned']):
            for j, details in enumerate(self.summary_cols.values()):
                j += FIRST_SUMMARY_COLUMN
                tab[i+srow,j].data = ' ' if new[i][j] == 0 else f"{new[i][j]:,}" if details.get('format') == 'int' else new[i][j]

                if new[i][j] and new[i][j] != ' ' and new[i][j] != 0 and details.get('background') == True:
                    color = self.get_color(new[i][j], details.get('max', 1))
                    tab[i+srow,j+scol].highlight(bg=color)
                    if color != '':
                        tab[i+srow,j+scol].highlight(bg=color)
                else:
                    tab[i+srow,j+scol].highlight(bg=None)


    def get_detail_header(self) -> List[str]:
        cols: list = []
        for c, v in self.detail_cols.items():
            cols.append(v.get('header', c) if v.get('hide') != True else ' ')
        return cols


    def get_detail(self, system:Dict) -> List[List[Optional[str]]]:
        '''
        Build a data cube of info to update the table
        '''
        details:list = []
        builds = system.get('Builds', [])
        reqs = self.colonisation.get_required(builds)
        delivs = self.colonisation.get_delivered(builds)
        
        for i, build in enumerate(builds):
            bt = self.colonisation.get_base_type(build.get('Base Type', ' '))
            row:list = []
            for name, col in self.detail_cols.items():
                match col.get('format'):
                    case 'checkbox':
                        check = self.is_build_completed(build) != True and build.get(name, False) == True
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
                            if build.get('State', '') == BuildState.PROGRESS and i < len(reqs):
                                req = sum(reqs[i].values())
                                deliv = sum(delivs[i].values())
                                row.append(f"{int(deliv * 100 / (req+deliv))}%")
                            elif build.get('State', '') == BuildState.COMPLETE:
                                row.append('Complete')
                            else:
                                row.append('Planned')
                            continue
                        if name == 'Body' and build.get('Body', None) != None and system.get('StarSystem', None) != None:
                            row.append(build.get('Body').replace(system.get('StarSystem') + ' ', ''))
                            continue

                        row.append(build.get(name) if build.get(name, ' ') != ' ' else bt.get(name, ' '))

            details.append(row)

        # Is the last line an uncategorized base? If not add another
        if details[-1][1] != ' ':
            row:list = [' '] * (len(list(self.detail_cols.keys())) -1)
            details.append(row)

        return details


    def update_detail(self, srow:int, tab:ttk.Frame, system:Dict) -> None:
        new = self.get_detail(system)

        for i in enumerate(system.get('Builds', [])):
            for j, details in enumerate(self.detail_cols.values()):
                if i >= len(new) or j >= len(new[i]):
                    continue

                # Set or clear the cell value
                tab[i+srow,j].data = ' ' if new[i][j] == ' ' else f"{new[i][j]:,}" if details.get('format') == 'int' else new[i][j]
                
                # Clear the highlight
                if tab[i+srow,j].data != new[i][j]:
                    tab[i+srow,j].highlight(bg=None)

                    if details.get('background') == True and new[i][j] != 0:
                        color = self.get_color(new[i][j], details.get('max', 1))
                        tab[i+srow,j].highlight(bg=color)

                # Mark completed builds as readonly
                if j == 5 and new[i][j] == BuildState.COMPLETE:
                    tab[i+srow,0].del_checkbox(); tab[i+srow,0].data = ' '; tab[i+srow,0].readonly()

                    if new[i][1] != ' ': # Base type has been set so make it readonly
                        tab[i+srow,1].readonly()
                        tab[i+srow,1].del_dropdown()
                        tab[i+srow,1].align(align='left')

                    tab[i+srow,2].readonly()

        if len(tab.data) > len(system.get('Builds', [])) + FIRST_BUILD_INDEX + 1:
            Debug.logger.debug(f"Too many build rows in the sheet {len(tab.data)} {len(system.get('Builds', [])) + FIRST_BUILD_INDEX + 1}")


    def update_display(self) -> None:
        '''
        Update the display with current system data
        '''
        systems = self.colonisation.get_all_systems()
        for i, tab in enumerate(self.sheets):
            system = systems[i]
            Debug.logger.debug(f"Updating system {i} {system.get('Name')}")
            self.update_title(i, system)
            self.update_summary(FIRST_SUMMARY_INDEX, self.sheets[i], system)
            self.update_detail(FIRST_BUILD_INDEX, self.sheets[i], system)

        return


    def validate_edits(self, event) -> Optional[bool]:
        '''
        Validate edits to the sheet. This is isn't doing anything right now but maybe it will in the future.
        '''
        try:
            return event.value
            #if event.eventname == 'edit_table':
                # Validation here?
                # Return None to prevent invalid input
            #    return True

            #return True

        except Exception as e:
            Debug.logger.error(f"Error in validate_edits(): {e}")
            Debug.logger.error(traceback.format_exc())


    def sheet_modified(self, tabnum:int, event) -> None:
        try:
            # We only deal with edits.
            if not event.eventname.endswith('edit_table'):
                return
            
            row = event.row - FIRST_BUILD_INDEX; col = event.column; val = event.value

            Debug.logger.debug(f"Changed {tabnum} {row} {col}: {val} ")
            fields = list(self.detail_cols.keys())
            field = fields[col]

            # If they set the base type to empty remove the build
            if field == 'Base Type' and val == ' ':
                Debug.logger.debug(f" Removing build {row} from system {tabnum}")
                self.colonisation.remove_build(self.colonisation.systems[tabnum], row)
                data = self.sheets[tabnum].data
                data.pop(row + FIRST_BUILD_INDEX)
                self.sheets[tabnum].set_sheet_data(data)
                self.config_sheet(self.sheets[tabnum])
                self.update_display()
                return

            # Toggle the tracked status.
            if field == 'Track':
                # Make sure the plan name is up to date.
                self.colonisation.systems[tabnum]['Builds'][row]['Plan'] = self.colonisation.systems[tabnum].get('Name')
                self.colonisation.update_build_tracking(self.colonisation.systems[tabnum]['Builds'][row], val)
                self.update_display()
                return

            if row >= len(self.colonisation.systems[tabnum]['Builds']):
                self.colonisation.add_build(self.colonisation.systems[tabnum])
                Debug.logger.debug(f"Added build")

            # Any other fields, just update the build data and market it as dirty.
            Debug.logger.debug(f"Updated {row} {field} to {val}")
            self.colonisation.systems[tabnum]['Builds'][row][field] = val
            self.colonisation.dirty = True            
            self.update_display()

        except Exception as e:
            Debug.logger.error(f"Error in sheet_modified(): {e}")
            Debug.logger.error(traceback.format_exc())


    def add_system_dialog(self) -> None:
        """
        Show dialog to add a new system
        """
        dialog = tk.Frame(self.tabbar)
        dialog.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)

        # System name
        ttk.Label(dialog, text=_("Plan Name:")).grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        plan_name_var = tk.StringVar()
        plan_name_entry = ttk.Entry(dialog, textvariable=plan_name_var, width=30)
        plan_name_entry.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)

        # Display name
        ttk.Label(dialog, text=_("System Name (optional):")).grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        system_name_var = tk.StringVar()
        system_name_entry = ttk.Entry(dialog, textvariable=system_name_var, width=30)
        system_name_entry.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        # Add button
        add_button = ttk.Button(
            button_frame,
            text=_("Add"),
            command=lambda: self.add_system(plan_name_var.get(), system_name_var.get())
        )
        add_button.pack(side=tk.LEFT, padx=5)
        self.tabbar.add(dialog, text='+')


    def add_system(self, plan_name: str, system_name: str) -> None:
        """
        Add a new system
        """
        try:
            if not plan_name:
                messagebox.showerror(_("Error"), _("Plan name is required"))
                return

            Debug.logger.debug(f"Adding system {plan_name} {system_name}")

            # Add the system
            system = self.colonisation.add_system(plan_name, system_name)
            if system == False:
                messagebox.showerror(_("Error"), f"Unable to create system.")
                return

            systems = self.colonisation.get_all_systems()
            self.create_system_tab(system, len(systems)-1)
            self.update_display()

        except Exception as e:
            Debug.logger.error(f"Error in add_system: {e}")
            Debug.logger.error(traceback.format_exc())
            return


    def rename_system_dialog(self):
        """
        @TODO: Implement this.
        Show dialog to rename a system
        """
        if not self.current_system:
            return

        dialog = tk.Toplevel(self.window)
        dialog.title(_("Rename System"))
        dialog.geometry("400x150")
        dialog.transient(self.window)
        dialog.grab_set()

        # Display name
        ttk.Label(dialog, text=_("Display Name:")).grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        system_name_var = tk.StringVar(value=self.current_system.get('Name', ''))
        system_name_entry = ttk.Entry(dialog, textvariable=system_name_var, width=30)
        system_name_entry.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)

        # Rename button
        rename_button = ttk.Button(
            button_frame,
            text=_("Rename"),
            command=lambda: self.rename_system(system_name_var.get(), dialog)
        )
        rename_button.pack(side=tk.LEFT, padx=5)

        # Cancel button
        cancel_button = ttk.Button(
            button_frame,
            text=_("Cancel"),
            command=dialog.destroy
        )
        cancel_button.pack(side=tk.LEFT, padx=5)

        # Focus on display name entry
        system_name_entry.focus_set()


    def rename_system(self, system_name:str, dialog) -> None:
        """
        Rename a system

        Args:
            system_name: The new display name
            dialog: The dialog to close
        """
        if not self.get_current_system():
            return

        # Update the system
        self.current_system['Name'] = system_name

        # Close the dialog
        dialog.destroy()

        # Update the display
        self.update_display()

        # Save changes
        self.colonisation.dirty = True
        self.colonisation.save()


    def delete_system(self, tabnum:int, tab: ttk.Frame) -> None:
        """
        Remove the current system
        """
        try:
            # Confirm removal
            if not messagebox.askyesno(
                _("Confirm Removal"),
                _("Are you sure you want to remove this system?")
            ):
                return

            if tabnum >= len(self.colonisation.get_all_systems()):
                Debug.logger.info(f"Invalid tab {tabnum}")

            Debug.logger.info(f"Deleting system {tabnum}")
            tabs = self.tabbar.tabs()
            self.tabbar.forget(tabs[tabnum+1]) # +1 for the add tab
            self.colonisation.remove_system(tabnum)

            self.update_display()

        except Exception as e:
            Debug.logger.error(f"Error in delete_system(): {e}")
            Debug.logger.error(traceback.format_exc())


    def close(self):
        """
        Close the window
        """
        if self.window:
            self.window.destroy()
            self.window = None

        self.current_system = None
        self.current_tab = 0
        # UI components
        self.tabbar = None
        self.system_tabs = []
        self.content_frames = []
        self.plan_titles = []
        self.track_all_vars = []

        # Data storage
        self.planned_labels = []
        self.progress_labels = []


    def calc_points(self, type, builds, row):
        '''
        Calculate the T2 or T3 base point cost/reward. It depends on the type of base and what's planned/built so far
        '''
        bt = self.colonisation.get_base_type(builds[row].get('Base Type', ''))
        val = bt.get(type+' Reward', 0)
        cost = bt.get(type + ' Cost', 0)
        if row > 0:
            if bt.get('Category') == 'Starport': # Increasing point costs for starports
                sp = self.count_starports(builds[1:row])
                cost += (2 * sp) if type == 'T2' else (cost * sp)
            val -= cost
        #Debug.logger.debug(f"{build.get('Base Type')} {name} row {i} reward {bt.get(name+' Reward', 0)} sp {sp} cost {bt.get(name+' Cost', 0)} actual {cost} {v}")

        return val

    def weight(self, item, w='bold'):
        '''
        Set font weight
        '''
        fnt = tkFont.Font(font=item['font']).actual()
        item.configure(font=(fnt['family'], fnt['size'], w))


    def get_color(self, value:int, limit:int = 1):
        """
        Get a color based on the value and its range.

        Args:
            value: The value to color. Positive will be green, negative red.
            limit: The size of the range (technically half as we do negative & positive).

        Returns:
            A hex color string
        """
        if not isinstance(value, int) and not value.isdigit():
            return '#550055'

        gradient = self.create_gradient(limit)
        # keep it within the limits
        value = min(max(int(value), int(-limit)), int(limit))

        #Debug.logger.debug(f"value: {value} range: {limit} index {int(value + limit)} color {gradient[index]}")
        return gradient[int(value + limit)]


    def create_gradient(self, steps):
        """
        Generates a list of RGB color tuples representing a gradient from green to red.

        Args:
            steps: The number of steps in the gradient.

        Returns:
            A list of RGB color tuples.
        """
        try:
            base = 235 # smaller = overall darker
            scale = 70 # larger = wider range (light to dark)
            multi = 0.01 # Smaller = more intense
            gradient = []
            for i in range(steps+1): # zero up
                r = base - (i * scale / steps); g = base - (i * scale * multi / steps); b = base - (i * scale / steps)
                gradient.append(f"#{int(r):02x}{int(g):02x}{int(b):02x}")
            for i in range(1, steps+1): # -1 down
                r = base - (i * scale * multi / steps); g = base - (i * scale / steps); b = base - (i * scale / steps)
                gradient.insert(0, f"#{int(r):02x}{int(g):02x}{int(b):02x}")

            return gradient

        except Exception as e:
            Debug.logger.error(f"Error in gradient: {e}")
            Debug.logger.error(traceback.format_exc())
            return ["#CCCCCC"]


    def count_starports(self, builds:List[Dict]) -> int:
        '''
        We need to know how many startports have been built already to calculate the T2/T3 cost of the next one.
        '''
        i = 0
        starports = self.colonisation.get_base_types('Initial')
        for b in builds:
            i += 1 if b.get('Base Type') in starports else 0

        return i


    def is_build_completed(self, build:List[Dict]) -> bool:
        """
        Check if a build is completed
        """

        # If it has a state setting we're golden.
        if build.get('State', '') != '':
            return state == BuildState.COMPLETE

        # Not state so figure it out from its progress.
        market_id = build.get('MarketID')
        if market_id:
            build['State'] = BuildState.PROGRESS
            for depot in self.colonisation.progress:
                if depot.get('MarketID') == market_id and depot.get('ConstructionComplete', False):
                    build['State'] = BuildState.COMPLETE
        else:
            build['State'] = BuildState.PLANNED

        return build['State'] == BuildState.COMPLETE
