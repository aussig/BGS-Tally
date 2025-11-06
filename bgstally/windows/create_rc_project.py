"""
RavenColonial Create Project Dialog
Adapted from Ravencolonial-EDMC plugin
"""

import tkinter as tk
from tkinter import ttk
import tkinter.messagebox
import logging
import requests
import webbrowser
from urllib.parse import quote

from bgstally.debug import Debug
from bgstally.utils import _, catch_exceptions
from bgstally.ravencolonial import RavenColonial, RC_API

logger = logging.getLogger(__name__)


class CreateRCProjectDialog:
    """Dialog for creating a new RavenColonial colonization project"""
    
    def __init__(self, parent, bgstally, system:dict, build:dict, progress:dict):
        """
        Initialize the create project dialog
        
        Args:
            parent: Parent tkinter window
            bgstally: BGSTally main object
            system: System dictionary from colonisation
            build: Build dictionary from colonisation
            progress: Progress dictionary from colonisation
        """
        self.bgstally = bgstally
        self.colonisation = bgstally.colonisation
        self.system = system
        self.build = build
        self.progress = progress
        self.result = None
        
        # Fetch system bodies and sites from RavenColonial
        self.system_bodies = self._fetch_system_bodies()
        self.system_sites = self._fetch_system_sites()
        
        # Create top-level window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Create RavenColonial Project")
        self.dialog.geometry("550x750")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Construction types mapping (from Ravencolonial-EDMC)
        self.construction_types = self._get_construction_types()
        
        # Create widgets
        self._create_widgets()
        self._populate_fields()
    
    def _fetch_system_bodies(self) -> list:
        """Fetch bodies in the system from RavenColonial API"""
        try:
            system_address = self.system.get('SystemAddress')
            if not system_address:
                Debug.logger.debug("No SystemAddress, cannot fetch bodies")
                return []
            
            url = f"{RC_API}/v2/system/{system_address}/bodies"
            Debug.logger.debug(f"Fetching bodies from: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            bodies = response.json()
            Debug.logger.debug(f"Fetched {len(bodies)} bodies")
            return bodies if isinstance(bodies, list) else []
        except Exception as e:
            Debug.logger.error(f"Failed to fetch system bodies: {e}")
            return []
    
    def _fetch_system_sites(self) -> list:
        """Fetch pre-planned sites in the system from RavenColonial API"""
        try:
            system_name = self.system.get('StarSystem')
            if not system_name:
                Debug.logger.debug("No system name, cannot fetch sites")
                return []
            
            url = f"{RC_API}/v2/system/{quote(system_name)}/sites"
            Debug.logger.debug(f"Fetching sites from: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            sites = response.json()
            Debug.logger.debug(f"Fetched {len(sites)} pre-planned sites")
            return sites if isinstance(sites, list) else []
        except Exception as e:
            Debug.logger.error(f"Failed to fetch system sites: {e}")
            return []
    
    def _get_construction_types(self) -> dict:
        """Get the hierarchical construction types dictionary"""
        return {
            # Tier 3 Starports
            "Tier 3: Ocellus Starport": {"Ocellus": "ocellus"},
            "Tier 3: Orbis Starport": {
                "Apollo": "apollo",
                "Artemis": "artemis"
            },
            "Tier 3: Large Planetary Port": {
                "Aphrodite": "aphrodite",
                "Hera": "hera",
                "Poseidon": "poseidon",
                "Zeus": "zeus"
            },
            # Tier 2 Starports
            "Tier 2: Coriolis Starport": {
                "No truss": "no_truss",
                "Dual truss": "dual_truss",
                "Quad truss": "quad_truss"
            },
            "Tier 2: Asteroid Starport": {"Asteroid": "asteroid"},
            # Tier 1 Outposts
            "Tier 1: Civilian Outpost": {"Vesta": "vesta"},
            "Tier 1: Commercial Outpost": {"Plutus": "plutus"},
            "Tier 1: Industrial Outpost": {"Vulcan": "vulcan"},
            "Tier 1: Military Outpost": {"Nemesis": "nemesis"},
            "Tier 1: Scientific Outpost": {"Prometheus": "prometheus"},
            "Tier 1: Pirate Outpost": {"Dysnomia": "dysnomia"},
            # Add more types as needed
        }
    
    def _create_widgets(self):
        """Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        row = 0
        
        # Title
        ttk.Label(main_frame, text=_("New RavenColonial Project"), 
                 font=('TkDefaultFont', 12, 'bold')).grid(row=row, column=0, columnspan=2, pady=(0, 10))
        row += 1
        
        # Location info (read-only)
        ttk.Label(main_frame, text=_("System:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.system_label = ttk.Label(main_frame, text=self.system.get('StarSystem', 'Unknown'))
        self.system_label.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        ttk.Label(main_frame, text=_("Station:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.station_label = ttk.Label(main_frame, text=self.build.get('Name', 'Unknown'))
        self.station_label.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, 
                                                             sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # Build Name
        ttk.Label(main_frame, text=_("Build Name:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.name_var = tk.StringVar(value=self.build.get('Name', ''))
        self.name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=42)
        self.name_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Construction Type (two-dropdown system)
        ttk.Label(main_frame, text=_("Construction Category:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(main_frame, textvariable=self.category_var, 
                                          state='readonly', width=40)
        self.category_combo['values'] = list(self.construction_types.keys())
        self.category_combo.bind('<<ComboboxSelected>>', self._on_category_selected)
        self.category_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Model dropdown (populated when category is selected)
        ttk.Label(main_frame, text=_("Model:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(main_frame, textvariable=self.model_var, 
                                       state='readonly', width=40)
        self.model_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Body dropdown
        ttk.Label(main_frame, text=_("Body:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.body_var = tk.StringVar()
        self.body_combo = ttk.Combobox(main_frame, textvariable=self.body_var, width=40)
        # Populate with bodies from API
        body_options = []
        for body in self.system_bodies:
            body_name = body.get('name', '')
            body_type = body.get('type', '')
            if body_name:
                display_name = f"{body_name} ({body_type})" if body_type else body_name
                body_options.append(display_name)
        
        if body_options:
            self.body_combo['values'] = body_options
            # Pre-select current body if available
            current_body = self.build.get('Body', '')
            if current_body:
                matching = [b for b in body_options if current_body in b]
                if matching:
                    self.body_var.set(matching[0])
                else:
                    self.body_var.set(body_options[0])
            else:
                self.body_var.set(body_options[0])
        elif self.build.get('Body'):
            # Fallback: just show current body
            self.body_combo['values'] = [self.build.get('Body')]
            self.body_var.set(self.build.get('Body'))
        
        self.body_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Architect Name
        ttk.Label(main_frame, text=_("Architect:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.architect_var = tk.StringVar(value=self.system.get('Architect', self.colonisation.cmdr or ''))
        self.architect_entry = ttk.Entry(main_frame, textvariable=self.architect_var, width=42)
        self.architect_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Pre-planned Site Selection (if available)
        if self.system_sites:
            ttk.Label(main_frame, text=_("Pre-planned Site:")).grid(row=row, column=0, sticky=tk.W, pady=2)
            self.site_var = tk.StringVar()
            self.site_combo = ttk.Combobox(main_frame, textvariable=self.site_var, 
                                          state='readonly', width=40)
            site_options = [_("<None - Create New>")]
            self.site_id_map = {_("<None - Create New>"): None}
            self.site_data_map = {_("<None - Create New>"): None}
            
            for site in self.system_sites:
                site_name = site.get('name', 'Unknown')
                site_type = site.get('buildType', '')
                display_name = f"{site_name} ({site_type})"
                site_options.append(display_name)
                self.site_id_map[display_name] = site.get('id')
                self.site_data_map[display_name] = site
            
            self.site_combo['values'] = site_options
            self.site_combo.current(0)
            self.site_combo.bind('<<ComboboxSelected>>', self._on_site_selected)
            self.site_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
            row += 1
        
        # Primary Port checkbox
        self.is_primary_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text=_("This is the primary port in the system"),
                       variable=self.is_primary_var).grid(row=row, column=0, columnspan=2, 
                                                          sticky=tk.W, pady=5)
        row += 1
        
        # Notes
        ttk.Label(main_frame, text=_("Notes:")).grid(row=row, column=0, sticky=(tk.W, tk.N), pady=2)
        self.notes_text = tk.Text(main_frame, width=40, height=6)
        self.notes_text.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Discord Link
        ttk.Label(main_frame, text=_("Discord Link:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.discord_var = tk.StringVar()
        self.discord_entry = ttk.Entry(main_frame, textvariable=self.discord_var, width=42)
        self.discord_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text=_("Create"), command=self._on_create).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=_("Cancel"), command=self._on_cancel).pack(side=tk.LEFT, padx=5)
    
    def _populate_fields(self):
        """Pre-populate fields based on existing build data"""
        # Try to match existing base type to a category/model
        base_type = self.build.get('Base Type', '').lower().replace(' ', '_')
        
        # Search for matching model in construction types
        for category, models in self.construction_types.items():
            for model_name, model_code in models.items():
                if model_code == base_type:
                    self.category_var.set(category)
                    self._on_category_selected()
                    self.model_var.set(model_name)
                    return
    
    def _on_category_selected(self, event=None):
        """Handle category selection - populate model dropdown"""
        category = self.category_var.get()
        if category and category in self.construction_types:
            models = list(self.construction_types[category].keys())
            self.model_combo['values'] = models
            if models:
                self.model_var.set(models[0])  # Auto-select first model
        else:
            self.model_combo['values'] = []
            self.model_var.set('')
    
    def _on_site_selected(self, event=None):
        """Handle pre-planned site selection - auto-populate construction type and body"""
        selected_display = self.site_var.get()
        
        # If "<None - Create New>" is selected, do nothing
        if selected_display == _("<None - Create New>"):
            return
        
        # Get the site data
        site_data = self.site_data_map.get(selected_display)
        if not site_data:
            Debug.logger.warning(f"No site data found for: {selected_display}")
            return
        
        # Auto-populate build type from site
        build_type_code = site_data.get('buildType', '')
        Debug.logger.debug(f"Site selected with buildType: {build_type_code}")
        Debug.logger.debug(f"Site data: {site_data}")
        
        # Try to find matching category and model
        found = False
        for category, models in self.construction_types.items():
            for model_name, model_code in models.items():
                if model_code == build_type_code:
                    Debug.logger.info(f"Found match: category={category}, model={model_name}")
                    
                    # Set the category
                    self.category_var.set(category)
                    
                    # Populate models for this category
                    model_list = list(self.construction_types[category].keys())
                    self.model_combo['values'] = model_list
                    
                    # Set the specific model
                    self.model_var.set(model_name)
                    found = True
                    break
            if found:
                break
        
        if not found:
            Debug.logger.warning(f"No matching construction type found for buildType: {build_type_code}")
        
        # Auto-populate body if available in site data
        body_num = site_data.get('bodyNum')
        Debug.logger.debug(f"Body number from site data: {body_num}")
        Debug.logger.debug(f"Available body options: {self.body_combo['values']}")
        
        if body_num is not None:
            # bodyNum appears to be 1-indexed (starts at 1, not 0)
            body_index = body_num - 1  # Convert to 0-indexed
            Debug.logger.debug(f"Looking for body at bodyNum={body_num} (index {body_index}) in {len(self.system_bodies)} bodies")
            
            matching_body = None
            if 0 <= body_index < len(self.system_bodies):
                matching_body = self.system_bodies[body_index]
                Debug.logger.debug(f"Found body at index {body_index}: {matching_body.get('name')}")
            else:
                Debug.logger.warning(f"bodyNum {body_num} (index {body_index}) is out of range for {len(self.system_bodies)} bodies")
            
            if matching_body:
                body_name = matching_body.get('name', '')
                body_type = matching_body.get('type', '')
                display_name = f"{body_name} ({body_type})" if body_type else body_name
                
                Debug.logger.info(f"Found body for bodyNum {body_num}: {display_name}")
                
                # Try to find in dropdown
                body_options = self.body_combo['values']
                if display_name in body_options:
                    self.body_var.set(display_name)
                    Debug.logger.info(f"Auto-selected body: {display_name}")
                else:
                    # Try partial match
                    matching = [b for b in body_options if body_name in b]
                    if matching:
                        self.body_var.set(matching[0])
                        Debug.logger.info(f"Auto-selected body (partial match): {matching[0]}")
                    else:
                        Debug.logger.warning(f"Body '{display_name}' not found in dropdown options")
            else:
                Debug.logger.warning(f"Could not find body with bodyId {body_num} in fetched bodies")
        else:
            Debug.logger.debug("No bodyNum field found in site data")
        
        # Auto-populate name if available in site data
        site_name = site_data.get('name')
        if site_name:
            self.name_var.set(site_name)
            Debug.logger.info(f"Auto-populated name: {site_name}")
    
    def _on_create(self):
        """Handle Create button click"""
        # Get the selected model's API code
        category = self.category_var.get()
        model = self.model_var.get()
        
        if not category or not model:
            tkinter.messagebox.showerror(_("Error"), _("Please select a construction type and model"))
            return
        
        build_type = self.construction_types.get(category, {}).get(model)
        if not build_type:
            tkinter.messagebox.showerror(_("Error"), _("Invalid construction type selected"))
            return
        
        # Get other fields
        build_name = self.name_var.get().strip()
        body_display = self.body_var.get().strip()
        # Extract body name from "Body Name (Type)" format
        body = body_display.split(' (')[0] if body_display else ''
        
        architect = self.architect_var.get().strip()
        notes = self.notes_text.get("1.0", tk.END).strip()
        discord_link = self.discord_var.get().strip()
        is_primary = self.is_primary_var.get()
        
        if not build_name:
            tkinter.messagebox.showerror(_("Error"), _("Build name is required"))
            return
        
        if not architect:
            tkinter.messagebox.showerror(_("Error"), _("Architect name is required"))
            return
        
        # Update build name if different
        if self.build.get('Name') != build_name:
            self.colonisation.modify_build(self.system, self.build.get('BuildID'), {'Name': build_name})
        
        # Update build with selected type if different
        if self.build.get('Layout') != build_type:
            self.colonisation.modify_build(self.system, self.build.get('BuildID'), {
                'Layout': build_type,
                'Base Type': f"{category} - {model}"
            })
        
        # Update system architect if different
        if self.system.get('Architect') != architect:
            self.colonisation.modify_system(self.system, {'Architect': architect})
        
        # Update body if provided
        if body and self.build.get('Body') != body:
            self.colonisation.modify_build(self.system, self.build.get('BuildID'), {'Body': body})
        
        Debug.logger.info(f"Creating RavenColonial project: {self.build.get('Name')}, Type: {build_type}")
        
        # Call RavenColonial create_project
        try:
            RavenColonial(self.colonisation).create_project(self.system, self.build, self.progress)
            
            # Get the project ID that was just created
            project_id = self.progress.get('ProjectID')
            
            tkinter.messagebox.showinfo(
                _("Success"),
                _("RavenColonial project created successfully!\n\nOpening build page in browser...")
            )
            
            # Open the build page in browser
            if project_id:
                url = f"https://ravencolonial.com/#build={project_id}"
                Debug.logger.info(f"Opening RavenColonial build page: {url}")
                webbrowser.open(url)
            
            self.result = True
            self.dialog.destroy()
        except Exception as e:
            Debug.logger.error(f"Failed to create project: {e}")
            tkinter.messagebox.showerror(
                _("Error"),
                _("Failed to create project. Check EDMC logs for details.")
            )
    
    def _on_cancel(self):
        """Handle Cancel button click"""
        self.result = False
        self.dialog.destroy()
