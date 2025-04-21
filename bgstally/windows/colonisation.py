import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from typing import Dict, List, Optional

from bgstally.constants import FONT_HEADING_1, FONT_TEXT, FONT_TEXT_BOLD
from bgstally.debug import Debug
from bgstally.utils import _


class ColonisationWindow:
    """
    Window for managing Elite Dangerous colonisation
    """
    def __init__(self, parent, colonisation):
        """
        Initialize the colonisation window

        Args:
            parent: The parent window
            colonisation: The Colonisation instance
        """
        self.parent = parent
        self.colonisation = colonisation
        self.window = None
        self.current_system = None

        # UI components
        self.header_frame = None
        self.system_tabs = None
        self.title_frame = None
        self.summary_frame = None
        self.table_frame = None
        self.table = None

        # Create the window
        self.create_window()

    def create_window(self):
        """
        Create the colonisation window
        """
        if self.window is not None:
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title(_("Elite Dangerous Colonisation"))
        self.window.geometry("1200x800")
        self.window.minsize(1000, 600)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        # Create main frames
        self.create_header_frame()
        self.create_title_frame()
        self.create_summary_frame()
        self.create_table_frame()

        # Load systems and select the first one if available
        systems = self.colonisation.get_all_systems()
        if systems:
            self.select_system(systems[0]['address'])
        else:
            # No systems yet, show empty state
            self.update_display()

    def create_header_frame(self):
        """
        Create the header frame with system tabs
        """
        self.header_frame = ttk.Frame(self.window)
        self.header_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        # Create system tabs
        self.system_tabs = ttk.Frame(self.header_frame)
        self.system_tabs.pack(fill=tk.X, side=tk.LEFT)

        # Add button
        add_button = ttk.Button(self.header_frame, text="+", width=3, command=self.add_system_dialog)
        add_button.pack(side=tk.LEFT, padx=(5, 0))

        # Navigation buttons
        nav_frame = ttk.Frame(self.header_frame)
        nav_frame.pack(side=tk.RIGHT)

        prev_button = ttk.Button(nav_frame, text="<", width=3, command=self.prev_system)
        prev_button.pack(side=tk.LEFT)

        menu_button = ttk.Button(nav_frame, text="≡", width=3, command=self.show_menu)
        menu_button.pack(side=tk.LEFT, padx=2)

        next_button = ttk.Button(nav_frame, text=">", width=3, command=self.next_system)
        next_button.pack(side=tk.LEFT)

        # Update system tabs
        self.update_system_tabs()

    def create_title_frame(self):
        """
        Create the title frame with system name and tick info
        """
        self.title_frame = ttk.Frame(self.window, style="Title.TFrame")
        self.title_frame.pack(fill=tk.X, padx=0, pady=(0, 5))

        # Configure style for title frame
        style = ttk.Style()
        style.configure("Title.TFrame", background="#e0b0e0")

        # System name label
        self.system_name_label = ttk.Label(
            self.title_frame,
            text="",
            font=FONT_HEADING_1,
            foreground="#800080",
            background="#e0b0e0"
        )
        self.system_name_label.pack(side=tk.LEFT, padx=10, pady=5)

        # Inara link
        self.inara_link = ttk.Label(
            self.title_frame,
            text="Inara →",
            font=FONT_TEXT,
            foreground="blue",
            cursor="hand2",
            background="#e0b0e0"
        )
        self.inara_link.pack(side=tk.LEFT, padx=10, pady=5)
        self.inara_link.bind("<Button-1>", self.open_inara)

    def create_summary_frame(self):
        """
        Create the summary frame with system statistics
        """
        self.summary_frame = ttk.Frame(self.window)
        self.summary_frame.pack(fill=tk.X, padx=5, pady=5)

        # Create grid layout for summary
        # Row 1: Headers
        headers = [
            "Total Build", "Orbital", "Surface",
            "T2", "T3", "Total Commodities", "Loads", "Pad", "Facility Economy",
            "Pop Inc", "Pop Max", "Economy Influence", "Security", "Tech Level",
            "Wealth", "Standard of Living", "Dev Level"
        ]

        # Function to split header text for wrapping
        def split_header(header_text):
            # If the header contains a space, split at the space
            if " " in header_text:
                parts = header_text.split(" ", 1)
                return parts[0], parts[1]
            # If it's a single long word, split at a reasonable point
            elif len(header_text) > 10:
                mid_point = len(header_text) // 2
                return header_text[:mid_point], header_text[mid_point:]
            # Short single words don't need splitting
            else:
                return header_text, ""

        # Create headers with wrapping for long or multi-word headers
        for i, header in enumerate(headers):
            # Determine if this header needs wrapping
            if len(header) > 10 or " " in header:
                # Split the header text
                first_line, second_line = split_header(header)

                # Create a frame for this header to contain both lines
                header_cell_frame = ttk.Frame(self.summary_frame)
                header_cell_frame.grid(row=0, column=i, padx=2, pady=2, sticky=tk.W+tk.E)

                # Add the two lines of text
                ttk.Label(
                    header_cell_frame,
                    text=first_line,
                    font=FONT_TEXT_BOLD,
                    anchor=tk.W
                ).pack(fill=tk.X)

                if second_line:
                    ttk.Label(
                        header_cell_frame,
                        text=second_line,
                        font=FONT_TEXT_BOLD,
                        anchor=tk.W
                    ).pack(fill=tk.X)
            else:
                # Single line header
                label = ttk.Label(self.summary_frame, text=header, font=FONT_TEXT_BOLD)
                label.grid(row=0, column=i, padx=2, pady=2, sticky=tk.W)

        # Row 2: Planned values
        self.planned_labels = {}
        for i in range(len(headers)):
            label = ttk.Label(self.summary_frame, text="0")
            label.grid(row=1, column=i, padx=2, pady=2, sticky=tk.W)
            self.planned_labels[headers[i]] = label

        # Row 3: Progress label
        progress_label = ttk.Label(self.summary_frame, text="Progress", font=FONT_TEXT_BOLD)
        progress_label.grid(row=2, column=0, padx=2, pady=2, sticky=tk.W)

        # Row 4: Progress values
        self.progress_labels = {}
        for i in range(len(headers)):
            label = ttk.Label(self.summary_frame, text="0")
            label.grid(row=3, column=i, padx=2, pady=2, sticky=tk.W)
            self.progress_labels[headers[i]] = label

    def create_table_frame(self):
        """
        Create the table frame with the builds list
        """
        self.table_frame = ttk.Frame(self.window)
        self.table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Headers
        headers = [
            "Track", "Type", "Name", "Body", "Dependencies", "T2 Cost", "T3 Cost",
            "Total Commodities", "Loads", "Pad", "Facility Economy", "Pop Inc", "Pop Max",
            "Economy Influence", "Security", "Tech Level", "Wealth",
            "Standard of Living", "Dev Level"
        ]

        # Calculate column widths
        widths = [8, 20, 20, 15, 20, 8, 8, 15, 8, 8, 15, 8, 8, 15, 8, 10, 8, 15, 10]

        # Configure the table frame to resize with the window
        self.table_frame.columnconfigure(0, weight=1)
        self.table_frame.rowconfigure(0, weight=1)

        # Create a frame that will contain both headers and the scrollable content
        main_content_frame = ttk.Frame(self.table_frame)
        main_content_frame.grid(row=0, column=0, sticky=tk.NSEW)
        main_content_frame.columnconfigure(0, weight=1)
        main_content_frame.rowconfigure(1, weight=1)  # Row 1 (canvas_frame) should expand

        # Create headers frame
        headers_frame = ttk.Frame(main_content_frame)
        headers_frame.grid(row=0, column=0, sticky=tk.EW)

        # Configure header columns to resize proportionally with minimum widths
        for i in range(len(headers)):
            # Set minimum width in pixels (approximately 6 pixels per character)
            min_width = max(widths[i] * 6, 30)  # Ensure at least 30 pixels
            headers_frame.columnconfigure(i, weight=1, minsize=min_width)

        # Function to split header text for wrapping
        def split_header(header_text):
            # If the header contains a space, split at the space
            if " " in header_text:
                parts = header_text.split(" ", 1)
                return parts[0], parts[1]
            # If it's a single long word, split at a reasonable point
            elif len(header_text) > 10:
                mid_point = len(header_text) // 2
                return header_text[:mid_point], header_text[mid_point:]
            # Short single words don't need splitting
            else:
                return header_text, ""

        # Create headers with wrapping for long or multi-word headers
        for i, header in enumerate(headers):
            # Special case for "Track" header - add a checkbox
            if i == 0:  # First column is "Track"
                header_cell_frame = ttk.Frame(headers_frame)
                header_cell_frame.grid(row=0, column=i, padx=2, pady=2, sticky=tk.W+tk.E)

                # Add the header text
                ttk.Label(
                    header_cell_frame,
                    text=header,
                    font=FONT_TEXT_BOLD,
                    anchor=tk.CENTER
                ).pack(fill=tk.X)

                # Add the "check all" checkbox
                self.track_all_var = tk.BooleanVar(value=False)
                track_all_check = ttk.Checkbutton(
                    header_cell_frame,
                    variable=self.track_all_var,
                    command=self.toggle_all_builds
                )
                track_all_check.pack(fill=tk.X)
            # Handle other headers with wrapping for long or multi-word headers
            elif len(header) > 10 or " " in header:
                # Split the header text
                first_line, second_line = split_header(header)

                # Create a frame for this header to contain both lines
                header_cell_frame = ttk.Frame(headers_frame)
                header_cell_frame.grid(row=0, column=i, padx=2, pady=2, sticky=tk.W+tk.E)

                # Add the two lines of text
                ttk.Label(
                    header_cell_frame,
                    text=first_line,
                    font=FONT_TEXT_BOLD,
                    anchor=tk.CENTER
                ).pack(fill=tk.X)

                if second_line:
                    ttk.Label(
                        header_cell_frame,
                        text=second_line,
                        font=FONT_TEXT_BOLD,
                        anchor=tk.CENTER
                    ).pack(fill=tk.X)
            else:
                # Single line header
                label = ttk.Label(headers_frame, text=header, font=FONT_TEXT_BOLD)
                label.grid(row=0, column=i, padx=2, pady=2, sticky=tk.W+tk.E)

        # Create scrollable frame for builds
        canvas_frame = ttk.Frame(main_content_frame)
        canvas_frame.grid(row=1, column=0, sticky=tk.NSEW)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.builds_canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.builds_canvas.yview)
        self.builds_frame = ttk.Frame(self.builds_canvas)

        # Configure the builds frame columns to match headers with minimum widths
        for i in range(len(headers)):
            # Set minimum width in pixels (approximately 6 pixels per character)
            min_width = max(widths[i] * 6, 30)  # Ensure at least 30 pixels
            self.builds_frame.columnconfigure(i, weight=1, minsize=min_width)

        self.builds_frame.bind(
            "<Configure>",
            lambda e: self.builds_canvas.configure(scrollregion=self.builds_canvas.bbox("all"))
        )

        # Bind canvas resize to update the window width
        self.builds_canvas.bind("<Configure>", self._on_canvas_configure)

        self.builds_canvas.create_window((0, 0), window=self.builds_frame, anchor=tk.NW)
        self.builds_canvas.configure(yscrollcommand=scrollbar.set)

        self.builds_canvas.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        # Add buttons frame at the bottom
        buttons_frame = ttk.Frame(self.table_frame)
        buttons_frame.grid(row=1, column=0, sticky=tk.EW, pady=(5, 0))

        # Add button - directly adds a new row without showing a dialog
        add_build_button = ttk.Button(buttons_frame, text=_("Add Row"), command=self.add_empty_build)
        add_build_button.pack(side=tk.LEFT, padx=2, pady=2)

    def update_system_tabs(self):
        """
        Update the system tabs based on available systems
        """
        # Clear existing tabs
        for widget in self.system_tabs.winfo_children():
            widget.destroy()

        # Add tabs for each system
        systems = self.colonisation.get_all_systems()
        for i, system in enumerate(systems):
            # Create a frame for the tab
            tab_frame = ttk.Frame(self.system_tabs)
            tab_frame.pack(side=tk.LEFT, padx=(0 if i == 0 else 2, 0))

            # Create the tab button
            tab_text = system['display_name'] if system['display_name'] else system['name']
            if len(tab_text) > 20:
                tab_text = tab_text[:17] + "..."

            # Determine tracking status for this system
            tracking_status = self.get_system_tracking_status(system['address'])

            # Set the appropriate icon based on tracking status
            if tracking_status == "all":
                status_icon = "☑"  # All builds tracked
            elif tracking_status == "partial":
                status_icon = "⊟"  # Some builds tracked
            else:
                status_icon = "☐"  # No builds tracked

            tab_button = ttk.Button(
                tab_frame,
                text=f"{tab_text} {status_icon}",
                command=lambda addr=system['address']: self.select_system(addr)
            )
            tab_button.pack(fill=tk.X)

            # Highlight current system
            if self.current_system and system['address'] == self.current_system['SystemAddress']:
                tab_button.state(['pressed'])

    def update_display(self):
        """
        Update the display with current system data
        """
        if not self.current_system:
            # No system selected, show empty state
            self.system_name_label.config(text=_("No System Selected"))
            self.clear_summary()
            self.clear_builds_table()
            return

        # Update title with both display name and actual system name
        display_name = self.current_system.get('Name', '')
        system_name = self.current_system['System']

        if display_name and display_name != system_name:
            title_text = f"{display_name} ({system_name})"
        else:
            title_text = system_name

        self.system_name_label.config(text=title_text)

        # Update summary
        self.update_summary()

        # Update builds table
        self.update_builds_table()

    def update_summary(self):
        """
        Update the summary section with current system data
        """
        if not self.current_system:
            self.clear_summary()
            return

        # Calculate summary values
        builds = self.current_system.get('Builds', [])

        # Count planned vs progress
        planned_count = 0
        progress_count = 0

        # Count orbital vs surface
        orbital_count = 0
        surface_count = 0

        # Other totals
        total_comm = 0
        loads = 0
        pads = {'Small': 0, 'Medium': 0, 'Large': 0}
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
        t2_count = 0
        t3_count = 0

        # Process each build
        for build in builds:
            # Get base type info
            base_type = self.colonisation.get_base_type(build.get('Type', ''))
            if not base_type:
                continue

            # Count as planned or progress
            if build.get('Tracked', 'No') == 'Yes':
                progress_count += 1
            else:
                planned_count += 1

            # Count as orbital or surface
            if base_type.get('Location', '') == 'Orbital':
                orbital_count += 1
            else:
                surface_count += 1

            # Add to other totals
            total_comm += int(base_type.get('Total Comm', 0))
            loads += int(base_type.get('Loads', 0))

            # Count pad types
            pad_type = base_type.get('Pad', '')
            if pad_type in pads:
                pads[pad_type] += 1

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
            tier = int(base_type.get('Tier', 1))
            if tier == 2:
                t2_count += 1
            elif tier == 3:
                t3_count += 1

        # Update planned labels
        self.planned_labels["Total Build"].config(text=str(planned_count))
        self.planned_labels["Orbital"].config(text=str(orbital_count))
        self.planned_labels["Surface"].config(text=str(surface_count))
        self.planned_labels["T2"].config(text=str(t2_count))
        self.planned_labels["T3"].config(text=str(t3_count))
        self.planned_labels["Total Commodities"].config(text=str(total_comm))
        self.planned_labels["Loads"].config(text=str(loads))

        # Pad count display
        pad_text = f"{pads['Small']}/{pads['Medium']}/{pads['Large']}"
        self.planned_labels["Pad"].config(text=pad_text)

        # Economy display
        main_economy = max(economies.items(), key=lambda x: x[1])[0] if economies else ""
        self.planned_labels["Facility Economy"].config(text=main_economy)

        # Population
        self.planned_labels["Pop Inc"].config(text=str(pop_inc))
        self.planned_labels["Pop Max"].config(text=str(pop_max))

        # Economy influence
        main_influence = max(economy_influences.items(), key=lambda x: x[1])[0] if economy_influences else ""
        self.planned_labels["Economy Influence"].config(text=main_influence)

        # Other metrics
        self.planned_labels["Security"].config(text=str(security))
        self.planned_labels["Tech Level"].config(text=str(tech_level))
        self.planned_labels["Wealth"].config(text=str(wealth))
        self.planned_labels["Standard of Living"].config(text=str(standard_of_living))
        self.planned_labels["Dev Level"].config(text=str(dev_level))

        # Update progress labels - for now just show zeros
        for key in self.progress_labels:
            self.progress_labels[key].config(text="0")

    def clear_summary(self):
        """
        Clear the summary section
        """
        for key in self.planned_labels:
            self.planned_labels[key].config(text="0")

        for key in self.progress_labels:
            self.progress_labels[key].config(text="0")

    def update_builds_table(self):
        """
        Update the builds table with current system data
        """
        # Clear existing builds
        self.clear_builds_table()

        if not self.current_system:
            return

        # Get builds for the current system
        builds = self.current_system.get('Builds', [])

        # Calculate column widths
        widths = [8, 20, 20, 15, 20, 8, 8, 15, 8, 8, 15, 8, 8, 15, 8, 10, 8, 15, 10]

        # Add each build to the table
        for i, build in enumerate(builds):
            # Get base type info
            base_type = self.colonisation.get_base_type(build.get('Type', ''))
            if not base_type:
                continue

            # Capture the current index
            build_index = i

            # Check if the build is completed
            is_completed = self.is_build_completed(build)

            # Track checkbox or completed indicator
            if is_completed:
                # For completed builds, show a read-only checkmark button
                track_button = ttk.Button(
                    self.builds_frame,
                    text="✓",
                    state="disabled"
                )
                track_button.grid(row=i, column=0, padx=2, pady=2, sticky=tk.W+tk.E)
            else:
                # For builds in progress, show a checkbox
                complete_var = tk.BooleanVar(value=build.get('Tracked', 'No') == 'Yes')
                complete_check = ttk.Checkbutton(
                    self.builds_frame,
                    variable=complete_var,
                    command=lambda idx=build_index, var=complete_var: self.toggle_build_complete(idx, var)
                )
                complete_check.grid(row=i, column=0, padx=2, pady=2, sticky=tk.W+tk.E)

            # Type dropdown
            type_var = tk.StringVar(value=build.get('Type', ''))
            type_combo = ttk.Combobox(
                self.builds_frame,
                textvariable=type_var,
                values=self.colonisation.get_all_base_types(),
                width=widths[1]
            )
            type_combo.grid(row=i, column=1, padx=2, pady=2, sticky=tk.W+tk.E)

            # Use a separate function to ensure the correct index is captured
            def on_type_selected(event, idx=build_index, var=type_var):
                self.update_build_type(idx, var)
            type_combo.bind("<<ComboboxSelected>>", on_type_selected)

            # Name field - editable if not determined from journal entries
            name_value = build.get('Name', '')
            # Check if name is from a journal entry
            is_journal_name = any(prefix in name_value for prefix in [
                "Orbital Construction Site:",
                "Planetary Construction Site:",
                "$EXT_PANEL_ColonisationShip:"
            ])

            if is_journal_name:
                # If name is from journal, display as read-only label
                name_label = ttk.Label(self.builds_frame, text=name_value)
                name_label.grid(row=i, column=2, padx=2, pady=2, sticky=tk.W+tk.E)
            else:
                # If name is not from journal, provide an entry field
                name_var = tk.StringVar(value=name_value)
                name_entry = ttk.Entry(self.builds_frame, textvariable=name_var, width=widths[2])
                name_entry.grid(row=i, column=2, padx=2, pady=2, sticky=tk.W+tk.E)

                # Use a separate function to ensure the correct index is captured
                def on_name_changed(event, idx=build_index, var=name_var):
                    self.update_build_name(idx, var)
                name_entry.bind("<FocusOut>", on_name_changed)

            # Body entry - always editable, identified from SuperCruiseExit event
            body_var = tk.StringVar(value=build.get('Body', ''))
            body_entry = ttk.Entry(self.builds_frame, textvariable=body_var, width=widths[3])
            body_entry.grid(row=i, column=3, padx=2, pady=2, sticky=tk.W+tk.E)

            # Use a separate function to ensure the correct index is captured
            def on_body_changed(event, idx=build_index, var=body_var):
                self.update_build_body(idx, var)
            body_entry.bind("<FocusOut>", on_body_changed)

            # Dependencies as a read-only label
            deps_value = build.get('Dependencies', '')
            deps_label = ttk.Label(self.builds_frame, text=deps_value)
            deps_label.grid(row=i, column=4, padx=2, pady=2, sticky=tk.W+tk.E)

            # Handle T2 Cost - could be T2 Cost or T2 Reward
            t2_cost = base_type.get('T2 Cost', '')
            if not t2_cost and 'T2 Reward' in base_type:
                t2_cost = base_type['T2 Reward']
            t2_label = ttk.Label(self.builds_frame, text=str(t2_cost))
            t2_label.grid(row=i, column=5, padx=2, pady=2, sticky=tk.W+tk.E)

            # Handle T3 Cost - could be T3 Cost or T3 Reward
            t3_cost = base_type.get('T3 Cost', '')
            if not t3_cost and 'T3 Reward' in base_type:
                t3_cost = base_type['T3 Reward']
            t3_label = ttk.Label(self.builds_frame, text=str(t3_cost))
            t3_label.grid(row=i, column=6, padx=2, pady=2, sticky=tk.W+tk.E)

            # Handle remaining attributes
            col = 7
            for attr_key, display_name in [
                ('Total Comm', 'Total Commodities'),
                ('Loads', 'Loads'),
                ('Pad', 'Pad'),
                ('Facility Economy', 'Facility Economy'),
                ('Pop Inc', 'Pop Inc'),
                ('Pop Max', 'Pop Max'),
                ('Economy Influence', 'Economy Influence'),
                ('Security', 'Security'),
                ('Tech Level', 'Tech Level'),
                ('Wealth', 'Wealth'),
                ('Standard of Living', 'Standard of Living'),
                ('Dev Level', 'Dev Level')
            ]:
                value = base_type.get(attr_key, '')
                label = ttk.Label(self.builds_frame, text=str(value))
                label.grid(row=i, column=col, padx=2, pady=2, sticky=tk.W+tk.E)
                col += 1

    def clear_builds_table(self):
        """
        Clear the builds table
        """
        for widget in self.builds_frame.winfo_children():
            widget.destroy()

    def select_system(self, system_address):
        """
        Select a system to display

        Args:
            system_address: The system address to select
        """
        self.current_system = self.colonisation.get_system(system_address)
        self.update_system_tabs()
        self.update_display()

    def add_system_dialog(self):
        """
        Show dialog to add a new system
        """
        dialog = tk.Toplevel(self.window)
        dialog.title(_("Add System"))
        dialog.geometry("400x200")
        dialog.transient(self.window)
        dialog.grab_set()

        # System name
        ttk.Label(dialog, text=_("System Name:")).grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        system_name_var = tk.StringVar()
        system_name_entry = ttk.Entry(dialog, textvariable=system_name_var, width=30)
        system_name_entry.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)

        # Display name
        ttk.Label(dialog, text=_("Display Name (optional):")).grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        display_name_var = tk.StringVar()
        display_name_entry = ttk.Entry(dialog, textvariable=display_name_var, width=30)
        display_name_entry.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)

        ttk.Button(
            button_frame,
            text=_("Cancel"),
            command=dialog.destroy
        ).pack(side=tk.LEFT, padx=10)

        ttk.Button(
            button_frame,
            text=_("Add"),
            command=lambda: self.add_system(system_name_var.get(), display_name_var.get(), dialog)
        ).pack(side=tk.LEFT, padx=10)

        # Focus on system name entry
        system_name_entry.focus_set()

    def add_system(self, system_name, display_name, dialog):
        """
        Add a new system

        Args:
            system_name: The system name
            display_name: The display name
            dialog: The dialog to close
        """
        if not system_name:
            messagebox.showerror(_("Error"), _("System name is required"))
            return

        # Add the system
        system_address = self.colonisation.add_system(system_name, display_name)

        # Close the dialog
        dialog.destroy()

        # Select the new system
        self.select_system(system_address)

        # Save changes
        self.colonisation.save()

    def add_build_dialog(self):
        """
        Show dialog to add a new build
        """
        if not self.current_system:
            messagebox.showerror(_("Error"), _("No system selected"))
            return

        dialog = tk.Toplevel(self.window)
        dialog.title(_("Add Build"))
        dialog.geometry("400x250")
        dialog.transient(self.window)
        dialog.grab_set()

        # Build type
        ttk.Label(dialog, text=_("Build Type:")).grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        build_type_var = tk.StringVar()
        build_type_combo = ttk.Combobox(dialog, textvariable=build_type_var, width=30)
        build_type_combo['values'] = self.colonisation.get_all_base_types()
        build_type_combo.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)

        # Name
        ttk.Label(dialog, text=_("Name:")).grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)

        # Body
        ttk.Label(dialog, text=_("Body:")).grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        body_var = tk.StringVar()
        body_entry = ttk.Entry(dialog, textvariable=body_var, width=30)
        body_entry.grid(row=2, column=1, padx=10, pady=10, sticky=tk.W)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Button(
            button_frame,
            text=_("Cancel"),
            command=dialog.destroy
        ).pack(side=tk.LEFT, padx=10)

        ttk.Button(
            button_frame,
            text=_("Add"),
            command=lambda: self.add_build(build_type_var.get(), name_var.get(), body_var.get(), dialog)
        ).pack(side=tk.LEFT, padx=10)

        # Focus on build type combo
        build_type_combo.focus_set()

    def add_empty_build(self):
        """
        Add a new empty build row directly to the table
        """
        if not self.current_system:
            messagebox.showerror(_("Error"), _("No system selected"))
            return

        # Add an empty build
        success = self.colonisation.add_build(
            self.current_system['SystemAddress']
        )

        if not success:
            messagebox.showerror(_("Error"), _("Failed to add build"))
            return

        # Update the display
        self.update_display()

        # Save changes
        self.colonisation.save()

    def add_build(self, build_type, name, body, dialog):
        """
        Add a new build

        Args:
            build_type: The build type
            name: The build name
            body: The body
            dialog: The dialog to close
        """
        if not build_type:
            messagebox.showerror(_("Error"), _("Build type is required"))
            return

        if not name:
            messagebox.showerror(_("Error"), _("Name is required"))
            return

        # Add the build
        success = self.colonisation.add_build(
            self.current_system['SystemAddress'],
            build_type,
            name,
            body
        )

        if not success:
            messagebox.showerror(_("Error"), _("Failed to add build"))
            return

        # Close the dialog
        dialog.destroy()

        # Update the display
        self.update_display()

        # Save changes
        self.colonisation.save()

    def remove_build(self):
        """
        Remove the selected build
        """
        # TODO: Implement build selection and removal
        messagebox.showinfo(_("Info"), _("Build removal not yet implemented"))

    def toggle_all_builds(self):
        """
        Toggle all builds' tracking status
        """
        if not self.current_system:
            return

        builds = self.current_system.get('Builds', [])
        if not builds:
            return

        # Determine the new state based on the header checkbox
        new_state = 'Yes' if self.track_all_var.get() else 'No'

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

    def toggle_build_complete(self, index, var):
        """
        Toggle a build's tracking status

        Args:
            index: The build index
            var: The checkbox variable
        """
        if not self.current_system:
            return

        builds = self.current_system.get('Builds', [])
        if index < 0 or index >= len(builds):
            return

        # Update the build
        builds[index]['Tracked'] = 'Yes' if var.get() else 'No'

        # Save changes
        self.colonisation.dirty = True
        self.colonisation.save()

        # Update the display
        self.update_display()

    def update_build_type(self, index, var):
        """
        Update a build's type

        Args:
            index: The build index
            var: The type variable
        """
        if not self.current_system:
            return

        builds = self.current_system.get('Builds', [])
        if index < 0 or index >= len(builds):
            return

        # Update the build
        builds[index]['Type'] = var.get()

        # Save changes
        self.colonisation.dirty = True
        self.colonisation.save()

        # Update the display
        self.update_display()

    def update_build_name(self, index, var):
        """
        Update a build's name

        Args:
            index: The build index
            var: The name variable
        """
        if not self.current_system:
            return

        builds = self.current_system.get('Builds', [])
        if index < 0 or index >= len(builds):
            return

        # Update the build
        builds[index]['Name'] = var.get()

        # Save changes
        self.colonisation.dirty = True
        self.colonisation.save()

    def update_build_body(self, index, var):
        """
        Update a build's body

        Args:
            index: The build index
            var: The body variable
        """
        if not self.current_system:
            return

        builds = self.current_system.get('Builds', [])
        if index < 0 or index >= len(builds):
            return

        # Update the build
        builds[index]['Body'] = var.get()

        # Save changes
        self.colonisation.dirty = True
        self.colonisation.save()

    def update_build_notes(self, index, var):
        """
        Update a build's notes

        Args:
            index: The build index
            var: The notes variable
        """
        if not self.current_system:
            return

        builds = self.current_system.get('Builds', [])
        if index < 0 or index >= len(builds):
            return

        # Update the build
        builds[index]['Notes'] = var.get()

        # Save changes
        self.colonisation.dirty = True
        self.colonisation.save()

    def update_build_dependencies(self, index, var):
        """
        Update a build's dependencies

        Args:
            index: The build index
            var: The dependencies variable
        """
        if not self.current_system:
            return

        builds = self.current_system.get('Builds', [])
        if index < 0 or index >= len(builds):
            return

        # Update the build
        builds[index]['Dependencies'] = var.get()

        # Save changes
        self.colonisation.dirty = True
        self.colonisation.save()

    def prev_system(self):
        """
        Select the previous system
        """
        if not self.current_system:
            return

        systems = self.colonisation.get_all_systems()
        if not systems:
            return

        # Find current system index
        current_index = -1
        for i, system in enumerate(systems):
            if system['address'] == self.current_system['SystemAddress']:
                current_index = i
                break

        if current_index == -1:
            return

        # Select previous system
        prev_index = (current_index - 1) % len(systems)
        self.select_system(systems[prev_index]['address'])

    def next_system(self):
        """
        Select the next system
        """
        if not self.current_system:
            return

        systems = self.colonisation.get_all_systems()
        if not systems:
            return

        # Find current system index
        current_index = -1
        for i, system in enumerate(systems):
            if system['address'] == self.current_system['SystemAddress']:
                current_index = i
                break

        if current_index == -1:
            return

        # Select next system
        next_index = (current_index + 1) % len(systems)
        self.select_system(systems[next_index]['address'])

    def show_menu(self):
        """
        Show the system menu
        """
        if not self.current_system:
            return

        menu = tk.Menu(self.window, tearoff=0)
        menu.add_command(label=_("Rename System"), command=self.rename_system_dialog)
        menu.add_command(label=_("Delete System"), command=self.delete_system)
        menu.add_separator()
        menu.add_command(label=_("Copy System Name"), command=self.copy_system_name)
        menu.add_command(label=_("Copy System Address"), command=self.copy_system_address)

        # Display the menu
        menu.post(self.window.winfo_pointerx(), self.window.winfo_pointery())

    def rename_system_dialog(self):
        """
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
        display_name_var = tk.StringVar(value=self.current_system.get('Name', ''))
        display_name_entry = ttk.Entry(dialog, textvariable=display_name_var, width=30)
        display_name_entry.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=1, column=0, columnspan=2, pady=20)

        ttk.Button(
            button_frame,
            text=_("Cancel"),
            command=dialog.destroy
        ).pack(side=tk.LEFT, padx=10)

        ttk.Button(
            button_frame,
            text=_("Rename"),
            command=lambda: self.rename_system(display_name_var.get(), dialog)
        ).pack(side=tk.LEFT, padx=10)

        # Focus on display name entry
        display_name_entry.focus_set()

    def rename_system(self, display_name, dialog):
        """
        Rename a system

        Args:
            display_name: The new display name
            dialog: The dialog to close
        """
        if not self.current_system:
            return

        # Update the system
        self.current_system['Name'] = display_name

        # Close the dialog
        dialog.destroy()

        # Update the display
        self.update_system_tabs()

        # Save changes
        self.colonisation.dirty = True
        self.colonisation.save()

    def delete_system(self):
        """
        Delete the current system
        """
        if not self.current_system:
            return

        # Confirm deletion
        if not messagebox.askyesno(
            _("Confirm Deletion"),
            _("Are you sure you want to delete this system? This action cannot be undone.")
        ):
            return

        # Get system address
        system_address = self.current_system['SystemAddress']

        # Delete the system
        del self.colonisation.systems[system_address]

        # Save changes
        self.colonisation.dirty = True
        self.colonisation.save()

        # Select another system if available
        systems = self.colonisation.get_all_systems()
        if systems:
            self.select_system(systems[0]['address'])
        else:
            self.current_system = None
            self.update_display()

        # Update system tabs
        self.update_system_tabs()

    def copy_system_name(self):
        """
        Copy the system name to clipboard
        """
        if not self.current_system:
            return

        self.window.clipboard_clear()
        self.window.clipboard_append(self.current_system['System'])

    def copy_system_address(self):
        """
        Copy the system address to clipboard
        """
        if not self.current_system:
            return

        self.window.clipboard_clear()
        self.window.clipboard_append(self.current_system['SystemAddress'])

    def open_inara(self, event=None):
        """
        Open the system in Inara
        """
        if not self.current_system:
            return

        system_name = self.current_system['System']
        url = f"https://inara.cz/elite/search/?search={system_name}"
        webbrowser.open(url)

    def _on_canvas_configure(self, event):
        """
        Handle canvas resize event to update the window width

        Args:
            event: The configure event
        """
        # Update the window width to match the canvas width
        if event.width > 1:  # Avoid setting to 1 which can happen during initialization
            self.builds_canvas.itemconfig(self.builds_canvas.find_withtag("all")[0], width=event.width)

    def get_system_tracking_status(self, system_address):
        """
        Get the tracking status for a system

        Args:
            system_address: The system address

        Returns:
            "all" if all non-completed builds are tracked
            "partial" if some non-completed builds are tracked
            "none" if no non-completed builds are tracked
        """
        system = self.colonisation.get_system(system_address)
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

    def close(self):
        """
        Close the window
        """
        if self.window:
            self.window.destroy()
            self.window = None
