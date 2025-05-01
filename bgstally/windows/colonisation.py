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
    Window for managing Elite Dangerous colonisation
    """
    def __init__(self, bgstally):
        """
        Initialize the colonisation window

        Args:
            parent: The parent window
            colonisation: The Colonisation instance
        """
        self.bgstally = bgstally
        self.colonisation = None
        self.window = None
        self.image_tab_tracked: PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_enabled.png"))
        self.image_tab_part_tracked: PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_part_enabled.png"))
        self.image_tab_untracked: PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_disabled.png"))

        self.summary_cols = {
            'Total': {'header': 'Total', 'background': False, 'format': 'int'},
            'Orbital': {'header': 'Orbital', 'background': False, 'format': 'int'},
            'Surface': {'header': 'Surface', 'background': False, 'format': 'int'},
            'T2': {'header': 'T2', 'background': True, 'format': 'int', 'min': -1, 'max': 1},
            'T3': {'header': 'T3', 'background': True, 'format': 'int', 'min': -1, 'max': 1},
            'Cost': {'header': 'Cost', 'background': False, 'format': 'int'},
            'Trips': {'header': 'Trips', 'background': False, 'format': 'int'},
            'Pad': {'header': 'Pad', 'background': False, 'hide': True, 'format': 'hidden'},
            'Economy': {'header': 'Econ', 'background': False, 'hide': True, 'format': 'hidden'},
            'Pop Inc': {'header': 'Pop Inc', 'background': True, 'format': 'int', 'min': -20, 'max': 20},
            'Pop Max': {'header': 'Pop Max', 'background': True, 'format': 'int', 'min': -20, 'max': 20},
            'Economy Inf': {'header': 'Econ Inf', 'background': True, 'hide': True},
            'Security': {'header': 'Security', 'background': True, 'format': 'int', 'min': -20, 'max': 20},
            'Technology Level' : {'header': 'Tech Lvl', 'background': True, 'format': 'int', 'min': -20, 'max': 20},
            'Wealth' : {'header': 'Wealth', 'background': True, 'format': 'int', 'min': -20, 'max': 20},
            'Standard of Living' : {'header': 'SoL', 'background': True, 'format': 'int', 'min': -20, 'max': 20},
            'Development Level' : {'header': 'Dev Lvl', 'background': True, 'format': 'int', 'min': -20, 'max': 20}
        }
        self.detail_cols = {
            "Track": {'header': 'Track', 'background': None, 'format': 'checkbox', 'width':50},
            "Base Type" : {'header': 'Base Type', 'background': None, 'format': 'dropdown', 'width': 205},
            "Name" : {'header': 'Base Name', 'background': None, 'format': 'string', 'width': 175},
            "Body": {'header': 'Body', 'background': None, 'format': 'string', 'width': 100},
            "Prerequisites": {'header': 'Requirements', 'background': None, 'format': 'string', 'width': 100},
            "State": {'header': 'State', 'background': None, 'format': 'string', 'width': 100},
            "T2": {'header': 'T2', 'background': True, 'format': 'int', 'min':-1, 'max':1, 'width': 30},
            "T3": {'header': 'T3', 'background': True, 'format': 'int', 'min':-1, 'max':1, 'width': 30},
            "Cost": {'header': 'Cost', 'background': False, 'format': 'int', 'min':0, 'max':200000, 'width': 75},
            "Trips":{'header': 'Trips', 'background': False, 'format': 'int', 'min':0, 'max':100, 'width': 40},
            "Pad": {'header': 'Pad', 'background': None, 'format': 'string', 'width': 40},
            "Economy": {'header': 'Economy', 'background': None, 'format': 'string', 'width': 75},
            "Pop Inc": {'header': 'Pop Inc', 'background': True, 'format': 'int', 'min':0, 'max':10, 'width': 75},
            "Pop Max": {'header': 'Pop Max', 'background': True, 'format': 'int', 'min':0, 'max':10, 'width': 75},
            "Econony Inf": {'header': 'Econ Inf', 'background': None, 'format': 'string', 'width': 75},
            "Security": {'header': 'Security', 'background': True, 'format': 'int', 'min':-10, 'max':10, 'width': 75},
            "Technology Level": {'header': 'Tech Lvl', 'background': True, 'format': 'int', 'min':-10, 'max':10, 'width': 75},
            "Wealth": {'header': 'Wealth', 'background': True, 'format': 'int', 'min':-10, 'max':10, 'width': 75},
            "Standard of Living": {'header': 'SoL', 'background': True, 'format': 'int', 'min':-10, 'max':10, 'width': 75},
            "Development Level": {'header': 'Dev Lvl', 'background': True, 'format': 'int', 'min':-10, 'max':10, 'width': 75}
        }
        self.checkall = None
        self.current_system = None
        self.current_tab = 0

        # UI components
        self.tabbar = None
        self.sheets = []
        self.content_frames = []
        self.plan_titles = []

    def show(self):
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

            # Create main frames
            self.create_frames()
            self.update_display()

        except Exception as e:
            Debug.logger.error(f"Error in colonisation.show(): {e}")
            Debug.logger.error(traceback.format_exc())
            messagebox.showerror(_("Error"), f"Error in colonisation.show(): {e}\n{traceback.format_exc()}")
            return

    def create_frames(self):
        """
        Create the header frame with system tabs
        """
        try:
            #Debug.logger.debug("Creating main frames")

            # Create system tabs notebook
            self.tabbar = ScrollableNotebook(self.window, wheelscroll=True, tabmenu=True)
            self.tabbar.pack(fill=tk.BOTH, side=tk.TOP, expand=True, padx=5, pady=5)
            self.add_system_dialog()

            #Debug.logger.debug("Creating tabs for systems")

            # Add tabs for each system
            systems = self.colonisation.get_all_systems()

            if len(systems) == 0:
                return

            for i, system in enumerate(systems):
                # Create a frame for the sytem tab
                self.create_system_tab(system, i)

            if i > 0:
                #Debug.logger.debug(f"Setting current tab to {self.current_tab}")
                self.tabbar.select(1)
                self.current_tab = 1
                self.current_system = self.colonisation.get_system('Name', systems[0]['Name'])

            #Debug.logger.debug(f"Created {i} system tabs {self.tabbar.tabs()}")

        except Exception as e:
            Debug.logger.error(f"Error in colonisation.show(): {e}")
            Debug.logger.error(traceback.format_exc())


    def create_system_tab(self, system, tabnum):
        tracking_status = self.colonisation.get_system_tracking(system)
        tab = ttk.Frame(self.tabbar)
        tab.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)

        self.create_title_frame(tab, tabnum)
        self.create_table_frame(tab, tabnum, system)

        Debug.logger.debug(f"Creating tab {tabnum+1} {system.get('Name')} {system.get('StarSystem')}")
        self.tabbar.add(tab, text=system['Name'], compound='right', image=self.image_tab_tracked if tracking_status == "All" else self.image_tab_part_tracked if tracking_status == "Partial" else self.image_tab_untracked)

    def create_title_frame(self, tab, tabnum):
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
        def inara_click(event, tab=tabnum):
            try:
                if tab >= len(self.plan_titles):
                    Debug.logger.info(f"on_inara_click invalid tab: {tab}")
                    return
                star = self.plan_titles[tab]['System']['text']
                url = f"https://inara.cz/elite/starsystem/search/?search={star}"
                Debug.logger.debug(f"Opening star {tab} [{star}]")
                webbrowser.open(url)
            except Exception as e:
                Debug.logger.error(f"Error in create_title_frame() {e}")
                Debug.logger.error(traceback.format_exc())

        inara.bind("<Button-1>", inara_click)
        self.plan_titles[tabnum]['Inara'] = inara

        btn = ttk.Button(title_frame, text=_("Delete"), command=lambda: self.delete_system(tab, tabnum))
        btn.pack(side=tk.RIGHT, padx=10, pady=5)


    def create_table_frame(self, tab_frame, tabnum, system):
        """
        Create a unified table frame with both summary and builds in a single scrollable area
        """
        # Main table frame
        table_frame = ttk.Frame(tab_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Configure the table frame to resize with the window
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Hack to figure out the default font.
        #tmp = ttk.Label(table_frame)
        #fnt = tkFont.Font(font=tmp['font']).actual()
        #bld = (fnt['family'], fnt['size'], 'bold')

        Debug.logger.debug("Creating tab {tabnum}")
        sheet:Sheet = Sheet(table_frame, show_row_index=False, cell_auto_resize_enabled=True, height=600,
                            show_horizontal_grid=True, show_vertical_grid=False, show_top_left=False,
                            align="center", table_selected_cells_border_fg=None, show_dropdown_borders=False,
                            empty_vertical=15, empty_horizontal=0, font=FONT_SMALL, arrow_key_down_right_scroll_page=True,
                            show_header=False)
        sheet.pack(fill=tk.BOTH, padx=0, pady=(0, 5))
        #sheet.set_sheet_data(data=self.get_summary(system.get('Builds')))

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
        #command=partial(self._copy_to_clipboard, frm_container, activity)
        #sheet.edit_validation(self.validate_edits).bind("<<SheetModified>>", self.sheet_modified)
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
            # Update title with both display name and actual system name
            name = system.get('Name', '')
            sysname = system.get('StarSystem', '')
            if name == '':
                name = sysname
            if sysname == '':
                sysname = '(Unknown)'

            self.plan_titles[t]['Name']['text'] = name
            self.plan_titles[t]['System']['text'] = sysname

            if name == sysname:
                self.plan_titles[t]['System'].pack_forget()
            else:
                self.plan_titles[t]['System'].pack()

            if sysname == '(Unknown)':
                self.plan_titles[t]['System'].pack_forget()
                self.plan_titles[t]['Inara'].pack_forget()
            else:
                self.plan_titles[t]['Inara'].pack()


    def config_sheet(self, sheet):
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

    def calc_totals(self, system):
        # Calculate the totals
        totals = {'Planned': {}, 'Completed': {}}
        builds = system.get('Builds', [])
        required = self.colonisation.get_required(builds)
        for j, (name, col) in enumerate(self.summary_cols.items()):
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
                        if j >= len(required):
                            continue
                        res = required[j]
                        trips = ceil(sum(res.values()) / self.bgstally.state.cargo_capacity)
                        totals['Planned'][name] += trips
                        totals['Completed'][name] += trips if self.is_build_completed(build) else 0
                    case _ if col.get('format') == 'int':
                        totals['Planned'][name] += bt.get(name, 0)
                        totals['Completed'][name] += bt.get(name, 0) if self.is_build_completed(build) else 0

        return totals


    def get_summary(self, system):
        """
        Return the summary section with current system data
        """
        totals = self.calc_totals(system)

        # Update the values in the cells.
        summary:list = []
        for i, r in enumerate(['Planned', 'Completed']):
            row:list = [' ', ' ', r]
            for j, (name, col) in enumerate(self.summary_cols.items()):
                if col.get('hide', False) == True:
                    row.append(' ')
                    continue
                row.append(totals[r].get(name, 0))
            summary.append(row)

        return summary


    def update_summary(self, srow, tab, system):
        scol = 0
        new = self.get_summary(system)

        for i, rowname in enumerate(['Completed', 'Planned']):
            for j, (col, details) in enumerate(self.summary_cols.items()):
                j += FIRST_SUMMARY_COLUMN
                tab[i+srow,j].data = ' ' if new[i][j] == 0 else f"{new[i][j]:,}" if details.get('format') == 'int' else new[i][j]

                if new[i][j] and new[i][j] != ' ' and new[i][j] != 0 and details.get('background') == True:
                    color = self.get_color(new[i][j], details.get('min', -1), details.get('max', 1))
                    tab[i+srow,j+scol].highlight(bg=color)
                    if color != '':
                        tab[i+srow,j+scol].highlight(bg=color)
                else:
                    tab[i+srow,j+scol].highlight(bg=None)


    def get_detail_header(self):
        cols: list = []
        for c, v in self.detail_cols.items():
            cols.append(v.get('header', c) if v.get('hide') != True else ' ')
        return cols

    #def update_detail_header(self, srow, tab):
    #    for j, name in enumerate(self.get_detail_header()):
    #        tab[srow,j].data = name
    #        tab[srow,j].highlight(bg='lightgrey')


    def get_detail(self, system):
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
            for j, (name, col) in enumerate(self.detail_cols.items()):
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
                            v = ceil(sum(reqs[i].values()) / self.bgstally.state.cargo_capacity)
                        row.append(v if v != 0 else ' ')

                    case _:
                        if name == 'State':
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

                        row.append(build.get(name, ' '))

            details.append(row)

        # Is the last line an uncategorized base? If so add another
        if details[-1][1] != ' ':
            row:list = [' '] * (len(list(self.detail_cols.keys())) -1)
            details.append(row)
        else:
            Debug.logger.debug(f"Not adding empty base row [{details[-1][1]}]")

        return details


    def update_detail(self, srow, tab, system):
        new = self.get_detail(system)

        # It seems trying to read the sheet data just errors. :(
        for i, build in enumerate(system.get('Builds', [])):
            for j, (col, details) in enumerate(self.detail_cols.items()):
                if i >= len(new) or j >= len(new[i]):
                    continue

                # Set or clear the cell value
                tab[i+srow,j].data = ' ' if new[i][j] == ' ' else f"{new[i][j]:,}" if details.get('format') == 'int' else new[i][j]
                # Clear the highlight
                if tab[i+srow,j].data != new[i][j]:
                    tab[i+srow,j].highlight(bg=None)

                    if details.get('background') == True and new[i][j] != 0:
                        color = self.get_color(new[i][j], details.get('min', -1), details.get('max', 1))
                        tab[i+srow,j].highlight(bg=color)

                # Mark completed builds as readonly
                if j == 5 and new[i][j] == BuildState.COMPLETE:
                    tab[i+srow,0].del_checkbox(); tab[i+srow,0].data = ' '; tab[i+srow,0].readonly()
                    # Base type has been set so make it readonly
                    if new[i][1] != ' ':
                        tab[i+srow,1].readonly()
                        tab[i+srow,1].del_dropdown()

                    tab[i+srow,2].readonly()

        if len(tab.data) > len(system.get('Builds', [])) + FIRST_BUILD_INDEX + 1:
            Debug.logger.debug(f"Too many build rows in the sheet {len(tab.data)} {len(system.get('Builds', [])) + FIRST_BUILD_INDEX + 1}")

    def update_display(self):
        systems = self.colonisation.get_all_systems()
        for i, tab in enumerate(self.sheets):
            system = systems[i]
            Debug.logger.debug(f"Updating system {i} {system.get('Name')}")
            self.update_title(i, system)
            self.update_summary(FIRST_SUMMARY_INDEX, self.sheets[i], system)
            self.update_detail(FIRST_BUILD_INDEX, self.sheets[i], system)

        #self.color_cells(self)

        return


    def validate_edits(self, event):
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


    def sheet_modified(self, tabnum, event):
        try:
            # uncomment below if you want to take a look at the event object
            Debug.logger.debug(f"The sheet was modified! {event}")

            # otherwise more information at:
            # #event-data
            Debug.logger.debug(f"Event: {event.eventname}")
            if event.eventname.endswith('edit_table'):
                row = event.row - 4
                col = event.column
                val = event.value
                Debug.logger.debug(f"Changed {tabnum} {row} {col}: {val} ")
                fields = list(self.detail_cols.keys())
                field = fields[col]

                if field == 'Base Type' and val == ' ':
                    Debug.logger.debug(f" Removing build {row} from system {tabnum}")
                    self.colonisation.remove_build(self.colonisation.systems[tabnum], row)
                    data = self.sheets[tabnum].data
                    data.pop(row + FIRST_BUILD_INDEX)
                    self.sheets[tabnum].set_sheet_data(data)
                    self.config_sheet(self.sheets[tabnum])
                    self.update_display()
                    return

                if row >= len(self.colonisation.systems[tabnum]['Builds']):
                    self.colonisation.add_build(self.colonisation.systems[tabnum])
                    Debug.logger.debug(f"Added build")

                if field == 'Track':
                    # Make sure the plan name is up to date.
                    self.colonisation.systems[tabnum]['Builds'][row]['Plan'] = self.colonisation.systems[tabnum].get('Name')
                    self.colonisation.update_build_tracking(self.colonisation.systems[tabnum]['Builds'][row], val)
                    Debug.logger.debug(f"Updated tracking to {val}")
                    self.update_display()
                    return

                Debug.logger.debug(f"Updated {row} {field} to {val}")
                self.colonisation.systems[tabnum]['Builds'][row][field] = val

                self.colonisation.dirty = True
                self.colonisation.save()
                self.update_display()

            return

        except Exception as e:
            Debug.logger.error(f"Error in sheet_modified(): {e}")
            Debug.logger.error(traceback.format_exc())


    def add_system_dialog(self):
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
            command=lambda: self.add_system(plan_name_var.get(), system_name_var.get(), dialog)
        )
        add_button.pack(side=tk.LEFT, padx=5)
        self.tabbar.add(dialog, text='+')


    def add_system(self, plan_name, system_name, dialog):
        """
        Add a new system

        Args:
            plan_name: The system name
            system_name: The display name
            dialog: The dialog to close
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
        Show dialog to rename a system
        """
        if not self.get_current_system():
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


    def rename_system(self, system_name, dialog):
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


    def delete_system(self, tab, tabnum):
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
            del self.content_frames[tabnum]
            del self.plan_titles[tabnum]
            del self.track_all_vars[tabnum]
            del self.summary_labels[tabnum]
            del self.detail_labels[tabnum]

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
        fnt = tkFont.Font(font=item['font']).actual()
        item.configure(font=(fnt['family'], fnt['size'], w))


    def get_color(self, value:int, min_value:int = -1, max_value:int = 1):
        """
        Get a color based on the value and its range

        Args:
            value: The value to color
            min_value: The minimum value for the range
            max_value: The maximum value for the range

        Returns:
            A hex color string
        """
        if not isinstance(value, int) and not value.isdigit():
            return '#550055'

        if value == 0:
            return '#005500'

        # keep it within the limits
        value = min(max(int(value), int(min_value)), int(max_value))

        gradient = self.create_gradient(max_value - min_value + 1)
        # Normalize the value to a range of 0-1
        normalized_value = (value - min_value) / (max_value - min_value)
        normalized_value = max(0, min(1, normalized_value))

        # Calculate the gradient color
        gradient_index = int(normalized_value * (len(gradient) - 1))
        # Debug.logger.debug(f"Gradient: min {min_value} max {max_value} val {value} norm {normalized_value} {gradient_index} {gradient[gradient_index]}")
        return gradient[gradient_index]


    def create_gradient(self, steps):
        """
        Generates a list of RGB color tuples representing a gradient from green to red.

        Args:
            steps: The number of steps in the gradient.

        Returns:
            A list of RGB color tuples.
        """
        try:
            gradient = []
            ulim=25
            llim=200
            for i in range(steps):
                #if i == 0:
                #    red = ulim
                #    green=llim
                #    blue=llim
                if i == int(steps/2):
                    red=255
                    green=255
                    blue=255
                elif i > steps / 2:
                    green = int(ulim * (steps-i) / (steps -1)) + llim
                    red = int(green/2)
                    blue = int(green/2)
                else:
                    red = int(ulim * i / (steps - 1)) + llim
                    green = int(red/2)
                    blue = int(red/2)

                gradient.append(f"#{red:02x}{green:02x}{blue:02x}")

        except Exception as e:
            Debug.logger.error(f"Error in gradient: {e}")
            Debug.logger.error(traceback.format_exc())
            gradient = ["#CCCCCC"]

        return gradient


    def get_system_tracking_status(self, plan_name):
        """
        Get the tracking status for a system

        Args:
            system_name: The system address

        Returns:
            "all" if all non-completed builds are tracked
            "partial" if some non-completed builds are tracked
            "none" if no non-completed builds are tracked
        """
        system = self.colonisation.get_system('Name', plan_name)
        if not system:
            return "none"

        builds = system.get('Builds', [])
        if not builds:
            return "none"

        # Count tracked and non-tracked builds (excluding completed builds)
        tracked_count = 0
        non_tracked_count = 0

        for build in builds:
            # Skip completed builds
            if self.is_build_completed(build):
                continue

            if build.get('Track', False) == True:
                tracked_count += 1
            else:
                non_tracked_count += 1

        # Determine status
        if tracked_count > 0 and non_tracked_count == 0:
            return "all"
        elif tracked_count > 0:
            return "partial"
        else:
            return "none"

    def count_starports(self, builds) -> int:
        i = 0
        starports = self.colonisation.get_base_types('Initial')
        for b in builds:
            i += 1 if b.get('Base Type') in starports else 0

        return i

    def is_build_completed(self, build):
        """
        Check if a build is completed

        Args:
            build: The build to check

        Returns:
            True if the build is completed, False otherwise
        """

        state = build.get('State', '')
        if state != '':
            return state == BuildState.COMPLETE

        # If the build has a MarketID, check if all resources have been provided
        market_id = build.get('MarketID')
        if market_id:
            build['State'] = BuildState.PROGRESS
            for depot in self.colonisation.progress:
                if depot.get('MarketID') == market_id and depot.get('ConstructionComplete', False):
                    build['State'] = BuildState.COMPLETE
        else:
            build['State'] = BuildState.PLANNED

        return build['State'] == BuildState.COMPLETE

    def get_current_system(self):
        return
    def update_build_body(self, tab, index, var):
        return
    def toggle_all_builds(self, tabnum):
        return
    def toggle_build(self, tab, index, var):
        return
    def update_build_type(self, tab, index, var):
        return
    def update_build_name(self, tab, index, var):
        return
