import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from bgstally.constants import CheckStates
from bgstally.debug import Debug
from bgstally.utils import _


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
        self.systems = {}     # Systems with colonisation data
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
            base_types_path = os.path.join(self.bgstally.plugin_dir, 'data', 'base_types.json')
            with open(base_types_path, 'r') as f:
                self.base_types = json.load(f)
                Debug.logger.info(f"Loaded {len(self.base_types)} base types for colonisation")
        except Exception as e:
            Debug.logger.error(f"Error loading base types: {e}")
            self.base_types = {}

    def load_base_costs(self):
        """
        Load base cost definitions from base_costs.json
        """
        try:
            base_costs_path = os.path.join(self.bgstally.plugin_dir, 'data', 'base_costs.json')
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

    def get_all_base_types(self) -> List[str]:
        """
        Get a list of all base type names

        Returns:
            List of base type names
        """
        return list(self.base_types.keys())

    def system_claimed(self, entry: Dict, state):
        """
        Handle ColonisationSystemClaim event

        Args:
            entry: The journal entry
            state: The BGSTally state
        """
        system_name = entry.get('StarSystem', '')
        system_address = str(entry.get('SystemAddress', ''))

        if not system_name or not system_address:
            Debug.logger.warning(f"Invalid ColonisationSystemClaim event: {entry}")
            return

        # Create or update system
        if system_address not in self.systems:
            self.systems[system_address] = {
                'Name': system_name,
                'System': system_name,
                'SystemAddress': system_address,
                'Claimed': entry.get('timestamp', datetime.now().isoformat()),
                'BeaconDeployed': '',
                'Builds': []
            }
        else:
            self.systems[system_address]['Claimed'] = entry.get('timestamp', datetime.now().isoformat())

        self.dirty = True
        Debug.logger.info(f"System claimed: {system_name}")

    def beacon_deployed(self, entry: Dict, state):
        """
        Handle ColonisationBeaconDeployed event

        Args:
            entry: The journal entry
            state: The BGSTally state
        """
        system_name = entry.get('StarSystem', '')
        system_address = str(entry.get('SystemAddress', ''))

        if not system_name or not system_address:
            Debug.logger.warning(f"Invalid ColonisationBeaconDeployed event: {entry}")
            return

        # Create or update system
        if system_address not in self.systems:
            self.systems[system_address] = {
                'Name': system_name,
                'System': system_name,
                'SystemAddress': system_address,
                'Claimed': '',
                'BeaconDeployed': entry.get('timestamp', datetime.now().isoformat()),
                'Builds': []
            }
        else:
            self.systems[system_address]['BeaconDeployed'] = entry.get('timestamp', datetime.now().isoformat())

        self.dirty = True
        Debug.logger.info(f"Beacon deployed in system: {system_name}")

    def construction_depot(self, entry: Dict, state):
        """
        Handle ColonisationConstructionDepot event

        Args:
            entry: The journal entry
            state: The BGSTally state
        """
        system_name = entry.get('StarSystem', '')
        system_address = str(entry.get('SystemAddress', ''))
        market_id = entry.get('MarketID')
        timestamp = entry.get('timestamp', datetime.now().isoformat())
        building_type = entry.get('BuildingType', 'Unknown')
        building_name = entry.get('BuildingName', f"New Construction {market_id}")
        body = entry.get('Body', '')
        resources_required = entry.get('ResourcesRequired', [])

        if not system_name or not system_address or not market_id:
            Debug.logger.warning(f"Invalid ColonisationConstructionDepot event: {entry}")
            return

        # Create a comprehensive progress entry
        progress_entry = {
            'MarketID': market_id,
            'SystemAddress': system_address,
            'SystemName': system_name,
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

        # Create or update system
        if system_address not in self.systems:
            self.systems[system_address] = {
                'Name': system_name,
                'System': system_name,
                'SystemAddress': system_address,
                'Claimed': '',
                'BeaconDeployed': '',
                'Builds': []
            }

        # Check if build exists with this MarketID
        build_exists = False
        for build in self.systems[system_address]['Builds']:
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
            self.systems[system_address]['Builds'].append({
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
        Debug.logger.info(f"Construction depot established in system: {system_name}, MarketID: {market_id}")

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

        self.dirty = True
        # Save immediately to ensure we don't lose any data
        self.save()
        Debug.logger.info(f"Contribution made to construction: {commodity} x{quantity}, MarketID: {market_id}")

    def update_system_info(self, entry: Dict, state):
        """
        Update system information from standard ED events

        Args:
            entry: The journal entry
            state: The BGSTally state
        """
        system_name = entry.get('StarSystem', '')
        system_address = str(entry.get('SystemAddress', ''))

        if not system_name or not system_address:
            return

        # Update existing system if we're tracking it
        if system_address in self.systems:
            # Just ensure the name is correct
            self.systems[system_address]['System'] = system_name
            self.dirty = True

    def add_system(self, system_name: str, display_name: str = '', system_address: str = '') -> str:
        """
        Add a new system for colonisation planning

        Args:
            system_name: The name of the system
            display_name: A custom display name for the system
            system_address: The system address (if known)

        Returns:
            The system address of the added system
        """
        # Generate a temporary system address if not provided
        internal_address = system_address
        if not internal_address:
            # Use timestamp as a temporary unique ID
            internal_address = str(int(datetime.now().timestamp()))

        # Create new system
        system_data = {
            'Name': display_name if display_name else system_name,
            'System': system_name,
            'Claimed': '',
            'BeaconDeployed': '',
            'Builds': []
        }

        # Only include SystemAddress if it's a real one from the game
        if system_address:
            system_data['SystemAddress'] = system_address

        self.systems[internal_address] = system_data

        self.dirty = True
        Debug.logger.info(f"Added system for colonisation planning: {system_name}")
        return internal_address

    def add_build(self, system_address: str, build_type: str = "", name: str = "", body: str = "") -> bool:
        """
        Add a new build to a system

        Args:
            system_address: The system address
            build_type: The type of build (can be empty for a new row)
            name: The name of the build
            body: The body where the build is located

        Returns:
            True if successful, False otherwise
        """
        if system_address not in self.systems:
            Debug.logger.warning(f"Cannot add build - system not found: {system_address}")
            return False

        # Only validate build_type if it's not empty
        if build_type and build_type not in self.base_types:
            Debug.logger.warning(f"Cannot add build - unknown build type: {build_type}")
            return False

        # Add new build
        self.systems[system_address]['Builds'].append({
            'Tracked': 'No',
            'Type': build_type,
            'Name': name,
            'Body': body
        })

        self.dirty = True
        Debug.logger.info(f"Added new build row to system {self.systems[system_address]['System']}")
        return True

    def remove_build(self, system_address: str, build_index: int) -> bool:
        """
        Remove a build from a system

        Args:
            system_address: The system address
            build_index: The index of the build to remove

        Returns:
            True if successful, False otherwise
        """
        if system_address not in self.systems:
            Debug.logger.warning(f"Cannot remove build - system not found: {system_address}")
            return False

        builds = self.systems[system_address]['Builds']
        if build_index < 0 or build_index >= len(builds):
            Debug.logger.warning(f"Cannot remove build - invalid build index: {build_index}")
            return False

        # Remove build
        removed_build = builds.pop(build_index)

        self.dirty = True
        Debug.logger.info(f"Removed build {removed_build.get('Name', '')} from system {self.systems[system_address]['System']}")
        return True

    def get_system_builds(self, system_address: str) -> List[Dict]:
        """
        Get all builds for a system

        Args:
            system_address: The system address

        Returns:
            List of builds for the system
        """
        if system_address not in self.systems:
            return []

        return self.systems[system_address]['Builds']

    def get_all_systems(self) -> List[Dict]:
        """
        Get all systems being tracked for colonisation

        Returns:
            List of systems
        """
        return [
            {
                'address': address,
                'name': system['System'],
                'display_name': system['Name'],
                'claimed': system['Claimed'] != '',
                'beacon_deployed': system['BeaconDeployed'] != '',
                'build_count': len(system['Builds'])
            }
            for address, system in self.systems.items()
        ]

    def get_system(self, system_address: str) -> Optional[Dict]:
        """
        Get a system by address

        Args:
            system_address: The system address

        Returns:
            The system data or None if not found
        """
        return self.systems.get(system_address)

    def save(self):
        """
        Save colonisation data to file
        """
        if not self.dirty:
            return

        try:
            # Save systems data
            systems_path = os.path.join(self.bgstally.plugin_dir, 'otherdata', 'colonisation.json')

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
            Debug.logger.info(f"Saved colonisation data: {len(self.systems)} systems, {len(self.progress)} construction depots")
        except Exception as e:
            Debug.logger.error(f"Error saving colonisation data: {e}")

    def load(self):
        """
        Load colonisation data from file
        """
        try:
            systems_path = os.path.join(self.bgstally.plugin_dir, 'otherdata', 'colonisation.json')
            if not os.path.exists(systems_path):
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
