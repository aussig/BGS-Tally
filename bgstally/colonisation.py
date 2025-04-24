import json
from os import path
from datetime import datetime
from typing import Dict, List, Optional

from bgstally.constants import FOLDER_OTHER_DATA, FOLDER_DATA, CheckStates
from bgstally.debug import Debug
from bgstally.utils import _

FILENAME = "colonisation.json"
BASE_TYPES_FILENAME = 'base_types.json'
BASE_COSTS_FILENAME = 'base_costs.json'
class Colonisation:
    """
    Manages colonisation data and events for Elite Dangerous colonisation
    """
    def __init__(self, bgstally):
        """
        Initialize the Colonisation manager

        Args:
            bgstally: The BGSTally instance
        """
        self.bgstally = bgstally
        self.base_types = {}  # Loaded from base_types.json
        self.base_costs = []  # Loaded from base_costs.json
        self.systems = []     # Systems with colonisation data
        self.progress = []    # Construction progress data
        self.dirty = False

        # Load base types, costs, and saved data
        self.load_base_types()
        self.load_base_costs()
        self.load()

    def load_base_types(self):
        """
        Load base type definitions from base_types.json
        """
        try:
            base_types_path = path.join(self.bgstally.plugin_dir, FOLDER_DATA, BASE_TYPES_FILENAME)
            with open(base_types_path, 'r') as f:
                self.base_types = json.load(f)
                self.base_types['<delete me>'] = {}
                Debug.logger.info(f"Loaded {len(self.base_types)} base types for colonisation")
        except Exception as e:
            Debug.logger.error(f"Error loading base types: {e}")
            self.base_types = {}

    def load_base_costs(self):
        """
        Load base cost definitions from base_costs.json
        """
        try:
            base_costs_path = path.join(self.bgstally.plugin_dir, FOLDER_DATA, BASE_COSTS_FILENAME)
            with open(base_costs_path, 'r') as f:
                self.base_costs = json.load(f)
                Debug.logger.info(f"Loaded {len(self.base_costs)} base costs for colonisation")

                # Update base_types with total commodity counts from base_costs
                self.update_base_types_with_costs()
        except Exception as e:
            Debug.logger.error(f"Error loading base costs: {e}")
            self.base_costs = []

    def update_base_types_with_costs(self):
        """
        Update base_types with total commodity counts from base_costs
        """
        for base_cost in self.base_costs:
            base_type_name = base_cost.get('base_type', '')
            if base_type_name in self.base_types:
                # Calculate total commodities
                total_comm = 0
                for key, value in base_cost.items():
                    if key != 'base_type' and value:
                        try:
                            # Handle values with commas (e.g., "3,912")
                            if isinstance(value, str) and ',' in value:
                                value = value.replace(',', '')
                            total_comm += int(value)
                        except (ValueError, TypeError):
                            # Skip non-numeric values
                            pass

                # Update base_type with total commodities
                self.base_types[base_type_name]['Total Comm'] = total_comm

    def get_base_type(self, type_name: str) -> Dict:
        """
        Get a base type by name

        Args:
            type_name: The name of the base type

        Returns:
            The base type definition or an empty dict if not found
        """
        return self.base_types.get(type_name, {})

    def get_base_types(self, category:str = 'Any') -> List[str]:
        """
        Get a list of all base type names

        Returns:
            List of base type names
        """
        if category == 'Any':
            return list(self.base_types.keys())
        if category == 'Initial':
            return [base_type for base_type in self.base_types if self.base_types[base_type].get('Category') in ['Starport', 'Outpost']]

        return [base_type for base_type in self.base_types if self.base_types[base_type].get('Category') == category]

    def find_or_create_system(self, name, addr):
        system = self.get_system('SystemAddress', addr)
        if system == None:
            system = self.get_system('StarSystem', name)
        if system == None:
            system = self.get_system('Name', name)

        if system is None:
            system = {
                'Name': name,
                'StarSystem' : name,
                'SystemAddress' : addr,
                'Builds': []
            }
            self.systems.append(system)
            self.dirty = True

        return system

    def find_or_create_build(self, system, market, name):
        build = None
        for b in system['Builds']:
            if b.get('MarketID', '') == market:
                build = b
                break
            if b.get('Name', '') == name:
                build = b
                break

        if build == None:
            build = {
                'Name': name,
                'MarketID': market
            }
            system['Builds'].append(build)
            self.dirty = True
        return build


    def system_claimed(self, entry: Dict, state):
        """
        Handle ColonisationSystemClaim event

        Args:
            entry: The journal entry
            state: The BGSTally state
        """
        system = self.find_or_create_system(entry.get('StarSystem', ''), entry.get('SystemAddress', ''))

        system['SystemAddress'] = entry.get('SystemAddress', '')
        system['Claimed'] = entry.get('timestamp', datetime.now().isoformat())
        system['BeaconDeployed'] = ''

        self.dirty = True
        Debug.logger.info(f"System claimed: {entry.get('StarSystem', '')}")


    def docked(self, entry: Dict, state):
        """
        Handle dock event. This gives us info the other colonisation events do not.
        """

        system = self.find_or_create_system(entry.get('StarSystem'), entry.get('SystemAddress'))
        name = None
        if entry.get('StationName', '') == '"$EXT_PANEL_ColonisationShip:#index=1;':
            name = entry.get('StationName_Localised')
            type = 'Orbital'
        elif 'Orbital Construction Site: ' in entry.get('StationName', ''):
            name = entry.get('StationName', '')
            name = name.replace('Orbital Construction Site: ', '')
            type = 'Orbital'
        elif 'Planetary Construction Site: ' in entry.get('StationName', ''):
            name = entry.get('StationName', '')
            name = name.replace('Planetary Construction Site: ', '')
            type = 'Planetary'

        # This is not a docking even we care about
        if name == None:
            return

        build = self.find_or_create_build(entry, system, entry.get('MarketID'), name)
        build['Name'] = name
        build['MarketID'] = entry.get('MarketID')
        build['Type'] = type
        build['Economy'] =entry.get('StationEconomy', '')
        self.dirty = True

    def construction_depot(self, entry: Dict, state):
        """
        Handle ColonisationConstructionDepot event

        Args:
            entry: The journal entry
            state: The BGSTally state
        """
        system_name = str(entry.get('StarSystem', ''))
        system_address = str(entry.get('SystemAddress', ''))
        market_id = entry.get('MarketID')
        timestamp = entry.get('timestamp', datetime.now().isoformat())
        building_type = entry.get('BuildingType', 'Unknown')
        building_name = entry.get('BuildingName', f"New Construction {market_id}")
        body = entry.get('Body', '')
        resources_required = entry.get('ResourcesRequired', [])

        if not system_name or not market_id:
            Debug.logger.warning(f"Invalid ColonisationConstructionDepot event: {entry}")
            return
        system = self.get_system('SystemAddress', system_address)
        if system is None:
            Debug.logger.warning(f"ColonisationConstructionDepot event for unknown system: {entry}")
            return

        # Create a comprehensive progress entry
        progress_entry = {
            'MarketID': market_id,
            'StarSystem': system_name,
            'SystemName': system_address,
            'Timestamp': timestamp,
            'BuildingType': building_type,
            'BuildingName': building_name,
            'Body': body,
            'ConstructionProgress': 0.0,
            'ConstructionComplete': False,
            'ConstructionFailed': False,
            'ResourcesRequired': resources_required,
            'EventData': entry  # Store the complete event data for reference
        }

        # Update progress tracking
        depot_exists = False
        for i, depot in enumerate(self.progress):
            if depot.get('MarketID') == market_id:
                depot_exists = True
                # Update existing depot with new comprehensive data
                self.progress[i] = progress_entry
                break

        if not depot_exists:
            # Add new depot
            self.progress.append(progress_entry)

        # Check if build exists with this MarketID
        build_exists = False
        for build in system['Builds']:
            if build.get('MarketID') == market_id:
                build_exists = True
                # Update existing build with latest information
                build['Tracked'] = 'Yes'
                build['Type'] = building_type
                build['Name'] = building_name
                build['Body'] = body
                # Add reference to progress entry
                build['ProgressRef'] = market_id
                break

        if not build_exists:
            # Add new build with reference to progress entry
            system['Builds'].append({
                'MarketID': market_id,
                'ProgressRef': market_id,
                'Tracked': 'Yes',
                'Type': building_type,
                'Name': building_name,
                'Body': body
            })

        self.dirty = True
        # Save immediately to ensure we don't lose any data
        self.save()
        Debug.logger.info(f"Construction depot established in system: {plan_name}, MarketID: {market_id}")

    def contribution(self, entry: Dict, state):
        """
        Handle ColonisationContribution event

        Args:
            entry: The journal entry
            state: The BGSTally state
        """
        market_id = entry.get('MarketID')
        commodity = entry.get('Commodity', '')
        quantity = entry.get('Quantity', 0)
        timestamp = entry.get('timestamp', datetime.now().isoformat())

        if not market_id or not commodity or quantity <= 0:
            Debug.logger.warning(f"Invalid ColonisationContribution event: {entry}")
            return

        # Update progress tracking
        depot_updated = False
        for i, depot in enumerate(self.progress):
            if depot.get('MarketID') == market_id:
                # Store the contribution event
                if 'ContributionEvents' not in depot:
                    depot['ContributionEvents'] = []

                # Add this contribution to the history
                contribution_event = {
                    'Timestamp': timestamp,
                    'Commodity': commodity,
                    'Quantity': quantity,
                    'EventData': entry  # Store the complete event data
                }
                depot['ContributionEvents'].append(contribution_event)

                # Update resource provided amount
                for resource in depot.get('ResourcesRequired', []):
                    if resource.get('Name') == commodity:
                        resource['ProvidedAmount'] = resource.get('ProvidedAmount', 0) + quantity
                        break

                # Calculate overall progress
                total_required = 0
                total_provided = 0
                for resource in depot.get('ResourcesRequired', []):
                    total_required += resource.get('RequiredAmount', 0)
                    total_provided += resource.get('ProvidedAmount', 0)

                if total_required > 0:
                    depot['ConstructionProgress'] = (total_provided / total_required) * 100.0

                # Check if construction is complete
                if total_provided >= total_required:
                    depot['ConstructionComplete'] = True
                    depot['CompletionTimestamp'] = timestamp

                depot_updated = True
                break

        if not depot_updated:
            Debug.logger.warning(f"Contribution event for unknown depot: MarketID {market_id}")
            return

        self.dirty = True
        # Save immediately to ensure we don't lose any data
        self.save()

    def update_system_info(self, entry: Dict, state):
        """
        Update system information from standard ED events

        Args:
            entry: The journal entry
            state: The BGSTally state
        """
        plan_name = entry.get('Name', '')

        if not plan_name:
            return

        # Update existing system if we're tracking it
        system = self.get_system('Name', plan_name)
        if system is None:
            Debug.logger.warning(f"Update system info for unknown system: {entry}")
            return

        for k,v in entry.items():
            if k in ['Name', 'System', 'Claimed', 'BeaconDeployed']:
                continue
            if k in system:
                system[k] = v
        self.dirty = True

    def add_system(self, plan_name: str, system_name: str = '') -> str:
        """
        Add a new system for colonisation planning

        Args:
            plan_name: A custom display name for the system
            system_name: The system name (if known)

        Returns:
            The system address of the added system
        """
        if self.get_system('Name', plan_name) is not None:
            Debug.logger.warning(f"Cannot add system - already exists: {plan_name}")
            return False

        # Create new system
        system_data = {
            'Name': plan_name,
            'System': system_name,
            'Claimed': '',
            'BeaconDeployed': '',
            'Builds': []
        }

        self.systems.append(system_data)

        self.dirty = True
        return plan_name

    def delete_system(self, index):
        del self.systems[index]
        self.dirty = True

        return True


    def add_build(self, plan_name: str, build_type: str = "", name: str = "", body: str = "") -> bool:
        """
        Add a new build to a system

        Args:
            system_name: The system address
            build_type: The type of build (can be empty for a new row)
            name: The name of the build
            body: The body where the build is located

        Returns:
            True if successful, False otherwise
        """

        # Only validate build_type if it's not empty
        if build_type and build_type not in self.base_types:
            Debug.logger.warning(f"Cannot add build - unknown build type: {build_type}")
            return False

        system = self.get_system('Name', plan_name)
        if system is None:
            Debug.logger.warning(f"Cannot add build - unknown system: {plan_name}")
            return False

        system['Builds'].append({
            'Tracked': 'No',
            'Type': build_type,
            'Name': name,
            'Body': body
        })

        self.dirty = True
        return True

    def remove_build(self, plan_name: str, build_index: int) -> bool:
        """
        Remove a build from a system

        Args:
            system_name: The system address
            build_index: The index of the build to remove

        Returns:
            True if successful, False otherwise
        """
        system = self.get_system('Name', plan_name)
        if system is None:
            Debug.logger.warning(f"Cannot remove build - unknown system: {plan_name}")
            return False

        builds = system['Builds']
        if build_index < 0 or build_index >= len(builds):
            Debug.logger.warning(f"Cannot remove build - invalid build index: {build_index}")
            return False

        # Remove build
        removed_build = builds.pop(build_index)

        self.dirty = True
        return True


    def get_all_systems(self) -> List[Dict]:
        """
        Get all systems being tracked for colonisation

        Returns:
            List of systems
        """

        return self.systems

    def get_system(self, key: str, value: str) -> Optional[Dict]:
        """
        Get a system by address

        Args:
            system_name: The system address

        Returns:
            The system data or None if not found
        """
        for i, system in enumerate(self.systems):
            if system.get(key) == value:
                return system
        return None

    def load(self):
        """
        Load state from file
        """
        file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        if path.exists(file):
            try:
                with open(file) as json_file:
                    self._from_dict(json.load(json_file))
            except Exception as e:
                Debug.logger.warning(f"Unable to load {file}")

    def save(self):
        """
        Save state to file
        """
        file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)

        with open(file, 'w') as outfile:
            json.dump(self._as_dict(), outfile)

    def _as_dict(self):
        """
        Return a Dictionary representation of our data, suitable for serializing
        """
        return {
            'Progress': self.progress,
            'Systems': self.systems,
            }


    def _from_dict(self, dict: dict):
        """
        Populate our data from a Dictionary that has been deserialized
        """
        self.progress = dict.get('Progress', [])
        self.systems = dict.get('Systems', [])

    def save_xx(self):
        """
        Save colonisation data to file
        """
        if not self.dirty:
            return

        try:
            # Save systems data
            systems_path = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)

            # Create a copy of the systems data for saving
            systems_to_save = []
            for system_key, system_data in self.systems.items():
                # Create a copy of the system data
                system_copy = system_data.copy()

                # Add to the list for saving
                systems_to_save.append(system_copy)

            data = {
                'Systems': systems_to_save,
                'Progress': self.progress
            }

            with open(systems_path, 'w') as f:
                json.dump(data, f, indent=4)

            self.dirty = False

        except Exception as e:
            Debug.logger.error(f"Error saving colonisation data: {e}")

    def load_xx(self):
        """
        Load colonisation data from file
        """
        try:
            systems_path = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
            if not path.exists(systems_path):
                Debug.logger.info("No colonisation data file found, starting fresh")
                return

            with open(systems_path, 'r') as f:
                data = json.load(f)

            # Process systems
            self.systems = {}
            for system in data.get('Systems', []):
                # For systems with a real SystemAddress, use that as the key
                if 'SystemAddress' in system:
                    self.systems[system['SystemAddress']] = system
                # For manually added systems without a SystemAddress, generate a temporary key
                else:
                    # Use system name and timestamp to create a unique key
                    temp_key = str(int(datetime.now().timestamp()))
                    self.systems[temp_key] = system
                    Debug.logger.debug(f"Assigned temporary key {temp_key} to system {system.get('System', 'Unknown')}")

            # Process progress
            self.progress = data.get('Progress', [])

            Debug.logger.info(f"Loaded colonisation data: {len(self.systems)} systems, {len(self.progress)} construction depots")
        except Exception as e:
            Debug.logger.error(f"Error loading colonisation data: {e}")
            self.systems = {}
            self.progress = []
