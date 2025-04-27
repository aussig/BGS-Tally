import json
from os import path
from os.path import join
import traceback
from datetime import datetime
from typing import Dict, List, Optional

from bgstally.constants import FOLDER_OTHER_DATA, FOLDER_DATA, BuildStatus, CheckStates
from bgstally.debug import Debug
from bgstally.utils import _
from config import config

FILENAME = "colonisation.json"
BASE_TYPES_FILENAME = 'base_types.json'
BASE_COSTS_FILENAME = 'base_costs.json'
CARGO_FILENAME = "Cargo.json"

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
        self.system_id = None
        self.docked = False
        self.base_types = {}  # Loaded from base_types.json
        self.base_costs = {}  # Loaded from base_costs.json
        self.systems = []     # Systems with colonisation data
        self.progress = []    # Construction progress data
        self.dirty = False

        self.cargo ={}
        self.carrier_cargo = {}
        self.market = {}

        # Load base types, costs, and saved data
        self.load_base_types()
        self.load_base_costs()
        self.update_cargo()
        self.update_carrier()
        self.update_market()

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
                for base_type in self.base_costs.keys():
                    if base_type in self.base_types:
                        self.base_types[base_type]['Total Comm'] = sum(self.base_costs[base_type].values())

        except Exception as e:
            Debug.logger.error(f"New Error loading base costs: {e}")
            Debug.logger.error(traceback.format_exc())
            self.base_costs = {}


    def journal_entry(self, cmdr, is_beta, system, station, entry, state):
        """
        Parse an incoming journal entry and store the data we need
        """
        Debug.logger.debug(f"journal_entry called {entry.get('event')}")
        try:
            match entry.get('event'):
                case 'Cargo':
                    self.update_cargo()

                case 'ColonisationSystemClaim':
                    system = self.find_or_create_system(entry.get('StarSystem', ''), entry.get('SystemAddress', ''))

                    system['StarSystem'] = entry.get('StarSystem', '')
                    system['SystemAddress'] = entry.get('SystemAddress', '')
                    system['Claimed'] = entry.get('timestamp', datetime.now().isoformat())
                    system['BeaconDeployed'] = ''

                    self.dirty = True
                    Debug.logger.info(f"System claimed: {entry.get('StarSystem', '')}")

                case 'ColonisationConstructionDepot':
                    #system = self.find_or_create_system(entry.get('StarSystem', ''), entry.get('SystemAddress', ''))
                    market_id = entry.get('MarketID')

                    if not market_id:
                        Debug.logger.info(f"Invalid ColonisationConstructionDepot event: {entry}")
                        return

                    progress = self.find_or_create_progress(market_id)

                    progress['Updated'] = entry.get('TimeStamp')
                    progress['ConstructionProgress'] = entry.get('ConstructionProgress')
                    progress['ResourcesRequired'] = entry.get('ResourcesRequired')
                    self.dirty = True

                case 'ColonisationContribution':
                    self.contribution(entry, state)

                case 'Docked':
                    self.update_market()
                    self.update_cargo()
                    self.update_carrier()

                    self.docked = True
                    if entry.get('StationName', '') == '"$EXT_PANEL_ColonisationShip:#index=1;':
                        name = entry.get('StationName_Localised')
                        type = 'Orbital'
                        status = BuildStatus.PROGRESS

                    elif 'Orbital Construction Site: ' in entry.get('StationName', ''):
                        name = entry.get('StationName', '')
                        name = name.replace('Orbital Construction Site: ', '')
                        type = 'Orbital'
                        status = BuildStatus.PROGRESS

                    elif 'Planetary Construction Site: ' in entry.get('StationName', ''):
                        name = entry.get('StationName', '')
                        name = name.replace('Planetary Construction Site: ', '')
                        type = 'Planetary'
                        status = BuildStatus.PROGRESS

                    else:
                        name = entry.get('StationName')
                        status = BuildStatus.COMPLETE

                    if status == BuildStatus.PROGRESS:
                        system = self.find_or_create_system(entry.get('StarSystem'), entry.get('SystemAddress'))
                        # Just in case
                        if not 'Name' in system:
                            system['Name'] = entry.get('StarSystem')

                        system['StarSystem'] = entry.get('StarSystem')
                        system['SystemAddress'] = entry.get('SystemAddress')

                        build = self.find_or_create_build(entry, system, entry.get('MarketID'), name)
                        build['Name'] = entry.get('StationName_Localised')
                        build['MarketID'] = entry.get('MarketID')
                        build['Location'] = type
                        build['State'] = status
                        build['Economy'] = entry.get('StationEconomy', '')
                        if self.bgstally.state.current_body != None:
                            build['Body'] = self.bgstally.state.body
                        self.dirty = True

                    # If we land at a build of ours that's completed then update it.
                    if status == BuildStatus.COMPLETE:
                        system = self.get_system('SystemAddress', entry.get('SystemAddress'))
                        if system is not None:
                            Debug.logger.debug(f"Our system: {system['Name']}")

                            build = self.get_build(system, entry.get('MarketID'), entry.get('StationName'))
                            if build is not None:
                                Debug.logger.debug(f"Our build: {build['Name']}")

                                build['State'] = status
                                build['MarketID'] = entry.get('MarketID')
                                if self.bgstally.state.current_body != None:
                                    build['Body'] = self.bgstally.state.body
                    self.dirty = True

                case 'Undocked':
                    self.update_market()
                    self.update_cargo()
                    self.update_carrier()

                    self.docked = False
                    self.dirty = True

            # Save immediately to ensure we don't lose any data
            if self.dirty:
                self.bgstally.ui.window_progress.update_display()
                self.save()

        except Exception as e:
            Debug.logger.error(f"Error processing event: {e}")
            Debug.logger.error(traceback.format_exc())

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
            str: The key to search
            value: The value to search for

        Returns:
            The system data or None if not found
        """
        for i, system in enumerate(self.systems):
            if system.get(key) == value:
                return system

        return None

    def get_system_tracking(self, system) -> List[Dict]:
        status = 'All'
        any = False
        for b in system['Builds']:
            if b.get('Track', 'No') == 'Yes':
                any = True
            else:
                status = 'Partial'

        if any == False:
            return 'None'

        return status


    def find_or_create_system(self, name, addr):
        Debug.logger.debug(f"find_or_create_system entered {name} {addr}")
        system = self.get_system('SystemAddress', addr)
        if system == None:
            system = self.get_system('StarSystem', name)
        if system == None:
            system = self.get_system('Name', name)

        if system is None:
            Debug.logger.debug(f"System created {name} {addr}")
            system = {
                'Name': name,
                'StarSystem' : name,
                'SystemAddress' : addr,
                'Builds': []
            }
            self.systems.append(system)
            self.dirty = True

        return system


    def add_system(self, plan_name: str, system_name: str = '') -> Dict:
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
        return system_data


    def remove_system(self, index):
        del self.systems[index]
        self.dirty = True

        return True


    def get_all_builds(self) -> List[Dict]:
        all = []
        for system in self.systems:
            all = all + self.get_system_builds(system)

        return all


    def get_tracked_builds(self) -> List[Dict]:
        tracked = []
        for build in self.get_all_builds():
            if build.get("Track") == 'Yes' and build.get('ResourcesRequired') != {}:
                tracked.append(build)

        return tracked

    def get_system_builds(self, system) -> List[Dict]:
        bs = []
        for build in system.get('Builds', []):
            #Debug.logger.debug(f"{build}")
            if build.get('SystemID'):
                #Debug.logger.debug(f"Adding actual resources for {build.get('Name', '')}")
                for m in self.progress:
                    if m['SystemID'] == build.get('SystemID'):
                        costs = m['ResourcesRequired']
                        break
                for comm in costs:
                    build['ResourcesRequired'][comm.get("Name_Localised", '')][comm.get("RequiredAmount", '')]
                    build['ResourcesDelivered'][comm.get("Name_Localised", '')][comm.get("ProvidedAmount", '')]
            elif build.get('Base Type', '') != '': # The default for a build
                #Debug.logger.debug(f"Adding default for {build.get('Name', '')}")
                build['ResourcesRequired'] = self.base_costs[build.get('Base Type')]
                build['ResourcesDelivered'] = {}
            build['Plan'] = system.get('Name', 'Unnamed')
            if build.get('Name') == '':
                build['Name'] = 'Unnamed'
            bs.append(build)

        return bs

    def get_build(self, system, id = None, name: str = None) -> Optional[Dict]:
        """
        Get a build by id or name

        Args:
            system_name: The system address

        Returns:
            The build data or None if not found
        """
        for build in self.get_system_builds(system):
            if id and build.get('MarketID') == id:
                return build
            if name and build.get('Name') == name:
                return build

        return None


    def find_or_create_build(self, system, market, name):
        Debug.logger.debug(f"find_or_create_build entered {name} {addr}")

        build = None
        for b in system['Builds']:
            if b.get('MarketID', '') == market:
                build = b
                break
            if b.get('Name', '') == name:
                build = b
                break

        if build == None:
            Debug.logger.debug(f"find_or_create_build entered {name} {addr}")

            build = {
                'Name': name,
                'MarketID': market,
                'State': BuildStatus.PLANNED
            }
            system['Builds'].append(build)
            self.dirty = True

        return build


    def add_build(self, system) -> bool:
        """
        Add a new build to a system

        Returns:
            True if successful, False otherwise
        """

        system['Builds'].append({
            'Track': 'No',
            'State': 'Planned',
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


    def get_required(self, builds:Dict) -> Dict:

        reqs = []
        # Build our list of bases and commodity requirements
        total = {}
        for tr in builds:
            res = tr.get('ResourcesRequired', {})
            reqs.append(res)
            for c in res.keys():
                if c not in total:
                    total[c] = 0
                total[c] += res[c]

        if len(reqs) > 0:
            reqs.append(total)

        return reqs


    def get_delivered(self, builds:Dict) -> Dict:
        # Build our list of bases and commodity requirements
        reqs = []
        total = {}
        for tr in builds:
            res = tr.get('ResourcesDelivered', {})
            reqs.append(res)
            for c in res.keys():
                if c not in total:
                    total[c] = 0
                total[c] += res[c]

        if len(reqs) > 0:
            reqs.append(total)

        return reqs


    def find_or_create_progress(self, id):
        market = None
        for m in self.progress:
            if m.get('MarketID', '') == id:
                market = m

        if market == None:
            market = {
                'MarketID': id
            }
            self.progress.append(market)
            self.dirty = True

        return market

    def update_carrier(self):
        carrier = {}
        if self.bgstally.fleet_carrier.available() == True:
            for item in self.bgstally.fleet_carrier.cargo:
                    if item['locName'] not in carrier:
                        carrier[item['locName']] = 0
                    carrier[item['locName']] += int(item['qty'])

        self.carrier_cargo = carrier
        Debug.logger.debug(f"carrier updated; {self.carrier_cargo}")


    def update_cargo(self):
        try:
            journal_dir:str = config.get_str('journaldir') or config.default_journal_dir
            if not journal_dir: return

            with open(join(journal_dir, CARGO_FILENAME), 'rb') as file:
                data:bytes = file.read().strip()
                if not data: return

                json_data = json.loads(data)
                for k, v in json_data['Inventory']:
                    self.cargo[k] = v

            Debug.logger.debug(f"cargo: {self.cargo}")

        except Exception as e:
            Debug.logger.info(f"Unable to load {CARGO_FILENAME} from the player journal folder")
            Debug.logger.error(traceback.format_exc())

    def update_market(self):
        market = {}

        if self.bgstally.state.current_system_id and self.bgstally.market.available(self.bgstally.state.current_system_id):
            market = self.bgstally.market.commodities

        self.market = market

        Debug.logger.debug(f"Market updated: {market}")

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
        #for system in self.systems:
        #    for build in system['Builds']:
        #        if 'Type' in build:
        #            build['Base Type'] = build['Type']
        #            del build['Type']

        return {
            'Docked' : self.docked,
            'System' : self.system_id,
            'Progress': self.progress,
            'Systems': self.systems,
            }


    def _from_dict(self, dict: dict):
        """
        Populate our data from a Dictionary that has been deserialized
        """
        self.docked = dict.get('Docked', False)
        self.system_id = dict.get('Sytstem')
        self.progress = dict.get('Progress', [])
        self.systems = dict.get('Systems', [])