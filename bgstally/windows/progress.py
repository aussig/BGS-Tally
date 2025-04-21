import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional

from bgstally.constants import FONT_TEXT_BOLD
from bgstally.debug import Debug
from bgstally.utils import _


class ProgressWindow:
    """
    Window for displaying construction progress for Elite Dangerous colonisation
    """
    def __init__(self, parent, colonisation, state):
        """
        Initialize the progress window

        Args:
            parent: The parent window
            colonisation: The Colonisation instance
            state: The BGSTally state
        """
        self.parent = parent
        self.colonisation = colonisation
        self.state = state
        self.window = None
        self.current_build_index = -1  # -1 means "Total" view
        self.current_system = None
        self.ship_cargo_capacity = 100  # Default cargo capacity
        self.show_percentage = True  # Toggle between percentage and ship loads

        # UI components
        self.header_frame = None
        self.navigation_frame = None
        self.commodities_frame = None
        self.progress_frame = None
        self.commodity_labels = {}
        self.required_labels = {}
        self.remaining_labels = {}
        self.carrier_labels = {}

        # Create the window
        self.create_window()

    def create_window(self):
        """
        Create the commodities window
        """
        if self.window is not None:
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title(_("Colonisation Commodities"))
        self.window.geometry("800x600")
        self.window.minsize(600, 400)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        # Create main frames
        self.create_header_frame()
        self.create_navigation_frame()
        self.create_progress_frame()
        self.create_commodities_frame()

        # Load systems and select the first one if available
        systems = self.colonisation.get_all_systems()
        if systems:
            self.select_system(systems[0]['address'])
        else:
            # No systems yet, show empty state
            self.update_display()

    def create_header_frame(self):
        """
        Create the header frame with title
        """
        self.header_frame = ttk.Frame(self.window)
        self.header_frame.pack(fill=tk.X, padx=5, pady=5)

        # System name label
        self.system_name_label = ttk.Label(
            self.header_frame,
            text=_("Colonisation Commodities"),
            font=("TkDefaultFont", 12, "bold")
        )
        self.system_name_label.pack(side=tk.LEFT, padx=10)

        # Ship cargo capacity entry
        cargo_frame = ttk.Frame(self.header_frame)
        cargo_frame.pack(side=tk.RIGHT, padx=10)

        ttk.Label(cargo_frame, text=_("Ship Cargo Capacity:")).pack(side=tk.LEFT, padx=(0, 5))

        self.cargo_var = tk.StringVar(value=str(self.ship_cargo_capacity))
        cargo_entry = ttk.Entry(cargo_frame, textvariable=self.cargo_var, width=5)
        cargo_entry.pack(side=tk.LEFT)
        cargo_entry.bind("<FocusOut>", self.update_cargo_capacity)
        cargo_entry.bind("<Return>", self.update_cargo_capacity)

    def create_navigation_frame(self):
        """
        Create the navigation frame with base selection
        """
        self.navigation_frame = ttk.Frame(self.window)
        self.navigation_frame.pack(fill=tk.X, padx=5, pady=5)

        # Left arrow button
        self.left_button = ttk.Button(
            self.navigation_frame,
            text="←",
            width=3,
            command=self.previous_build
        )
        self.left_button.pack(side=tk.LEFT, padx=5)

        # Current build label
        self.build_label = ttk.Label(
            self.navigation_frame,
            text=_("Total"),
            font=FONT_TEXT_BOLD
        )
        self.build_label.pack(side=tk.LEFT, padx=10, expand=True)

        # Right arrow button
        self.right_button = ttk.Button(
            self.navigation_frame,
            text="→",
            width=3,
            command=self.next_build
        )
        self.right_button.pack(side=tk.LEFT, padx=5)

    def create_progress_frame(self):
        """
        Create the progress frame with total progress
        """
        self.progress_frame = ttk.Frame(self.window)
        self.progress_frame.pack(fill=tk.X, padx=5, pady=5)

        # Progress label
        self.progress_label = ttk.Label(
            self.progress_frame,
            text=_("Total Progress:"),
            font=FONT_TEXT_BOLD
        )
        self.progress_label.pack(side=tk.LEFT, padx=10)

        # Progress value
        self.progress_value = ttk.Label(
            self.progress_frame,
            text="0%"
        )
        self.progress_value.pack(side=tk.LEFT, padx=5)

        # Toggle button
        self.toggle_button = ttk.Button(
            self.progress_frame,
            text=_("Show Ship Loads"),
            command=self.toggle_progress_display
        )
        self.toggle_button.pack(side=tk.RIGHT, padx=10)

    def create_commodities_frame(self):
        """
        Create the commodities frame with scrollable table
        """
        # Create a frame for the table
        table_frame = ttk.Frame(self.window)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create a canvas with scrollbar
        canvas = tk.Canvas(table_frame)
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=canvas.yview)

        # Configure the canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create a frame inside the canvas
        self.commodities_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.commodities_frame, anchor=tk.NW)

        # Configure the canvas to resize with the frame
        self.commodities_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Create the table headers
        self.create_table_headers()

    def create_table_headers(self):
        """
        Create the table headers
        """
        # Clear existing headers
        for widget in self.commodities_frame.winfo_children():
            widget.destroy()

        # Reset label dictionaries
        self.commodity_labels = {}
        self.required_labels = {}
        self.remaining_labels = {}
        self.carrier_labels = {}

        # Create headers
        ttk.Label(
            self.commodities_frame,
            text=_("Commodity"),
            font=FONT_TEXT_BOLD
        ).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        ttk.Label(
            self.commodities_frame,
            text=_("Required"),
            font=FONT_TEXT_BOLD
        ).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(
            self.commodities_frame,
            text=_("Remaining"),
            font=FONT_TEXT_BOLD
        ).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

        ttk.Label(
            self.commodities_frame,
            text=_("Carrier"),
            font=FONT_TEXT_BOLD
        ).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        # Add a separator
        separator = ttk.Separator(self.commodities_frame, orient=tk.HORIZONTAL)
        separator.grid(row=1, column=0, columnspan=4, sticky=tk.EW, pady=5)

    def update_display(self):
        """
        Update the display with current system data
        """
        if not self.current_system:
            # No system selected, show empty state
            self.system_name_label.config(text=_("No System Selected"))
            self.build_label.config(text=_("Total"))
            self.progress_value.config(text="0%")
            self.clear_commodities_table()
            return

        # Update system name
        display_name = self.current_system.get('Name', '')
        system_name = self.current_system.get('System', '')

        if display_name and display_name != system_name:
            title_text = f"{display_name} ({system_name})"
        else:
            title_text = system_name

        self.system_name_label.config(text=title_text)

        # Get builds for the current system
        builds = self.current_system.get('Builds', [])

        # Update navigation
        if self.current_build_index == -1:
            self.build_label.config(text=_("Total"))
        elif 0 <= self.current_build_index < len(builds):
            build = builds[self.current_build_index]
            build_name = build.get('Name', '')
            build_type = build.get('Type', '')
            self.build_label.config(text=f"{build_name} ({build_type})")
        else:
            self.build_label.config(text=_("Unknown"))

        # Update commodities table
        self.update_commodities_table(builds)

    def update_commodities_table(self, builds):
        """
        Update the commodities table with data from the selected build or total
        """
        # Clear existing table
        self.clear_commodities_table()

        # Get commodity requirements
        commodity_data = self.get_commodity_requirements(builds)

        # Calculate total progress
        total_required = sum(data['required'] for data in commodity_data.values())
        total_remaining = sum(data['remaining'] for data in commodity_data.values())
        total_delivered = total_required - total_remaining

        if total_required > 0:
            progress_percent = (total_delivered / total_required) * 100
        else:
            progress_percent = 0

        # Update progress display
        if self.show_percentage:
            self.progress_value.config(text=f"{progress_percent:.1f}%")
        else:
            if self.ship_cargo_capacity > 0:
                ship_loads = total_remaining / self.ship_cargo_capacity
                self.progress_value.config(text=f"{ship_loads:.1f} loads")
            else:
                self.progress_value.config(text="N/A")

        # Add commodities to the table
        row = 2  # Start after the header and separator
        for commodity, data in sorted(commodity_data.items()):
            if data['required'] > 0:  # Only show commodities that are required
                # Commodity name
                commodity_label = ttk.Label(
                    self.commodities_frame,
                    text=commodity
                )
                commodity_label.grid(row=row, column=0, padx=5, pady=2, sticky=tk.W)
                self.commodity_labels[commodity] = commodity_label

                # Required amount
                required_label = ttk.Label(
                    self.commodities_frame,
                    text=str(data['required'])
                )
                required_label.grid(row=row, column=1, padx=5, pady=2, sticky=tk.W)
                self.required_labels[commodity] = required_label

                # Remaining amount
                remaining_label = ttk.Label(
                    self.commodities_frame,
                    text=str(data['remaining'])
                )
                remaining_label.grid(row=row, column=2, padx=5, pady=2, sticky=tk.W)
                self.remaining_labels[commodity] = remaining_label

                # Carrier amount
                carrier_label = ttk.Label(
                    self.commodities_frame,
                    text=str(data['carrier'])
                )
                carrier_label.grid(row=row, column=3, padx=5, pady=2, sticky=tk.W)
                self.carrier_labels[commodity] = carrier_label

                row += 1

    def get_commodity_requirements(self, builds):
        """
        Get the commodity requirements for the selected build or total

        Args:
            builds: List of builds

        Returns:
            Dictionary of commodity requirements
        """
        commodity_data = {}

        # Determine which builds to process
        if self.current_build_index == -1:
            # Process all builds
            builds_to_process = builds
        elif 0 <= self.current_build_index < len(builds):
            # Process only the selected build
            builds_to_process = [builds[self.current_build_index]]
        else:
            builds_to_process = []

        # Process each build
        for build in builds_to_process:
            base_type_name = build.get('Type', '')

            # Find the base cost data for this type
            base_cost = None
            for cost_entry in self.colonisation.base_costs:
                if cost_entry.get('base_type') == base_type_name:
                    base_cost = cost_entry
                    break

            if base_cost:
                # Process each commodity
                for commodity, amount in base_cost.items():
                    if commodity != 'base_type' and amount:
                        # Convert string values with commas to integers
                        try:
                            if isinstance(amount, str) and ',' in amount:
                                amount = amount.replace(',', '')
                            amount = int(amount)
                        except (ValueError, TypeError):
                            amount = 0

                        if amount > 0:
                            # Initialize commodity data if not exists
                            if commodity not in commodity_data:
                                commodity_data[commodity] = {
                                    'required': 0,
                                    'remaining': 0,
                                    'carrier': 0
                                }

                            # Add to required amount
                            commodity_data[commodity]['required'] += amount

                            # Check if this build is being tracked
                            if build.get('Tracked', 'No') == 'Yes':
                                # Get progress from construction depot data
                                market_id = build.get('MarketID')
                                if market_id:
                                    # Find the depot in progress data
                                    for depot in self.colonisation.progress:
                                        if depot.get('MarketID') == market_id:
                                            # Find the resource in the depot
                                            for resource in depot.get('ResourcesRequired', []):
                                                if resource.get('Name') == commodity:
                                                    # Calculate remaining
                                                    required = resource.get('RequiredAmount', 0)
                                                    provided = resource.get('ProvidedAmount', 0)
                                                    remaining = max(0, required - provided)

                                                    # Update commodity data
                                                    commodity_data[commodity]['remaining'] += remaining
                                                    break
                                            break
                            else:
                                # If not tracked, all is remaining
                                commodity_data[commodity]['remaining'] += amount

        # Get carrier inventory
        carrier_inventory = self.get_carrier_inventory()

        # Update carrier amounts
        for commodity, inventory in carrier_inventory.items():
            if commodity in commodity_data:
                commodity_data[commodity]['carrier'] = inventory

        return commodity_data

    def get_carrier_inventory(self):
        """
        Get the carrier inventory

        Returns:
            Dictionary of commodity amounts on the carrier
        """
        # This would normally come from the fleet carrier data
        # For now, return an empty dictionary
        return {}

    def clear_commodities_table(self):
        """
        Clear the commodities table
        """
        # Keep the headers (first two rows)
        for widget in list(self.commodities_frame.winfo_children())[2:]:
            widget.destroy()

        # Reset label dictionaries
        self.commodity_labels = {}
        self.required_labels = {}
        self.remaining_labels = {}
        self.carrier_labels = {}

    def select_system(self, system_address):
        """
        Select a system to display

        Args:
            system_address: The system address to select
        """
        self.current_system = self.colonisation.get_system(system_address)
        self.current_build_index = -1  # Reset to "Total" view
        self.update_display()

    def previous_build(self):
        """
        Navigate to the previous build
        """
        if not self.current_system:
            return

        builds = self.current_system.get('Builds', [])
        if not builds:
            return

        if self.current_build_index == -1:
            # From "Total" go to last build
            self.current_build_index = len(builds) - 1
        else:
            # Go to previous build or to "Total" if at first build
            self.current_build_index = (self.current_build_index - 1) % (len(builds) + 1) - 1

        self.update_display()

    def next_build(self):
        """
        Navigate to the next build
        """
        if not self.current_system:
            return

        builds = self.current_system.get('Builds', [])
        if not builds:
            return

        if self.current_build_index == len(builds) - 1:
            # From last build go to "Total"
            self.current_build_index = -1
        else:
            # Go to next build
            self.current_build_index = (self.current_build_index + 1) % (len(builds) + 1) - 1
            if self.current_build_index < -1:
                self.current_build_index = 0

        self.update_display()

    def toggle_progress_display(self):
        """
        Toggle between percentage and ship loads display
        """
        self.show_percentage = not self.show_percentage

        if self.show_percentage:
            self.toggle_button.config(text=_("Show Ship Loads"))
        else:
            self.toggle_button.config(text=_("Show Percentage"))

        self.update_display()

    def update_cargo_capacity(self, event=None):
        """
        Update the ship cargo capacity

        Args:
            event: The event that triggered this function
        """
        try:
            capacity = int(self.cargo_var.get())
            if capacity > 0:
                self.ship_cargo_capacity = capacity
                self.update_display()
        except ValueError:
            # Reset to previous value
            self.cargo_var.set(str(self.ship_cargo_capacity))

    def close(self):
        """
        Close the window
        """
        if self.window:
            self.window.destroy()
            self.window = None
