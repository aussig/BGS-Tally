import csv
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
COMMODITY_FILENAME = 'commodity.csv'

class Colonisation:
    """
    Manages colonisation data and events for Elite Dangerous colonisation
    """
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.system_id = None
        self.docked = False
        self.base_types = {}  # Loaded from base_types.json
        self.base_costs = {}  # Loaded from base_costs.json
        self.commodities = {} # Loaded from commodity.csv
        self.systems:list = []     # Systems with colonisation data
        self.progress:dict = {}    # Construction progress data
        self.dirty = False

        self.cargo = {} # Local store of our current cargo
        self.carrier_cargo = {} # Local store of our current carrier cargo
        self.market = {} # Local store of the current market data
        self.cargo_capacity = 784 # Default cargo capacity
        # Mappinng of commodity internal names to local names. Over time this should update to each user's local names

        # Load base commodities, types, costs, and saved data
        self.load_commodities()
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
        The 'All' category is used to list all the colonisation commodities and their inara IDs
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
            self.base_costs = {}


    def load_commodities(self):
        '''
        Load the commodities from the CSV file. This is used to map the internal name to the local name.
        '''
        try:
            file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, COMMODITY_FILENAME)
            with open(file, encoding = 'utf-8') as csv_file_handler:
                csv_reader = csv.DictReader(csv_file_handler)

                for rows in csv_reader:
                    self.commodities[f"${rows.get('symbol', '').lower()}_name;"] = rows.get('name', '')
        except Exception as e:
                Debug.logger.error(f"Unable to load {file}")


    def journal_entry(self, cmdr, is_beta, system, station, entry, state):
        """
        Parse an incoming journal entry and store the data we need
        """
        try:
            match entry.get('event'):
                case 'StartUp': # Synthetic event.
                    self.update_cargo(state.get('Cargo'))
                    self.update_market()
                    self.update_carrier()
                    self.dirty = True

                case 'Cargo':
                    self.update_cargo(state.get('Cargo'))
                    self.dirty = True

                case 'CargoTransfer':
                    self.update_carrier()
                    self.dirty = True

                case 'ColonisationSystemClaim':
                    system = self.find_or_create_system(entry.get('StarSystem', ''), entry.get('SystemAddress', ''))

                    system['StarSystem'] = entry.get('StarSystem', '')
                    system['SystemAddress'] = entry.get('SystemAddress', '')
                    system['Claimed'] = entry.get('timestamp', datetime.now().isoformat())

                    self.dirty = True
                    Debug.logger.debug(f"System claimed: {entry.get('StarSystem', '')}")

                case 'ColonisationConstructionDepot':
                    if not entry.get('MarketID'):
                        Debug.logger.info(f"Invalid ColonisationConstructionDepot event: {entry}")
                        return

                    progress = self.find_or_create_progress(entry.get('MarketID'))

                    progress['Updated'] = entry.get('TimeStamp')
                    for f in ['ConstructionProgress', 'ConstructionFailed', 'ConstructionComplete', 'ResourcesRequired']:
                        progress[f] = entry.get(f)
                    self.dirty = True

                case 'Docked':
                    build_state = None
                    self.update_market(entry.get('MarketID'))
                    self.docked = True

                    # Figure out the station name and location
                    if entry.get('StationName', '') == '$EXT_PANEL_ColonisationShip:#index=1;':
                        Debug.logger.debug(f"Docked at Colonisation ship")
                        name = entry.get('StationName_Localised')
                        type = 'Orbital'
                        buildsstate = BuildState.PROGRESS
                    elif 'Orbital Construction Site: ' in entry.get('StationName', ''):
                        name = entry['StationName'].replace('Orbital Construction Site: ', '')
                        type = 'Orbital'
                        build_state = BuildState.PROGRESS
                    elif 'Planetary Construction Site: ' in entry.get('StationName', ''):
                        name = entry['StationName'].replace('Planetary Construction Site: ', '')
                        type = 'Planetary'
                        build_state = BuildState.PROGRESS
                    elif self.find_system(entry.get('StarSystem'), entry.get('SystemAddress')) != None:
                        s = self.find_system(entry.get('StarSystem'), entry.get('SystemAddress'))
                        Debug.logger.debug(f"Found system: {s}")
                        name = entry.get('StationName_Localised')
                        build_state = BuildState.COMPLETE

                    # If this isn't a colonisation ship or a system we're building, ignore it.
                    if build_state == None:
                        self.bgstally.ui.window_progress.update_display()
                        Debug.logger.debug(f"Not a construction or a system we're building")
                        return

                    if state == Buildbuild_state.PROGRESS:
                        Debug.logger.debug(f"Found a build in progress to adding/updating it {name}")                        
                        system = self.find_or_create_system(entry.get('StarSystem'), entry.get('SystemAddress'))
                        if not 'Name' in system: system['Name'] = entry.get('StarSystem')
                        system['StarSystem'] = entry.get('StarSystem')

                        build = self.find_or_create_build(system, entry.get('MarketID'), name)                        
                        build['Name'] = name
                        build['MarketID'] = entry.get('MarketID')
                        build['Location'] = type
                        build['State'] = build_state
                        build['StationEconomy'] = entry.get('StationEconomy_Localised', '')

                    # A build of ours that's completed so update it.
                    if build_state == BuildState.COMPLETE:
                        Debug.logger.debug("Found a complete build in a system of ours, updating it")
                        system = self.find_system(entry.get('StarSystem'), entry.get('SystemAddress'))
                        system['StarSystem'] = entry.get('StarSystem')
                        system['SystemAddress'] = entry.get('SystemAddress')

                        build = self.find_or_create_build(system, entry.get('MarketID'), entry.get('StationName'))
                        build['Name'] = entry.get('StationName')
                        build['State'] = build_state
                        build['Track'] = False

                    self.dirty = True

                case 'LoadOut':
                    # Let's not consider tiny capacities as they'll create silly numbers and you're probably not
                    # hauling right now.
                    # state.get('CargoCapacity') is supposed to work!
                    self.cargo_capacity = entry.get('CargoCapacity') if entry.get('CargoCapacity') > 16 else 784
                    self.dirty = True

                case 'Undocked':
                    self.market = {}
                    self.docked = False
                    self.dirty = True

            # Save immediately to ensure we don't lose any data
            if self.dirty == True:
                self.bgstally.ui.window_progress.update_display()
                self.save()

        except Exception as e:
            Debug.logger.error(f"Error processing event: {e}")
            Debug.logger.error(traceback.format_exc())


    def get_base_type(self, type_name: str) -> Dict:
        return self.base_types.get(type_name, {})


    def get_base_types(self, category:str = 'Any') -> List[str]:
        """
        Get a list of base type names
        """
        if category in ['Any', 'All']:
            return list(self.base_types.keys())

        if category == 'Initial': # Just the inital build starports
            return [base_type for base_type in self.base_types if self.base_types[base_type].get('Category') in ['Starport', 'Outpost']]

        # Category (Settlement, Outpost, Starport, etc)
        return [base_type for base_type in self.base_types if self.base_types[base_type].get('Category') == category]


    def get_all_systems(self) -> List[Dict]:
        """
        Get all systems being tracked for colonisation
        """
        return self.systems


    def get_system(self, key: str, value: str) -> Optional[Dict]:
        """
        Get a system by any attribute
        """
        for i, system in enumerate(self.systems):
            if system.get(key) == value:
                return system

        return None

    def get_system_tracking(self, system) -> str:
        """
        Get the tracking status of a system (All, Partial or None)
        """
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

    def find_system(self, name=None, addr=None) -> Optional[Dict]:
        """
        Find a system by addres, name, or plan name 
        """
        system = self.get_system('SystemAddress', addr)
        if system == None:
            system = self.get_system('StarSystem', name)
        if system == None:
            system = self.get_system('Name', name)
        return system

    def find_or_create_system(self, name, addr) -> Dict:
        """
        Find a system by name or plan, or create it if it doesn't exist
        """
        system = self.find_system(name, addr)
        if system is None:
            return self.add_system(name, name, addr)

        return system


    def add_system(self, plan_name: str, system_name: str = None, system_address: str = None) -> Dict:
        """
        Add a new system for colonisation planning
        """
        if self.get_system('Name', plan_name) is not None:
            Debug.logger.warning(f"Cannot add system - already exists: {plan_name}")
            return False

        # Create new system
        system_data = {
            'Name': plan_name,
            'Claimed': '',
            'Builds': []
        }
        if system_name != None: system_data['StarSystem'] = system_name
        if system_address != None: system_data['SystemAddress'] = system_address 
        self.systems.append(system_data)

        self.dirty = True
        return system_data


    def remove_system(self, index: int) -> bool:
        del self.systems[index]
        self.dirty = True

        return True


    def get_all_builds(self) -> List[Dict]:
        '''
        Get all builds from all systems
        '''
        all = []
        for system in self.systems:
            b = self.get_system_builds(system)
            if b != None:
                all = all + b

        return all


    def get_tracked_builds(self) -> List[Dict]:
        '''
        Get all builds that are being tracked
        '''
        tracked = []
        for build in self.get_all_builds():
            if build.get("Track") == True and build.get('State', '') != BuildState.COMPLETE:
                tracked.append(build)

        return tracked

    def get_system_builds(self, system: Dict) -> List[Dict]:
        '''
        Get all builds for a system
        '''
        try:
            for build in system.get('Builds', []):
                if build.get('Name') == '' or build.get('Name') == None:
                    build['Name'] = 'Unnamed'

            return system.get('Builds', [])

        except Exception as e:
            Debug.logger.error(f"Error getting builds: {e}")


    def find_build(self, system: Dict, marketid:int = None, name: str = None) -> Optional[Dict]:
        """
        Get a build by marketid or name
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


    def find_or_create_build(self, system: Dict, marketid: int = None, name: str = None) -> Dict:
        '''
        Find a build by marketid or name, or create it if it doesn't exist
        '''
        build = self.find_build(system, marketid, name)

        if build == None:
            return self.add_build(system, marketid, name)
            
        return build


    def add_build(self, system: Dict, marketid: int = None, name: str = 'Unnamed') -> Dict:
        """
        Add a new build to a system
        """
        build = {
                'Name': name,
                'Plan': system.get('Name'),
                'State': BuildState.PLANNED
                }
        if marketid != None: build['MarketID'] = marketid

        system['Builds'].append(build)

        self.dirty = True
        return build


    def remove_build(self, system: Dict, build_index: int) -> bool:
        """
        Remove a build from a system
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
        self.dirty = True
        
        return True


    def update_build_tracking(self, build: Dict, state: bool) -> None:
        '''
        Change a build's tracked status
        '''
        if build.get('Track') != state:
            build['Track'] = state
            self.dirty = True
            self.bgstally.ui.window_progress.update_display()


    def _get_progress(self, builds:List[Dict], type: str) -> Dict:
        try:
            prog = []
            found = 0
            for b in builds:
                res = {}
                # See if we have actual data
                if b.get('MarketID') != None:
                    p = self.progress.get(str(b.get('MarketID')), {})
                    for c in p.get('ResourcesRequired', []):
                        res[c.get('Name')] = c.get(type)

                # No actual data so we use the estimates from the base costs
                if res == {}: res = self.base_costs.get(b.get('Base Type'), {})
                if res != {}: found += 1

                prog.append(res)

            # Add an "all" total at the end of the list if there's more than one bulid found.
            if found > 1:
                total = {}
                for res in prog:
                    for c, v in res.items():
                        if c not in total: total[c] = 0
                        total[c] += v

                prog.append(total)

            return prog
        except Exception as e:
            Debug.logger.info(f"Unable to get required commodities")
            Debug.logger.error(traceback.format_exc())

    def get_required(self, builds:List[Dict]) -> Dict:
        '''
        Return the commodities required for the builds listed
        '''
        return self._get_progress(builds, 'RequiredAmount')


    def get_delivered(self, builds:List[Dict]) -> Dict:
        '''
        Return the commodities delivered for the builds listed
        '''
        return self._get_progress(builds, 'ProvidedAmount')


    def find_or_create_progress(self, id:int) -> Dict:
        if id not in self.progress:
            self.progress[id] = { 'MarketID': id }
        self.dirty = True

        return self.progress.get(id)


    def update_carrier(self):
        '''
        Update the carrier cargo data.
        '''
        try:
            carrier = {}
            if self.bgstally.fleet_carrier.available() == True:
                #Debug.logger.debug(f"Updating carrier data {self.bgstally.fleet_carrier.cargo}")
                for item in self.bgstally.fleet_carrier.cargo:
                    n = item.get('commodity')
                    n = f"${n.lower().replace(' ', '')}_name;"
                    if n not in carrier:
                        carrier[n] = 0
                    carrier[n] += int(item['qty'])

            Debug.logger.debug(f"Carrier: {carrier}")
            self.carrier_cargo = carrier

        except Exception as e:
            Debug.logger.info(f"Carrier update error")
            Debug.logger.error(traceback.format_exc())


    def update_cargo(self, cargo):
        '''
        Update the cargo data.
        '''
        try:
            tmp = {}
            Debug.logger.debug(f"cargo updated: {cargo}")
            for k, v in cargo:
                Debug.logger.debug(f"{k} {v}")
                if v > 0:
                    k = f"${k.lower()}_name;"
                    tmp[k] = v
            self.cargo = tmp

            Debug.logger.debug(f"cargo updated: {self.cargo}")
        except Exception as e:
            Debug.logger.info(f"Unable update the cargo data")
            Debug.logger.error(traceback.format_exc())


    def update_market(self, marketid=None):
        try:
            market = {}

            if marketid == None:
                self.market = {}
                Debug.logger.debug(f"Market cleared: {market}")
                return

            if self.bgstally.market.available(marketid):
                self.market = self.bgstally.market.commodities
                return

            # The market object doesn't have a market for us so we'll load it ourselves.
            journal_dir:str = config.get_str('journaldir') or config.default_journal_Name_dir
            if not journal_dir: return

            with open(join(journal_dir, MARKET_FILENAME), 'rb') as file:
                json_data = json.load(file)
                if marketid == json_data['MarketID']:
                    for item in json_data['Items']:
                        if item.get('Stock') > 0:
                            market[item.get('Name')] = item.get('Stock')
            self.market = market

            Debug.logger.debug(f"Market updated: {market}")

        except Exception as e:
            Debug.logger.info(f"Unable to load {MARKET_FILENAME} from the player journal folder")
            Debug.logger.error(traceback.format_exc())


    def get_commmodity(self, name:str, source: Dict, default=None):
        '''
        Commodities have a cargo/carrier symbol, a colonisation/internal name, and a local name.
        Find the commodity regardless of which one is being used.
        '''
        for n in [name, name.lower(), f"${name.lower().replace(' ', '')}_name;"]:
            if n in source:
                return source[n]

        return default

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

    def _as_dict(self):
        """
        Return a Dictionary representation of our data, suitable for serializing
        """
        return {
            'Docked' : self.docked,
            'System' : self.system_id,
            'Progress': self.progress,
            'Systems': self.systems,
            'CargoCapacity': self.cargo_capacity,
            'Carrier' : self.carrier_cargo,
            'Cargo' : self.cargo,
            'Market' : self.market
            }


    def _from_dict(self, dict: dict):
        """
        Populate our data from a Dictionary that has been deserialized
        """
        self.docked = dict.get('Docked', False)
        self.system_id = dict.get('Sytstem')
        self.progress = dict.get('Progress', [])
        self.systems = dict.get('Systems', [])
        self.carrier_cargo = dict.get('Carrier', {})
        self.cargo = dict.get('Cargo', {})
        self.market = dict.get('Market', {})
        self.cargo_capacity = dict.get('CargoCapacity', 784)