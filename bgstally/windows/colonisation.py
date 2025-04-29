import tkinter as tk
import tkinter.font as tkFont
from os import path
from math import ceil
import traceback
from tkinter import ttk, messagebox, PhotoImage
import webbrowser
from typing import Dict, List, Optional
from thirdparty.ScrollableNotebook import ScrollableNotebook

from bgstally.constants import FONT_HEADING_1, COLOUR_HEADING_1, FONT_HEADING_2, FONT_TEXT, FOLDER_ASSETS, BuildStatus
from bgstally.debug import Debug
from bgstally.utils import _

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

        # Create summary section (frozen at the top)
        #self.summary_cols = {
        #    "Total": "lightgoldenrod", "Orbital":"lightgoldenrod", "Surface":"lightgoldenrod",
        #    # "Requirements": "lightgrey",
        #    "State": "lightgoldenrod", "T2":"lightgrey", "T3":"lightgrey", "Cost":"firebrick3", "Trips":"firebrick3", "Pad": "lightgrey", "Economy":"lightgrey",
        #    "Pop Inc": "lightgrey", "Pop Max": "lightgrey", "Economy Inf": "lightgrey", "Security": "lightgrey",
            # "Tech Level": "lightgrey", "Wealth": "lightgrey", "SoL": "lightgrey", "Dev Level": "lightgrey"
        # }
        self.summary_cols = {
            'Total': {'background': False, 'number': True},
            'Orbital': {'background': False, 'number': True},
            'Surface': {'background': False, 'number': True},
            'State': {'background': False, 'hide': True},
            'T2': {'background': True, 'number': True, 'min': -1, 'max': 1},
            'T3': {'background': True, 'number': True, 'min': -1, 'max': 1},
            'Cost': {'background': None, 'number': True},
            'Trips': {'background': None, 'number': True},
            'Pad': {'background': None, 'hide': True},
            'Economy': {'background': None, 'hide': True},
            'Pop Inc': {'background': True, 'number': True, 'min': -10, 'max': 20},
            'Pop Max': {'background': True, 'number': True, 'min': -10, 'max': 20},
            'Economy Inf': {'background': True, 'number': True, 'hide': True, 'min': -10, 'max': 20},
            'Security': {'background': True, 'number': True, 'min': -10, 'max': 20},
            'Tech Level' : {'background': True, 'number': True, 'min': -10, 'max': 20},
            'Wealth' : {'background': True, 'number': True, 'min': -10, 'max': 20},
            'SoL' : {'background': True, 'number': True, 'min': -10, 'max': 20},
            'Dev Level' : {'background': True, 'number': True, 'min': -10, 'max': 20}
        }
        self.detail_cols = [
            "Track", "Base Type", "Name", "Body", "Requirements", "State", "T2", "T3",
            "Cost", "Trips", "Pad", "Economy", "Pop Inc", "Pop Max",
            "Econony Inf", "Security", "Tech Level", "Wealth",
            "SoL", "Dev Level"
        ]
        self.checkall = None
        # Calculate column widths
        widths = [8, 20, 20, 5, 20, 15, 8, 8, 15, 8, 8, 15, 8, 8, 15, 8, 10, 8, 15, 10]

        self.current_system = None
        self.current_tab = 0

        # UI components
        self.tabbar = None
        self.content_frames = []
        self.plan_titles = []
        self.track_all_vars = []
        self.summary_labels = []
        self.detail_labels = []
        self.srow = 5 # Starting row for builds table

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
            self.window.geometry("1200x300")
            self.window.protocol("WM_DELETE_WINDOW", self.close)

            # Create main frames
            self.create_frames()
            self.update_display()

        except Exception as e:
            Debug.logger.error(f"Error in colonisation.show(): {e}")
            Debug.logger.error(traceback.format_exc())

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

                # Determine tracking status for this system
                tracking_status = self.colonisation.get_system_tracking(system)
                tab = ttk.Frame(self.tabbar)
                tab.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)

                self.create_title_frame(tab, i)
                self.create_unified_table_frame(tab, i, system)

                Debug.logger.debug(f"Creating tab {i+1} {system.get('Name')} {system.get('StarSystem')}")
                self.tabbar.add(tab, text=system['Name'], compound='right', image=self.image_tab_tracked if tracking_status == "All" else self.image_tab_part_tracked if tracking_status == "Partial" else self.image_tab_untracked)
                #self.system_tabs.append(tab)

            if i > 0:
                #Debug.logger.debug(f"Setting current tab to {self.current_tab}")
                self.tabbar.select(1)
                self.current_tab = 1
                self.current_system = self.colonisation.get_system('Name', systems[0]['Name'])

            #Debug.logger.debug(f"Created {i} system tabs {self.tabbar.tabs()}")

        except Exception as e:
            Debug.logger.error(f"Error in colonisation.show(): {e}")
            Debug.logger.error(traceback.format_exc())

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
                Debug.logger.error(f"Error in update_display() {e}")
                Debug.logger.error(traceback.format_exc())

        inara.bind("<Button-1>", inara_click)
        self.plan_titles[tabnum]['Inara'] = inara

        btn = ttk.Button(title_frame, text=_("Delete"), command=lambda: self.delete_system(tab, tabnum))
        btn.pack(side=tk.RIGHT, padx=10, pady=5)


    def create_unified_table_frame(self, tab_frame, tabnum, system):
        """
        Create a unified table frame with both summary and builds in a single scrollable area
        """
        # Main table frame
        table_frame = ttk.Frame(tab_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Configure the table frame to resize with the window
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Create a canvas with scrollbar for the main content
        main_canvas = tk.Canvas(table_frame)
        y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=main_canvas.yview)
        y.grid(row=0, column=1, sticky=tk.NSEW)
        x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=main_canvas.xview)
        x.grid(row=1, column=0, sticky=tk.NSEW)

        # Create a frame inside the canvas to hold all content
        content_frame = ttk.Frame(main_canvas)

        if len(self.content_frames) <= tabnum:
            self.content_frames.append(content_frame)
        else:
            self.content_frames[tabnum] = content_frame

        # Configure the canvas
        main_canvas.create_window((0, 0), window=content_frame, anchor=tk.NW)
        #main_canvas.configure(yscrollcommand=scrollbar.set)
        #main_canvas.configure(xscrollcommand=scrollbar.set)
        main_canvas.grid(row=0, column=0, sticky=tk.NSEW)

        # Configure the canvas to resize with the content
        content_frame.bind("<Configure>",lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))

        # Headers for the table

        # Configure content frame columns to have consistent widths
        #for i in range(len(self.detail_cols)):
        #    min_width = max(widths[i] * 2, 5)  # Ensure at least 30 pixels
        #    content_frame.columnconfigure(i, weight=1) #, minsize=min_width)


        self.create_summary_section(content_frame, tabnum, 0)
        self.create_detail_section(content_frame, tabnum, 3, system)

        # Bind canvas resize to update the window width
        main_canvas.bind("<Configure>", self._on_canvas_configure)


    def _on_canvas_configure(self, event):
        """
        Handle canvas resize event to update the window width
        """
        for frame in self.content_frames:
            frame.configure(width=event.width, height=event.height)

    def create_summary_section(self, content_frame, tabnum, rnum):
        """
        Create the summary section with planned and progress rows
        """
        #Debug.logger.debug(f"Creating summary section for tab {tabnum}")

        # Header column
        scol=1
        for j, (header, col) in enumerate(self.summary_cols.items()):
            # Special case for "Track" header - add a checkbox
            cell = ttk.Label(content_frame, background='lightgrey', anchor=tk.CENTER)
            if col.get('hide') is not True:
                cell['text'] = header
            self.weight(cell)
            cell.grid(row=rnum, column=j+scol+1, padx=2, pady=2, ipadx=2, ipady=2, sticky=tk.NSEW)
        rnum += 1

        self.summary_labels.append([]) # New entry for this tab
        self.summary_labels[tabnum] = {}
        for i, r in enumerate(["Planned", "Progress"]):
            # Add "Planned"/"Progress" label
            lbl = ttk.Label(
                content_frame,
                background='',
                text=r,
                anchor=tk.E
            )
            lbl.grid(row=rnum+i, column=scol, padx=2, pady=2, ipady=2, ipadx=2, sticky=tk.NSEW)
            self.weight(lbl)

            # Now do the value columns
            self.summary_labels[tabnum][r] = {} # new row for our progress.
            for j, name in enumerate(self.summary_cols.keys()):
                label = ttk.Label(content_frame, text="", background='', anchor=tk.CENTER)
                label.grid(row=rnum+i, column=scol+j+1, padx=2, pady=2, ipadx=2, ipady=2, sticky=tk.NSEW)
                self.summary_labels[tabnum][r][name] = label

            #content_frame.grid_rowconfigure(rnum, weight=1)

    def create_detail_section(self, content_frame, tabnum, rnum, system):
        """
        Create the header row with column titles
        """

        #Debug.logger.debug(f"Creating detail section for tab {tabnum}")
        # Create headers with wrapping for long or multi-word headers
        for j, header in enumerate(self.detail_cols):
            # Special case for "Track" header - add a checkbox
            if j == 0:  # First column is "Track"
                # Add the header text
                lbl = ttk.Label(
                    content_frame,
                    text=header,
                    anchor=tk.CENTER,
                    )
                self.weight(lbl)
                lbl.grid(row=rnum-1, column=0, padx=2, pady=2, ipady=4, sticky=tk.W)

                # Add the "check all" checkbox
                while tabnum >= len(self.track_all_vars):
                    self.track_all_vars.append(tk.BooleanVar(value=False))

                cell = ttk.Checkbutton(
                    content_frame,
                    variable=self.track_all_vars[tabnum],
                    command=lambda tab=tabnum: self.toggle_all_builds(tab)
                )
                cell.grid(row=rnum, column=0, padx=2, pady=2)

            else:
                # Single line header
                cell = ttk.Label(content_frame, text=header, background="lightgrey", anchor=tk.CENTER)
                self.weight(cell)
                cell.grid(row=rnum, column=j, padx=2, pady=2, ipady=2, sticky=tk.NSEW)

        self.detail_labels.append([])

        for i, build in enumerate(system.get('Builds')):
            self.add_build_row(build, content_frame, tabnum, i)

        if len(system.get('Builds')) != 1 or system['Builds'][0].get('State') == BuildStatus.COMPLETE:
            self.add_build_row({}, content_frame, tabnum, len(system.get('Builds')))

    def add_build_row(self, build, content_frame, tabnum, row):
        #Debug.logger.debug(f"Adding build row {index} for tab {tabnum} {build}")
        # Check if the build is completed

        #Debug.logger.debug(f"Entering add_build_row for tab {tabnum}")
        is_completed = False
        if build != {}:
            is_completed = self.is_build_completed(build)

        self.detail_labels[tabnum].append([])
        self.detail_labels[tabnum][row] = {}

        for i, c in enumerate(self.detail_cols):
            cell = ''
            match c:
                case 'Track':
                    if not is_completed:
                        # For builds in progress, show a checkbox
                        cell = tk.BooleanVar(value=build.get('Track', 'No') == 'Yes')

                        ttk.Checkbutton(
                            content_frame,
                            variable=cell,
                            command=lambda idx=row, var=cell: self.toggle_build(tabnum, idx, var)
                        ).grid(row=row+self.srow, column=i, padx=2, pady=2)

                case 'Base Type':
                    # Type dropdown
                    types = self.colonisation.get_base_types('Any')
                    if row == 0:
                        types = self.colonisation.get_base_types('Initial')

                    cell = tk.StringVar(value=build.get(c, ''))
                    combo = ttk.Combobox(
                        content_frame,
                        textvariable=cell,
                        values=types
                    )
                    combo.grid(row=row+self.srow, column=i, padx=2, pady=2, sticky=tk.W)

                    # Use a separate function to ensure the correct index is captured
                    def on_type_selected(event, tab=tabnum, idx=row, var=cell):
                        self.update_build_type(tab, idx, var)
                    combo.bind("<<ComboboxSelected>>", on_type_selected)

                case 'Name':
                    # If name is not from journal, provide an entry field
                    cell = tk.StringVar(value=build.get('Name', ''))
                    entry = ttk.Entry(content_frame, textvariable=cell)
                    entry.grid(row=row+self.srow, column=i, padx=2, pady=2, sticky=tk.W)
                    if is_completed:
                        entry.config(state='readonly')
                    else:
                        # Use a separate function to ensure the correct index is captured
                        def on_name_changed(event, tab=tabnum, idx=row, var=cell):
                            self.update_build_name(tab, idx, var)
                        entry.bind("<FocusOut>", on_name_changed)

                case 'Body':
                    # Body entry - always editable, identified from SuperCruiseExit event
                    cell = tk.StringVar(value=build.get('Body', ''))
                    entry = ttk.Entry(content_frame, textvariable=cell, width=5)
                    entry.grid(row=row+self.srow, column=i, padx=2, pady=2, sticky=tk.W)

                    # Use a separate function to ensure the correct index is captured
                    def on_body_changed(event, tab=tabnum, idx=row, var=cell):
                        self.update_build_body(tab, idx, var)
                    entry.bind("<FocusOut>", on_body_changed)

                case _:
                    cell = ttk.Label(content_frame, text="" , anchor=tk.CENTER)
                    cell.grid(row=row+self.srow, column=i, padx=2, pady=2, sticky=tk.EW)

            #Debug.logger.debug(f"Added build row {tabnum} {row} {i} {c} to {cell}")
            self.detail_labels[tabnum][row][c] = cell


    def update_display(self):
        """
        Update the display with current system data
        """
        #Debug.logger.debug("Updating display")
        try:
            systems = self.colonisation.get_all_systems()
            if len(systems) != len(self.tabbar.tabs())-1:
                Debug.logger.info(f"Mismatch in system count {len(systems)} vs {len(self.tabbar.tabs())} {self.tabbar.tabs()}")
                return

            for t, system in enumerate(systems):
                self.update_title(t, system)
                builds = self.colonisation.get_system_builds(system) # We do it this way so the build requirements get filled in for us.
                self.update_summary(t, system, builds)
                self.update_builds(t, system, builds)

        except Exception as e:
            Debug.logger.error(f"Error in update_display() {e}")
            Debug.logger.error(traceback.format_exc())


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
                Debug.logger.debug(f"Hiding systemname {name} {sysname}")
                self.plan_titles[t]['System'].pack_forget()
            else:
                self.plan_titles[t]['System'].pack()

            if sysname == '(Unknown)':
                Debug.logger.debug(f"Hiding systemname and inara {name} {sysname}")
                self.plan_titles[t]['System'].pack_forget()
                self.plan_titles[t]['Inara'].pack_forget()
            else:
                self.plan_titles[t]['Inara'].pack()

    def update_summary(self, t, system, builds):
        """
        Update the summary section with current system data
        """
        # Calculate the totals
        totals = {'Planned': {}, 'Progress': {}}
        required = self.colonisation.get_required(builds)
        for j, (name, col) in enumerate(self.summary_cols.items()):
            if col.get('hide') == True:
                continue

            totals['Planned'][name] = 0
            totals['Progress'][name] = 0
            # Calculate summary values
            for row, build in enumerate(builds):
                bt = self.colonisation.get_base_type(build.get('Base Type', ''))
                match name:
                    case 'Total':
                        totals['Planned'][name] += 1
                        totals['Progress'][name] += 1 if self.is_build_completed(build) else 0
                    case 'Orbital'|'Surface':
                        if bt.get('Location') == name:
                            totals['Planned'][name] += 1
                            totals['Progress'][name] += 1 if self.is_build_completed(build) else 0
                    case 'T2':
                        t2 = bt.get('T2 Reward', 0)
                        sp = self.count_starports(builds[1:row])
                        cost = bt.get('T2 Cost', 0) + (2 * sp)
                        if row > 0:
                            t2 -= cost
                        totals['Planned'][name] += t2
                        totals['Progress'][name] += t2 if self.is_build_completed(build) else 0
                    case 'T3':
                        t3 = bt.get('T3 Reward', 0)
                        sp = self.count_starports(builds[1:row])
                        cost = bt.get('T3 Cost', 0) + (bt.get('T3 Cost', 0) * sp)
                        if row > 0:
                            t3 -= cost
                        totals['Planned'][name] += t3
                        totals['Progress'][name] += t3 if self.is_build_completed(build) else 0
                    case 'Cost':
                        if row >= len(required):
                            Debug.logger.debug(f" No required for summary {row} {build}")
                            continue
                        res = required[row]
                        res = sum(res.values())
                        totals['Planned'][name] += res
                        totals['Progress'][name] += res if self.is_build_completed(build) else 0
                    case 'Trips':
                        if j >= len(required):
                            continue
                        res = required[j]
                        trips = ceil(sum(res.values()) / self.bgstally.state.cargo_capacity)
                        totals['Planned'][name] += trips
                        totals['Progress'][name] += trips if self.is_build_completed(build) else 0
                    case _ if col.get('number') == True:
                        totals['Planned'][name] += bt.get(name, 0)
                        totals['Progress'][name] += bt.get(name, 0) if self.is_build_completed(build) else 0

        # Update the values in the cells.
        for i, r in enumerate(['Planned', 'Progress']):
            for j, (name, col) in enumerate(self.summary_cols.items()):
                if col.get('hide', False) == True: continue

                v = totals[r].get(name, 0)
                if col.get('background') == True:
                    self.summary_labels[t][r][name]['background'] = self.get_color(v, col.get('min', -1), col.get('max', 1))
                if col.get('number', False) == True and v != 0:
                    v = f"{v:,}"

                self.summary_labels[t][r][name]['text'] = v

    def update_builds(self, t, system, builds):
        """
        Update the builds table with current system data
        """
        try:
            if t >= len(self.detail_labels):
                Debug.logger.info(f"Update builds, too many tabs: tab {t} of {len(self.detail_labels)}")
                return
            if len(builds) > len(self.detail_labels[t]):
                Debug.logger.info(f"Update builds, too many rows: row {len(builds)} of {len(self.detail_labels[t])}")
                return

            required = self.colonisation.get_required(builds)
            delivered = self.colonisation.get_delivered(builds)
            #Debug.logger.debug(f"Reqauired {required}")

            for i, build in enumerate(builds):
                bt = self.colonisation.get_base_type(build.get('Base Type', ''))
                for j, c in enumerate(self.detail_cols):
                    match c:
                        case 'Track':
                            if self.is_build_completed(build) == True:
                                continue
                            if build.get('Track') == 'Yes':
                                self.detail_labels[t][i][c] = True
                            else:
                                self.detail_labels[t][i][c] = False
                        case 'Base Type':
                            self.detail_labels[t][i][c].set(build.get('Base Type', ''))
                        case 'Name':
                            self.detail_labels[t][i][c].set(build.get(c, ''))
                        case 'Body':
                            body = build.get('Body', '')
                            star = system.get('StarSystem')
                            body = body.replace(star + ' ', '') if star else body
                            self.detail_labels[t][i][c].set(body)
                        case 'State':
                            if build.get('State', '') == BuildStatus.PROGRESS and i < len(required):
                                req = required[i]
                                req = sum(req.values())
                                deliv = delivered[i]
                                deliv = sum(deliv.values())
                                self.detail_labels[t][i][c]['text'] = f"{int(deliv * 100 / (req+deliv))}%"
                            else:
                                self.detail_labels[t][i][c]['text'] = build.get('State', '')
                        case 'T2':
                            t2 = bt.get('T2 Reward', 0)
                            sp = self.count_starports(builds[1:i])
                            cost = bt.get('T2 Cost', 0) + (2 * sp)
                            if i > 0:
                                t2 -= cost
                            #Debug.logger.debug(f"t2: {t2} {cost}")
                            self.detail_labels[t][i][c]['text'] = t2
                        case 'T3':
                            t3 = bt.get('T3 Reward', 0)
                            sp = self.count_starports(builds[1:i])
                            cost = bt.get('T3 Cost', 0) + (build.get('T3 Cost', 0) * sp)
                            if i > 0:
                                t3 -= cost
                            self.detail_labels[t][i][c]['text'] = t3
                        case 'Cost':
                            if i >= len(required):
                                self.detail_labels[t][i][c]['text'] = ""
                                continue
                            req = required[i]
                            req = sum(req.values())
                            self.detail_labels[t][i][c]['text'] = f"{req:,}"
                        case 'Trips':
                            if j >= len(required):
                                continue
                            req = required[j]
                            trips = ceil(sum(req.values()) / self.bgstally.state.cargo_capacity)
                            self.detail_labels[t][i][c]['text'] = f"{trips:,}"
                        case _:
                            v = bt.get(c, 0)
                            if isinstance(v, int) and v != 0:
                                if c not in ['Total', 'Cost', 'Orbital', 'Surface']:
                                    self.detail_labels[t][i][c]['background'] = self.get_color(v, -10, 10)
                                v = f"{v:}"
                            elif v == 0:
                                v = ""
                            self.detail_labels[t][i][c]['text'] = v

        except Exception as e:
            Debug.logger.error(f"Error in colonisation.update_builds(): {e}")
            Debug.logger.error(traceback.format_exc())


    def clear_builds_table(self, tabnum):
        """
        Clear the builds table
        """

        if len(self.content_frames) <= tabnum:
            return

        for widget in self.content_frames[tabnum].grid_slaves():
            if int(widget.grid_info()["row"]) > self.srow:
                widget.grid_forget() #or widget.grid_remove()

    def toggle_all_builds(self, tabnum):
        """
        Toggle all builds' tracking status
        """
        try:
            systems = self.colonisation.get_all_systems()
            builds = systems[tabnum].get('Builds', [])
            if not builds:
                #Debug.logger.debug(f"No builds found for tab {tabnum}")
                return

            # Determine the new state based on the header checkbox
            new_state = 'Yes' if self.track_all_vars[tabnum] else 'No'
            Debug.logger.debug(f"Toggling tracked state for all builds for tab {tabnum} to {new_state}")

            # Update all builds that are not completed
            for i, build in enumerate(builds):
                # Skip completed builds
                if self.is_build_completed(build):
                    continue

                #if new_state != build['Track']:
                #    Debug.logger.debug(f"Current state: {self.detail_labels[tabnum][i]['Track']}")
                #    self.detail_labels[tabnum][i]['Track'].invoke()
                build['Track'] = new_state

                #build['Track'] = new_state
                #Debug.logger.debug(f"Current state: {self.detail_labels[tabnum][i]['Track']}")
                #self.detail_labels[tabnum][i]['Track'] = True if new_state == 'Yes' else False

            # This _is_ the box's check
            #self.track_all_vars[tabnum] = True if new_state == 'Yes' else False

            # Save changes
            self.colonisation.dirty = True

            # Update the display
            self.update_display()

        except Exception as e:
            Debug.logger.error(f"Error in toggle_all_builds(): {e}")
            Debug.logger.error(traceback.format_exc())


    def toggle_build(self, tab, index, var):
        """
        Toggle a build's tracking status

        Args:
            index: The build index
            var: The checkbox variable
        """
        #Debug.logger.debug(f"Toggling build {tab} {index} to {var.get()}")
        systems = self.colonisation.get_all_systems()
        builds = systems[tab].get('Builds', [])
        if index < 0 or index >= len(builds):
            return

        # Update the build
        builds[index]['Track'] = 'Yes' if var.get() else 'No'

        # Save changes
        self.colonisation.dirty = True
        self.bgstally.ui.window_progress.update_display()

    def update_build_type(self, tab, index, var):
        """
        Update a build's type

        Args:
            index: The build index
            var: The type variable
        """
        try:
            #Debug.logger.debug(f"Updating build type tab {tab} row {index} to {var.get()}")

            if index >= len(self.colonisation.systems[tab]['Builds']):
                self.colonisation.add_build(self.colonisation.systems[tab])
                self.add_build_row({}, self.content_frames[tab], tab, index+1)

            self.colonisation.systems[tab]['Builds'][index]['Base Type'] = var.get()

            if var.get() == '<delete me>':
                # Delete the build
                del self.colonisation.systems[tab]['Builds'][index]
                del self.detail_labels[tab][index]
            # Save changes
            self.colonisation.dirty = True
            self.colonisation.save()
            self.update_display()

        except Exception as e:
            Debug.logger.error(f"Error in update_build_type(): {e}")
            Debug.logger.error(traceback.format_exc())

    def update_build_name(self, tab, index, var):
        """
        Update a build's name

        Args:
            index: The build index
            var: The name variable
        """

        systems = self.colonisation.get_all_systems()
        builds = systems[tab].get('Builds', [])

        if index < 0 or index >= len(builds):
            #(f"Invalid build index {index} for tab {tab} (add new?)")
            return

        # Update the build
        builds[index]['Name'] = var.get()

        # Save changes
        self.colonisation.dirty = True
        self.update_display()


    def update_build_body(self, tab, index, var):
        """
        Update a build's body

        Args:
            index: The build index
            var: The body variable
        """
        systems = self.colonisation.get_all_systems()
        builds = systems[tab].get('Builds', [])
        if index < 0 or index >= len(builds):
            return

        # Update the build
        builds[index]['Body'] = var.get()

        # Save changes
        self.colonisation.dirty = True
        self.colonisation.save()

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

            #Debug.logger.debug(f"Adding system {plan_name} {system_name}")

            # Add the system
            system = self.colonisation.add_system(plan_name, system_name)
            #systems = self.colonisation.get_all_systems()

            if not plan_name:
                messagebox.showerror(_("Error"), _("Failed to add system"))
                return

            tab = ttk.Frame(self.tabbar)
            tab.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)

            tabnum = len(self.plan_titles)
            self.create_title_frame(tab, tabnum)
            self.create_unified_table_frame(tab, tabnum, system)
            self.tabbar.add(tab, text=system['Name'], compound='right', image=self.image_tab_untracked)
            self.update_display()
        except Exception as e:
            Debug.logger.error(f"Error in add_system: {e}")
            Debug.logger.error(traceback.format_exc())


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

    def weight(self, item, w='bold'):
        fnt = tkFont.Font(font=item['font']).actual()
        item.configure(font=(fnt['family'], fnt['size'], w))

    def get_color(self, value, min_value, max_value):
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
            return "grey94"

        value = int(value)
        if value == 0:
            return "grey94"

        gradient = self.create_gradient(max_value - min_value + 1)
        # Normalize the value to a range of 0-1
        normalized_value = (value - min_value) / (max_value - min_value)
        normalized_value = max(0, min(1, normalized_value))

        # Calculate the gradient color
        gradient_index = int(normalized_value * (len(gradient) - 1))
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

    def get_current_system(self):
        try:
            tab = self.tabbar.select(None)
            self.current_tab = self.tabbar.index(tab)
            systems = self.colonisation.get_all_systems()
            self.current_system = systems[self.current_tab] if systems else None
            Debug.logger.error(f"Current system: {self.current_system}")
        except Exception as e:
            #Debug.logger.error(f"Error in get_current_system(): {e}")
            #Debug.logger.error(traceback.format_exc())
            self.current_system = None

        return self.current_system


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

            if build.get('Track', 'No') == 'Yes':
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
            return state == BuildStatus.COMPLETE

        # If the build has a MarketID, check if all resources have been provided
        market_id = build.get('MarketID')
        if market_id:
            build['State'] = BuildStatus.PROGRESS
            for depot in self.colonisation.progress:
                if depot.get('MarketID') == market_id and depot.get('ConstructionComplete', False):
                    build['State'] = BuildStatus.COMPLETE
        else:
            build['State'] = BuildStatus.PLANNED

        return build['State'] == BuildStatus.COMPLETE

