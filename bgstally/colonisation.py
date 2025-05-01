import json
from os import path
from os.path import join
import traceback
from datetime import datetime
from typing import Dict, List, Optional

from bgstally.constants import FOLDER_OTHER_DATA, FOLDER_DATA, BuildState, CheckStates
from bgstally.debug import Debug
from bgstally.utils import _
from config import config

FILENAME = "colonisation.json"
BASE_TYPES_FILENAME = 'base_types.json'
BASE_COSTS_FILENAME = 'base_costs.json'
CARGO_FILENAME = 'Cargo.json'
MARKET_FILENAME = 'Market.json'
LOCAL_NAMES_FILENAME = 'local_names.json'

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
        self.systems:list = []     # Systems with colonisation data
        self.progress:dict = {}    # Construction progress data
        self.dirty = False

        self.cargo = {}
        self.carrier_cargo = {}
        self.market = {}
        # Mappinng of commodity internal names to local names. Over time this should update to each user's local names
        self.local_names = {}

        # Load base types, costs, and saved data
        self.load_local_names()
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
            Debug.logger.error(f"Error loading base costs: {e}")
            Debug.logger.error(traceback.format_exc())
            self.base_costs = {}


    def load_local_names(self):
        try:
            file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, LOCAL_NAMES_FILENAME)
            with open(file, 'r') as f:
                self.local_names = json.load(f)

        except Exception as e:
            Debug.logger.error(f"Error loading local names: {e}")
            Debug.logger.error(traceback.format_exc())
            self.local_names = {}

    def journal_entry(self, cmdr, is_beta, system, station, entry, state):
        """
        Parse an incoming journal entry and store the data we need
        """
        Debug.logger.debug(f"journal_entry called {entry.get('event')}")
        try:
            match entry.get('event'):
                case 'StartUp':
                    # Synthetic event.
                    self.update_cargo()
                    self.update_carrier()
                    self.dirty = True

                case 'Cargo':
                    self.update_cargo()
                    self.dirty = True

                case 'ColonisationSystemClaim':
                    system = self.find_or_create_system(entry.get('StarSystem', ''), entry.get('SystemAddress', ''))

                    system['StarSystem'] = entry.get('StarSystem', '')
                    system['SystemAddress'] = entry.get('SystemAddress', '')
                    system['Claimed'] = entry.get('timestamp', datetime.now().isoformat())
                    system['BeaconDeployed'] = ''

                    self.dirty = True
                    Debug.logger.info(f"System claimed: {entry.get('StarSystem', '')}")

                case 'ColonisationConstructionDepot':
                    if not entry.get('MarketID'):
                        Debug.logger.info(f"Invalid ColonisationConstructionDepot event: {entry}")
                        return

                    progress = self.find_or_create_progress(entry.get('MarketID'))

                    progress['Updated'] = entry.get('TimeStamp')
                    for f in ['ConstructionProgress', 'ConstructionFailed', 'ConstructionComplete', 'ResourcesRequired']:
                        progress[f] = entry.get(f)
                    self.dirty = True

                #case 'ColonisationContribution':
                    # Not sure we even want to track this.
                #    return
                    #progress = self.find_or_create_progress(entry.get('MarketID')):
                    # Store the contribution event
                    #if 'ContributionEvents' not in p:
                    #    p['ContributionEvents'] = []

                        # Add this contribution to the history
                    #   contribution_event = {
                    #        'Timestamp': entry.get('TimeStamp'),
                    #        'Commodity': entry.get('Commodity'),
                    #        'Quantity': entry.get('Quantity'),
                    #        'EventData': entry  # Store the complete event data
                    #    }
                    #    p['ContributionEvents'] = contribution_event

                case 'Docked':
                    state = None
                    self.update_market(entry.get('MarketID'))
                    self.update_cargo()
                    self.update_carrier()
                    self.docked = True

                    if entry.get('StationName', '') == '$EXT_PANEL_ColonisationShip:#index=1;':
                        Debug.logger.debug(f"Docked at Colonisation ship")
                        name = entry.get('StationName_Localised')
                        type = 'Orbital'
                        state = BuildState.PROGRESS
                    elif 'Orbital Construction Site: ' in entry.get('StationName', ''):
                        name = entry.get('StationName', '')
                        name = name.replace('Orbital Construction Site: ', '')
                        type = 'Orbital'
                        state = BuildState.PROGRESS
                    elif 'Planetary Construction Site: ' in entry.get('StationName', ''):
                        name = entry.get('StationName', '')
                        name = name.replace('Planetary Construction Site: ', '')
                        type = 'Planetary'
                        state = BuildState.PROGRESS
                    elif self.find_system(entry.get('StarSystem'), entry.get('SystemAddress')) != None:
                        s = self.find_system(entry.get('StarSystem'), entry.get('SystemAddress'))
                        Debug.logger.debug(f"Found system: {s}")
                        name = entry.get('StationName_Localised')
                        state = BuildState.COMPLETE

                    Debug.logger.debug(f"Docked progress: {state}")
                    if state == None:
                        self.bgstally.ui.window_progress.update_display()
                        Debug.logger.debug(f"Not a construction or a system we're building")
                        return

                    if state == BuildState.PROGRESS:
                        system = self.find_or_create_system(entry.get('StarSystem'), entry.get('SystemAddress'))
                        # Just in case
                        if not 'Name' in system:
                            system['Name'] = entry.get('StarSystem')

                        system['StarSystem'] = entry.get('StarSystem')

                        build = self.find_or_create_build(system, entry.get('MarketID'), name)
                        build['Name'] = entry.get('StationName')
                        build['MarketID'] = entry.get('MarketID')
                        build['Location'] = type
                        build['State'] = state
                        build['StationEconomy'] = entry.get('StationEconomy_Localised', '')
                        #if self.bgstally.state.current_body != None:
                        #    build['Body'] = self.bgstally.state.current_body.replace(entry.get('StarSystem')+' ', '')

                    # A build of ours that's completed so update it.
                    if state == BuildState.COMPLETE:
                        Debug.logger.debug("Found a complete build in a system of ours, updating it")
                        system = self.find_system(entry.get('StarSystem'), entry.get('SystemAddress'))
                        system['StarSystem'] = entry.get('StarSystem')
                        system['SystemAddress'] = entry.get('SystemAddress')
                        build = self.find_or_create_build(system, entry.get('MarketID'), entry.get('StationName'))
                        Debug.logger.debug(f"Setting build name to {entry.get('StationName')}")
                        build['Name'] = entry.get('StationName')
                        build['State'] = state
                        build['Track'] = False
                        #if self.bgstally.state.current_body != None:
                        #    build['Body'] = self.bgstally.state.current_body.replace(entry.get('StarSystem')+' ', '')

                    self.dirty = True

                case 'Undocked':
                    self.update_market()
                    self.update_cargo()
                    self.update_carrier()

                    self.docked = False
                    self.dirty = True

            # Save immediately to ensure we don't lose any data
            if self.dirty == True:
                Debug.logger.debug(f"Updating progress window and saving")
                self.bgstally.ui.window_progress.update_display()
                self.save()
            else:
                Debug.logger.debug(f"No update")
        except Exception as e:
            Debug.logger.error(f"Error processing event: {e}")
            Debug.logger.error(traceback.format_exc())


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
        if category in ['Any', 'All']:
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
            if b.get('Track', False) == True:
                any = True
            else:
                status = 'Partial'

        if any == False:
            return 'None'

        return status

    def find_system(self, name=None, addr=None):
        system = self.get_system('SystemAddress', addr)
        if system == None:
            system = self.get_system('StarSystem', name)
        if system == None:
            system = self.get_system('Name', name)
        return system

    def find_or_create_system(self, name, addr):
        Debug.logger.debug(f"find_or_create_system entered {name} {addr}")
        system = self.find_system(name, addr)
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
            'StarSystem': system_name,
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
            b = self.get_system_builds(system)
            if b != None:
                all = all + b

        return all


    def get_tracked_builds(self) -> List[Dict]:
        tracked = []
        for build in self.get_all_builds():
            if build.get("Track") == True and build.get('State', '') != BuildState.COMPLETE:
                tracked.append(build)

        return tracked

    def get_system_builds(self, system) -> List[Dict]:
        try:
            for build in system.get('Builds', []):
                if build.get('Name') == '' or build.get('Name') == None:
                    build['Name'] = 'Unnamed'

            return system.get('Builds', [])

        except Exception as e:
            Debug.logger.error(f"Error getting base types: {e}")
            self.base_types = {}

    def find_build(self, system, marketid = None, name: str = None) -> Optional[Dict]:
        """
        Get a build by id or name

        Args:
            system_name: The system address

        Returns:
            The build data or None if not found
        """
        builds = self.get_system_builds(system)

        if name == 'System Colonisation Ship' and len(builds) > 0:
            return builds[0]

        for build in builds:
            if marketid and build.get('MarketID') == marketid:
                return build
            if name and build.get('StationName') == name:
                return build
            if name and build.get('Name') == name:
                return build

        return None


    def find_or_create_build(self, system, marketid, name):
        Debug.logger.debug(f"find_or_create_build entered {marketid} {name}")

        build = self.find_build(system, marketid, name)

        if build == None:
            Debug.logger.debug(f"find_or_create_build entered {marketid} {name}")

            build = {
                'StationName' : name,
                'Name': name,
                'Plan': system.get('Name'),
                'MarketID': marketid,
                'State': BuildState.PLANNED
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
            'Plan': system.get('Name'),
            'Track': False,
            'State': 'Planned',
        })

        self.dirty = True
        return True


    def remove_build(self, system, build_index: int) -> bool:
        """
        Remove a build from a system

        Args:
            system_name: The system address
            build_index: The index of the build to remove

        Returns:
            True if successful, False otherwise
        """
        if system is None:
            Debug.logger.warning(f"Cannot remove build - unknown system")
            return False

        builds = system['Builds']
        if build_index < 0 or build_index >= len(builds):
            Debug.logger.warning(f"Cannot remove build - invalid build index: {build_index}")
            return False

        # Remove build
        builds.pop(build_index)
        Debug.logger.debug(f"Removed build {build_index} from {system}")
        self.dirty = True
        return True


    def update_build_tracking(self, build, state):
        '''
        Change a builds tracked status
        '''
        if build.get('Track') != state:
            build['Track'] = state
            self.dirty = True
            self.bgstally.ui.window_progress.update_display()

    def get_required(self, builds:Dict) -> Dict:
        try:
            reqs = []
            total = {}
            found = False
            for i, b in enumerate(builds):
                res = {}
                # See if we have actual data
                if b.get('MarketID') != None:
                    p = self.progress.get(str(b.get('MarketID')), {})
                    for c in p.get('ResourcesRequired', []):
                        res[c.get('Name')] = c.get('RequiredAmount')
                # No actual data so we'll use the estimates
                if res == {}: res = self.base_costs.get(b.get('Base Type'), {})


                if res != {}: found = True

                reqs.append(res)

            if found:
                for c in res.keys():
                    if c not in total:
                        total[c] = 0
                        total[c] += res[c]

                reqs.append(total)

            return reqs

        except Exception as e:
            Debug.logger.info(f"Unable to load {CARGO_FILENAME} from the player journal folder")
            Debug.logger.error(traceback.format_exc())


    def get_delivered(self, builds:Dict) -> Dict:
        # Build our list of bases and commodities delivered
        d = []
        total = {}
        found = False

        for i, b in enumerate(builds):
            res = {}
            if b.get('MarketID') is not None:
                p = self.progress.get(str(b.get('MarketID')), {})
                for c in p.get('ResourcesRequired', []):
                    res[c.get('Name')] = c.get('ProvidedAmount')

                if res != {}: found = True
            d.append(res)

        if found:
            for c in res.keys():
                if c not in total:
                    total[c] = 0
                    total[c] += res[c]

            d.append(total)
        return d


    def find_or_create_progress(self, id):
        if id not in self.progress:
            self.progress[id] = { 'MarketID': id }
        self.dirty = True

        return self.progress.get(id)


    def update_carrier(self):
        try:
            carrier = {}
            if self.bgstally.fleet_carrier.available() == True:
                #Debug.logger.info(f"{self.bgstally.fleet_carrier.cargo}")
                for item in self.bgstally.fleet_carrier.cargo:
                    n = item.get('commodity')
                    n = f"${n.lower()}_name;"
                    if n in self.local_names:
                        if n not in carrier:
                            carrier[n] = 0
                        carrier[n] += int(item['qty'])
                    else:
                        Debug.logger.info(f"Guessed cargo name wrong. {n} does not exist")

            self.carrier_cargo = carrier

        except Exception as e:
            Debug.logger.info(f"Carrier upodate error")
            Debug.logger.error(traceback.format_exc())


    def update_cargo(self):
        try:
            cargo = {}
            journal_dir:str = config.get_str('journaldir') or config.default_journal_dir
            if not journal_dir: return

            with open(join(journal_dir, CARGO_FILENAME), 'rb') as file:
                json_data = json.load(file)
                for item in json_data['Inventory']:
                    if item.get('Count') > 0:
                        n = item.get('Name')
                        n = f"${n.lower()}_name;"
                        cargo[n] = item.get('Count')
            self.cargo = cargo

            Debug.logger.debug(f"cargo updated: {self.cargo}")

        except Exception as e:
            Debug.logger.info(f"Unable to load {CARGO_FILENAME} from the player journal folder")
            Debug.logger.error(traceback.format_exc())


    def update_market(self, marketid=None):
        try:
            market = {}

            if marketid == None:
                self.market = {}
                Debug.logger.debug(f"Market cleared: {market}")

            if marketid and self.bgstally.market.available(marketid):
                market = self.bgstally.market.commodities

            if marketid:
                Debug.logger.debug("Getting market ourselves then!")
                journal_dir:str = config.get_str('journaldir') or config.default_journal_Name_dir
                if not journal_dir: return

                with open(join(journal_dir, MARKET_FILENAME), 'rb') as file:
                    #data:bytes = file.read().strip()
                    #if not data: return

                    json_data = json.load(file)
                    if marketid == json_data['MarketID']:
                        for item in json_data['Items']:
                            if item.get('Stock') > 0:
                                market[item.get('Name')] = item.get('Stock')
                            if item.get('Name_Localised'):
                                self.local_names[item.get('Name')] = item.get('Name_Localised')

            self.market = market
            Debug.logger.debug(f"Market updated: {market}")

        except Exception as e:
            Debug.logger.info(f"Unable to load {MARKET_FILENAME} from the player journal folder")
            Debug.logger.error(traceback.format_exc())

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
                Debug.logger.error(traceback.format_exc())

        Debug.logger.debug(f"Loaded progress: {len(self.progress.keys())} systems: {len(self.systems)}")


    def save(self):
        """
        Save state to file
        """

        file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self._as_dict(), outfile, indent=4)

        file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, LOCAL_NAMES_FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self.local_names, outfile, indent=4)

    def _as_dict(self):
        """
        Return a Dictionary representation of our data, suitable for serializing
        """
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