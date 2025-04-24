import tkinter as tk
from os import path
from math import ceil
import traceback
from tkinter import ttk, messagebox, PhotoImage
import webbrowser
from typing import Dict, List, Optional
from thirdparty.ScrollableNotebook import ScrollableNotebook

from bgstally.constants import FONT_HEADING_1, FONT_HEADING_2, FONT_TEXT, FOLDER_ASSETS
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

        self.current_system = None
        self.current_tab = 0
        # UI components
        self.tabbar = None
        self.system_tabs = []
        self.content_frames = []
        self.plan_name_labels = []
        self.track_all_vars = []

        # Data storage
        self.planned_labels = []
        self.progress_labels = []
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
            self.window.geometry("1200x800")
            self.window.minsize(1000, 600)
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
            Debug.logger.debug("Creating main frames")

            # Create system tabs notebook
            self.tabbar = ScrollableNotebook(self.window, wheelscroll=True, tabmenu=True)
            self.tabbar.pack(fill=tk.BOTH, side=tk.TOP, expand=True, padx=5, pady=5)
            self.add_system_dialog()

            Debug.logger.debug("Creating system tabs")

            # Add tabs for each system
            systems = self.colonisation.get_all_systems()

            if len(systems) == 0:
                return

            for i, system in enumerate(systems):
                # Create a frame for the sytem tab

                # Determine tracking status for this system
                tracking_status = self.get_system_tracking_status(system['Name'])
                tab = ttk.Frame(self.tabbar)
                tab.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
                self.create_title_frame(tab, i)
                self.create_unified_table_frame(tab, i)
                self.tabbar.add(tab, text=system['Name'], compound='right', image=self.image_tab_tracked if tracking_status == "all" else self.image_tab_part_tracked if tracking_status == "partial" else self.image_tab_untracked)

            if i > 0:
                Debug.logger.debug(f"Setting current tab to {self.current_tab}")
                self.tabbar.select(1)
                self.current_tab = 1
                self.current_system = self.colonisation.get_system('Name', systems[0]['Name'])

            Debug.logger.debug(f"Created {i} system tabs {self.tabbar.tabs()}")

        except Exception as e:
            Debug.logger.error(f"Error in colonisation.show(): {e}")
            Debug.logger.error(traceback.format_exc())

    def create_title_frame(self, tab, tabnum):
        """
        Create the title frame with system name and tick info
        """
        Debug.logger.debug(f"Creating title frame for tab {tabnum}")
        title_frame = ttk.Frame(tab, style="Title.TFrame")
        title_frame.pack(fill=tk.X, padx=0, pady=(0, 5))

        # Configure style for title frame
        style = ttk.Style()
        style.configure("Title.TFrame")

        # System name label

        plan_name_label = ttk.Label(title_frame, text="", font=FONT_HEADING_1)
        plan_name_label.pack(side=tk.LEFT, padx=10, pady=5)
        while len(self.plan_name_labels) <= tabnum:
            self.plan_name_labels.append(None)

        self.plan_name_labels[tabnum] = plan_name_label

        self.inara_link = ttk.Label(
            title_frame,
            text="Inara ⤴",
            font=FONT_TEXT,
            foreground="blue",
            cursor="hand2"
        )
        self.inara_link.pack(side=tk.LEFT, padx=10, pady=5)
        self.inara_link.bind("<Button-1>", self.open_inara)

        btn = ttk.Button(title_frame, text=_("Delete"), command=lambda: self.delete_system(tab, tabnum))
        btn.pack(side=tk.RIGHT, padx=10, pady=5)


    def create_unified_table_frame(self, tab_frame, tabnum):
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
        #y.pack(side = tk.RIGHT, fill = tk.Y)
        x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=main_canvas.xview)
        x.grid(row=1, column=0, sticky=tk.NSEW)
        #x.pack(side = tk.BOTTOM, fill = tk.X)

        # Create a frame inside the canvas to hold all content
        content_frame = ttk.Frame(main_canvas)

        # Configure the canvas
        main_canvas.create_window((0, 0), window=content_frame, anchor=tk.NW)
        #main_canvas.configure(yscrollcommand=scrollbar.set)
        #main_canvas.configure(xscrollcommand=scrollbar.set)
        main_canvas.grid(row=0, column=0, sticky=tk.NSEW)

        # Configure the canvas to resize with the content
        content_frame.bind("<Configure>",lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))

        # Headers for the table
        headers = [
            "Track", "Base Type", "Name", "Body", "Requirements", "T2", "T3",
            "Cost", "Trips", "Pad", "Economy", "Pop Inc", "Pop Max",
            "Econony Inf", "Security", "Tech Level", "Wealth",
            "SoL", "Dev Level"
        ]

        # Calculate column widths
        widths = [8, 20, 20, 5, 20, 8, 8, 15, 8, 8, 15, 8, 8, 15, 8, 10, 8, 15, 10]

        # Configure content frame columns to have consistent widths
        for i in range(len(headers)):
            min_width = max(widths[i] * 2, 5)  # Ensure at least 30 pixels
            content_frame.columnconfigure(i, weight=1) #, minsize=min_width)

        # Create summary section (frozen at the top)
        self.create_summary_section(content_frame, tabnum, 0)

        # Create the header row
        self.create_header_row(content_frame, headers, tabnum, 2)
        # Create a separator
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).grid(
            row=3, column=0, columnspan=len(headers), sticky=tk.EW, pady=5
        )
        self.srow = 4

        self.content_frames.append(content_frame)

        # Bind canvas resize to update the window width
        main_canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event):
        """
        Handle canvas resize event to update the window width
        """
        for frame in self.content_frames:
            frame.configure(width=event.width, height=event.height)

    def create_header_row(self, content_frame, headers, tabnum, rnum):
        """
        Create the header row with column titles
        """

        Debug.logger.debug(f"Creating header row for tab {tabnum}")
        # Create headers with wrapping for long or multi-word headers
        for i, header in enumerate(headers):
            # Special case for "Track" header - add a checkbox
            if i == 0:  # First column is "Track"
                # Add the header text
                ttk.Label(
                    content_frame,
                    text=header,
                    font=FONT_HEADING_2,
                    anchor=tk.CENTER,
                    ).grid(row=rnum-1, column=i, padx=2, pady=2, ipady=2, sticky=tk.W)

                # Add the "check all" checkbox
                while tabnum >= len(self.track_all_vars):
                    self.track_all_vars.append(tk.BooleanVar(value=False))

                Debug.logger.debug(f"Creating checkbox for tab {tabnum}")

                ttk.Checkbutton(
                    content_frame,
                    variable=self.track_all_vars[tabnum],
                    command=lambda tab=tabnum: self.toggle_all_builds(tab)
                ).grid(row=rnum, column=i, padx=2, pady=2)

            else:
                # Single line header
                label = ttk.Label(content_frame, text=header, font=FONT_HEADING_2, background="lightgrey", anchor=tk.CENTER)
                label.grid(row=rnum, column=i, padx=2, pady=2, ipady=2, sticky=tk.NSEW)

    def create_summary_section(self, content_frame, tabnum, rnum):
        """
        Create the summary section with planned and progress rows
        """
        Debug.logger.debug(f"Creating summary section for tab {tabnum}")

        scol=1
        # Headers for the table
        columns = {
            "Total":"lightgoldenrod", "Orbital":"lightgoldenrod", "Surface":"lightgoldenrod", "T2":"lightgrey", "T3":"lightgrey",
            "Cost":"firebrick3", "Trips":"firebrick3", "Pads": "lightgrey", "Economy":"lightgrey", "Pop Inc": "lightgrey",
            "Pop Max": "lightgrey", "Econony Inf": "lightgrey", "Security": "lightgrey", "Tech Level": "lightgrey", "Wealth": "lightgrey",
            "Standard of Living": "lightgrey", "Dev Level": "lightgrey"
        }

        # Add "Planned" label
        ttk.Label(
            content_frame,
            text="Planned",
            font=FONT_HEADING_2,
            background="palegreen",
            anchor=tk.E
        ).grid(row=rnum, column=scol, padx=2, pady=2, ipady=2, sticky=tk.NSEW)

        # Create planned values row
        while len(self.planned_labels) <= tabnum:
            self.planned_labels.append({})

        for i, col in enumerate(columns.keys()):
            label = ttk.Label(content_frame, text="", background=columns[col], font=FONT_HEADING_2, anchor=tk.CENTER)
            label.grid(row=rnum, column=i+scol+1, padx=2, pady=2, ipady=2, sticky=tk.NSEW)
            self.planned_labels[tabnum][col] = label

        content_frame.grid_rowconfigure(rnum, weight=1)

        rnum += 1
        # Add "Progress" label in first column
        ttk.Label(
            content_frame,
            text="Progress",
            font=FONT_HEADING_2,
            background="palegreen",
            anchor=tk.E
        ).grid(row=rnum, column=scol, padx=2, pady=2, ipady=2, sticky=tk.NSEW)

        # Create progress values row
        while len(self.progress_labels) <= tabnum:
            self.progress_labels.append({})

        for i, col in enumerate(columns.keys()):
            label = ttk.Label(content_frame, text=" ", background=columns[col], font=FONT_HEADING_2, anchor=tk.CENTER)
            label.grid(row=rnum, column=i+scol+1, padx=2, pady=2, ipady=2, sticky=tk.NSEW)
            self.progress_labels[tabnum][col] = label

        content_frame.grid_rowconfigure(rnum, weight=1)

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

            if build.get('Tracked', 'No') == 'Yes':
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

    def is_build_completed(self, build):
        """
        Check if a build is completed

        Args:
            build: The build to check

        Returns:
            True if the build is completed, False otherwise
        """
        # If the build has a MarketID, check if all resources have been provided
        market_id = build.get('MarketID')
        if market_id:
            for depot in self.colonisation.progress:
                if depot.get('MarketID') == market_id:
                    # Check if construction is complete
                    if depot.get('ConstructionComplete', False):
                        return True

                    # Check if all resources have been provided
                    all_provided = True
                    for resource in depot.get('ResourcesRequired', []):
                        required = resource.get('RequiredAmount', 0)
                        provided = resource.get('ProvidedAmount', 0)
                        if provided < required:
                            all_provided = False
                            break

                    return all_provided

        # If no MarketID or not found in progress data, check if it has a "Complete" flag
        return build.get('Complete', False)

    def update_display(self):
        """
        Update the display with current system data
        """
        try:
            systems = self.colonisation.get_all_systems()
            if len(systems) != len(self.tabbar.tabs())-1:
                Debug.logger.debug(f"Mismatch in system count {len(systems)} vs {len(self.tabbar.tabs())} {self.tabbar.tabs()}")
                return

            for tabnum, system in enumerate(systems):

                # Update title with both display name and actual system name
                plan_name = systems[tabnum].get('Name', '')
                system_name = systems[tabnum].get('StarSystem', '')

                if system_name and system_name != plan_name:
                    title_text = f"{system_name} ({plan_name})"
                else:
                    title_text = plan_name

                Debug.logger.debug(f"Updating tab {tabnum} {title_text}")

                self.plan_name_labels[tabnum].config(text=title_text)

                # Update summary
                self.update_summary(tabnum)

                # Update builds table
                self.update_builds_table(tabnum)

        except Exception as e:
            Debug.logger.error(f"Error in update_display() {e}")
            Debug.logger.error(traceback.format_exc())


    def update_summary(self, tabnum):
        """
        Update the summary section with current system data
        """

        # Calculate summary values
        systems = self.colonisation.get_all_systems()
        builds = systems[tabnum].get('Builds', [])

        # Count planned vs progress
        planned_count = 0
        progress_count = 0

        # Count orbital vs surface
        orbital_count = 0
        surface_count = 0

        # Other totals
        total_comm = 0
        loads = 0
        economies = {}
        pop_inc = 0
        pop_max = 0
        economy_influences = {}
        security = 0
        tech_level = 0
        wealth = 0
        standard_of_living = 0
        dev_level = 0

        # T2/T3 counts
        t2 = 0; t3 = 0

        # Process each build
        for i, build in enumerate(builds):
            # Get base type info
            base_type = self.colonisation.get_base_type(build.get('Type', ''))
            if not base_type:
                continue

            # Count as planned or progress
            if build.get('Tracked', 'No') == 'Yes':
                progress_count += 1

            planned_count += 1

            # Count as orbital or surface
            if base_type.get('Location', '') == 'Orbital':
                orbital_count += 1
            else:
                surface_count += 1

            # Add to other totals
            total_comm += int(base_type.get('Total Comm', 0))
            loads += ceil(total_comm / self.bgstally.state.cargo_capacity)  # 784 is the max capacity of a Type 9

            # Count economies
            economy = base_type.get('Facility Economy', '')
            if economy:
                economies[economy] = economies.get(economy, 0) + 1

            # Population
            pop_inc += int(base_type.get('Pop Inc', 0))
            pop_max += int(base_type.get('Pop Max', 0))

            # Economy influence
            econ_inf = base_type.get('Economy Influence', '')
            if econ_inf:
                economy_influences[econ_inf] = economy_influences.get(econ_inf, 0) + 1

            # Other metrics
            security += int(base_type.get('Security', 0))
            tech_level += int(base_type.get('Tech Level', 0))
            wealth += int(base_type.get('Wealth', 0))
            standard_of_living += int(base_type.get('Standard of Living', 0))
            dev_level += int(base_type.get('Dev Level', 0))

            # T2/T3 counts
            if i == 0:
                t2 += base_type.get('T2 Reward', 0)
                t3 += base_type.get('T3 Reward', 0)
            if i > 0:
                t2 += base_type.get('T2 Reward', 0) - base_type.get('T2 Cost', 0)
                t3 += base_type.get('T3 Reward', 0) - base_type.get('T3 Cost', 0)

            # Update planned labels
            self.planned_labels[tabnum]["Total"].config(text=str(planned_count)+" total")
            self.planned_labels[tabnum]["Orbital"].config(text=str(orbital_count) +" orbital")
            self.planned_labels[tabnum]["Surface"].config(text=str(surface_count) +" surface")
            self.planned_labels[tabnum]["T2"].config(text=str(t2),background=self.get_color(t2, -1, 1))
            self.planned_labels[tabnum]["T3"].config(text=str(t3),background=self.get_color(t3, -1, 1))
            self.planned_labels[tabnum]["Cost"].config(text=str(total_comm),background=self.get_color(total_comm, -1, 1))
            self.planned_labels[tabnum]["Trips"].config(text=str(loads),background=self.get_color(loads, -1, 1))

            # Economy display
            self.planned_labels[tabnum]["Economy"].config(text="")

            # Population
            self.planned_labels[tabnum]["Pop Inc"].config(text=str(pop_inc),foreground=self.get_color(pop_inc, 0, 10))
            self.planned_labels[tabnum]["Pop Max"].config(text=str(pop_max),foreground=self.get_color(pop_max, 0, 10))

            # Economy influence
            self.planned_labels[tabnum]["Econony Inf"].config(text="")

            # Other metrics
            self.planned_labels[tabnum]["Security"].config(text=str(security),foreground=self.get_color(security, -10, 10))
            self.planned_labels[tabnum]["Tech Level"].config(text=str(tech_level),foreground=self.get_color(tech_level, -10, 10))
            self.planned_labels[tabnum]["Wealth"].config(text=str(wealth),foreground=self.get_color(wealth, -10, 10))
            self.planned_labels[tabnum]["Standard of Living"].config(text=str(standard_of_living),foreground=self.get_color(standard_of_living, -10, 10))
            self.planned_labels[tabnum]["Dev Level"].config(text=str(dev_level),foreground=self.get_color(dev_level, -10, 10))

            # Update progress labels - for now just show zeros
            for key in self.progress_labels[tabnum]:
                self.progress_labels[tabnum][key].config(text="")

    def clear_summary(self):
        """
        Clear the summary section
        """

        for key in self.planned_labels[self.current_tab]:
            self.planned_labels[self.current_tab][key].config(text="0")


        for key in self.progress_labels[self.current_tab]:
            self.progress_labels[self.current_tab][key].config(text="0")

    def update_builds_table(self, tabnum):
        """
        Update the builds table with current system data
        """
        try:

            # Clear existing builds
            self.clear_builds_table(tabnum)

            # Get builds for the current system
            systems = self.colonisation.get_all_systems()
            builds = systems[tabnum].get('Builds', [])

            # Add each build to the table
            for i, build in enumerate(builds):
                self.add_build_row(build, i, tabnum)

            self.add_build_row({}, len(builds), tabnum)

        except Exception as e:
            Debug.logger.error(f"Error in colonisation.update_builds_table(): {e}")
            Debug.logger.error(traceback.format_exc())

    def add_build_row(self, build, index, tabnum):
        Debug.logger.debug(f"Adding build row {index} for tab {tabnum} {build}")
        # Check if the build is completed
        is_completed = self.is_build_completed(build)

        # Track checkbox or completed indicator
        if is_completed:
            # For completed builds, show a read-only checkmark button
            track_button = ttk.Button(
                self.content_frames[tabnum],
                text="✓",
                state="disabled"
            )
            track_button.grid(row=index+self.srow, column=0, padx=2, pady=2)
        else:
            # For builds in progress, show a checkbox
            track = tk.BooleanVar(value=build.get('Tracked', 'No') == 'Yes')
            Debug.logger.debug(f"Adding checkbox for build {index} {build} {track.get()}")
            complete_check = ttk.Checkbutton(
                self.content_frames[tabnum],
                variable=track,
                command=lambda idx=index, var=track: self.toggle_build(tabnum, idx, var)
            )
            complete_check.grid(row=index+self.srow, column=0, padx=2, pady=2)

        self.content_frames[tabnum].grid_rowconfigure(index+self.srow, weight=1)

        # Type dropdown
        type_var = tk.StringVar(value=build.get('Type', ''))
        type_combo = ttk.Combobox(
            self.content_frames[tabnum],
            textvariable=type_var,
            values=self.colonisation.get_base_types('Initial' if index == 0 else 'Any'),
        )
        type_combo.grid(row=index+self.srow, column=1, padx=2, pady=2, sticky=tk.W)

        # Use a separate function to ensure the correct index is captured
        def on_type_selected(event, tab=tabnum, idx=index, var=type_var):
            self.update_build_type(tab, idx, var)
        type_combo.bind("<<ComboboxSelected>>", on_type_selected)


        if 'MarketID' in build:
            # If name is from journal, display as read-only label
            name_label = ttk.Label(self.content_frames[tabnum], text=build.get('Name', ''))
            name_label.grid(row=index+self.srow, column=2, padx=2, pady=2, sticky=tk.W)
        else:
            # If name is not from journal, provide an entry field
            name_var = tk.StringVar(value=build.get('Name', ''))
            name_entry = ttk.Entry(self.content_frames[tabnum], textvariable=name_var)
            name_entry.grid(row=index+self.srow, column=2, padx=2, pady=2, sticky=tk.W)

            # Use a separate function to ensure the correct index is captured
            def on_name_changed(event, tab=tabnum, idx=index, var=name_var):
                self.update_build_name(tab, idx, var)
            name_entry.bind("<FocusOut>", on_name_changed)

        # Body entry - always editable, identified from SuperCruiseExit event
        body_var = tk.StringVar(value=build.get('Body', ''))
        body_entry = ttk.Entry(self.content_frames[tabnum], textvariable=body_var, width=5)
        body_entry.grid(row=index+self.srow, column=3, padx=2, pady=2, sticky=tk.W)

        # Use a separate function to ensure the correct index is captured
        def on_body_changed(event, tab=tabnum, idx=index, var=body_var):
            self.update_build_body(tab, idx, var)
        body_entry.bind("<FocusOut>", on_body_changed)

        # Get base type info
        base_type = self.colonisation.get_base_type(build.get('Type', ''))
        if not base_type:
            # Skip the rest of the columns if no base type
            return

        # Dependencies as a read-only label
        deps_value = base_type.get('Requirements', '')
        deps_label = ttk.Label(self.content_frames[tabnum], text=deps_value)
        deps_label.grid(row=index+self.srow, column=4, padx=2, pady=2, sticky=tk.W)

        t2 = 0; t3 = 0
        if index > 0:
            t2 = base_type.get('T2 Reward', 0) - base_type.get('T2 Cost', 0)
            t3 = base_type.get('T3 Reward', 0) - base_type.get('T3 Cost', 0)

        # Handle T3 Cost - could be T3 Cost or T3 Reward
        t2_label = ttk.Label(self.content_frames[tabnum], text=str(t2), anchor=tk.CENTER, background=self.get_color(t2, -1, 1))
        #t2_label.configure(background=gradient[0] if t2 < 0 else gradient[19] if t2 > 0 else gradient[19])
        t2_label.grid(row=index+self.srow, column=5, padx=2, pady=2, sticky=tk.NSEW)

        t3_label = ttk.Label(self.content_frames[tabnum], text=str(t3), anchor=tk.CENTER, background=self.get_color(t3, -1, 1))
        t3_label.grid(row=index+self.srow, column=6, padx=2, pady=2, sticky=tk.NSEW)

        loads = ceil(base_type.get('Total Comm', 0) / self.bgstally.state.cargo_capacity)
        t3_label = ttk.Label(self.content_frames[tabnum], text=str(t3), anchor=tk.CENTER, background=self.get_color(t3, -1, 1))
        t3_label.grid(row=index+self.srow, column=6, padx=2, pady=2, sticky=tk.NSEW)

        # Handle remaining attributes
        col = 7
        for attr_key in [
            'Total Comm', 'Loads', 'Pad', 'Facility Economy', 'Pop Inc', 'Pop Max',
            'Economy Influence', 'Security', 'Tech Level', 'Wealth',
            'Standar of Living', 'Dev Level']:
            value = base_type.get(attr_key, '')
            if attr_key == 'Loads': # todo have remaining ?
                value = ceil(base_type.get('Total Comm', 0) / self.bgstally.state.cargo_capacity)

            label = ttk.Label(self.content_frames[tabnum], text=str(value), anchor=tk.CENTER)
            if attr_key not in ('Total Comm', 'Loads', 'Pad', 'Facility Economy', 'Economy Influence'):
                label.configure(background=self.get_color(value, -10, +10))
            label.grid(row=index+self.srow, column=col, padx=2, pady=2, sticky=tk.NSEW)
            col += 1

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
            Debug.logger.debug(f"toggle_all_builds tab {tabnum}")

            systems = self.colonisation.get_all_systems()
            builds = systems[tabnum].get('Builds', [])
            if not builds:
                Debug.logger.debug(f"No builds found for tab {tabnum}")
                return

            # Determine the new state based on the header checkbox
            new_state = 'Yes' if self.track_all_vars[tabnum] else 'No'
            Debug.logger.debug(f"Toggling tracked state for all builds for tab {tabnum} to {new_state}")

            # Update all builds that are not completed
            for build in builds:
                # Skip completed builds
                if self.is_build_completed(build):
                    continue

                build['Tracked'] = new_state

            # Save changes
            self.colonisation.dirty = True
            self.colonisation.save()

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
        Debug.logger.debug(f"Toggling build {tab} {index} to {var.get()}")
        systems = self.colonisation.get_all_systems()
        builds = systems[tab].get('Builds', [])
        if index < 0 or index >= len(builds):
            return

        # Update the build
        builds[index]['Tracked'] = 'Yes' if var.get() else 'No'

        # Save changes
        self.colonisation.dirty = True
        self.colonisation.save()

    def update_build_type(self, tab, index, var):
        """
        Update a build's type

        Args:
            index: The build index
            var: The type variable
        """
        Debug.logger.debug(f"Updating build type {tab} {index} to {var.get()}")

        systems = self.colonisation.get_all_systems()
        builds = systems[tab].get('Builds', [])
        if index < 0:
            Debug.logger.debug(f"Invalid build index {index} for tab {tab} (add new?)")
            return
        if index == len(builds):
            self.add_build(tab, builds)
            systems = self.colonisation.get_all_systems()
            builds = systems[tab].get('Builds', [])

        if var.get() == '<delete me>':
            # Delete the build
            del builds[index]
        else:
            # Update the build
            builds[index]['Type'] = var.get()

        # Save changes
        self.colonisation.dirty = True
        self.colonisation.save()

        # Update the display
        self.update_display()

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
            Debug.logger.debug(f"Invalid build index {index} for tab {tab} (add new?)")
            return

        # Update the build
        builds[index]['Name'] = var.get()

        # Save changes
        self.colonisation.dirty = True
        self.colonisation.save()

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

    def add_build(self, tab, builds):
        """
        Add a new empty build row directly to the table
        """
        try:
            # Add an empty build
            systems = self.colonisation.get_all_systems()
            success = self.colonisation.add_build(systems[tab]['Name'])

            if not success:
                messagebox.showerror(_("Error"), _("Failed to add build"))
                return
            self.colonisation.save()
            self.add_build_row({}, len(builds), tab, 5)

        except Exception as e:
            Debug.logger.error(f"Error in colonisation.show(): {e}")
            Debug.logger.error(traceback.format_exc())

    def add_system_dialog(self):
        """
        Show dialog to add a new system
        """
        try:
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

            # Cancel button
            cancel_button = ttk.Button(
                button_frame,
                text=_("Cancel"),
                command=dialog.destroy
            )
            cancel_button.pack(side=tk.LEFT, padx=5)

            self.tabbar.add(dialog, text='+')

        except Exception as e:
            Debug.logger.error(f"Error in add_system_dialog: {e}")
            Debug.logger.error(traceback.format_exc())

    def add_system(self, plan_name, system_name, dialog):
        """
        Add a new system

        Args:
            plan_name: The system name
            system_name: The display name
            dialog: The dialog to close
        """

        if not plan_name:
            messagebox.showerror(_("Error"), _("Plan name is required"))
            return

        # Add the system
        plan_name = self.colonisation.add_system(plan_name, system_name)
        self.colonisation.save()
        systems = self.colonisation.get_all_systems()

        if not plan_name:
            messagebox.showerror(_("Error"), _("Failed to add system"))
            return

        # Update the display
        tracking_status = self.get_system_tracking_status(plan_name)
        tab = ttk.Frame(self.tabbar)
        tab.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
        self.create_title_frame(tab, len(systems)-1)
        self.create_unified_table_frame(tab, len(systems)-1)
        self.tabbar.add(tab, text=plan_name, compound='right', image=self.image_tab_tracked if tracking_status == "all" else self.image_tab_part_tracked if tracking_status == "partial" else self.image_tab_untracked)
        self.update_display()

        # Close the dialog
        dialog.destroy()


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

        # Confirm removal
        if not messagebox.askyesno(
            _("Confirm Removal"),
            _("Are you sure you want to remove this system?")
        ):
            return

        if tabnum < len(self.colonisation.get_all_systems()):
            Debug.logger.info(f"Deleting system {tabnum}")
            self.colonisation.delete_system(tabnum)
            #self.tabbar.destroy()
            tab.destroy()
            #self.window.forget(self.tabbar)
            self.create_frames()
            self.update_display()

    def open_inara(self, event):
        """
        Open the system in Inara

        Args:
            event: The event that triggered this
        """
        if not self.get_current_system():
            return

        star = self.current_system.get('StarSystem', '')
        if not star:
            return

        # Open the system in Inara
        url = f"https://inara.cz/elite/search/?search={star}"
        webbrowser.open(url)

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
        self.plan_name_labels = []
        self.track_all_vars = []

        # Data storage
        self.planned_labels = []
        self.progress_labels = []


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
            return "#000000"

        value = int(value)
        if value == 0:
            return "lightgray"

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
            ulim=100
            llim=100
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