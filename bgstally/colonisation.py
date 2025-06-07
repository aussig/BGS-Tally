import csv
import json
from json import JSONDecodeError
from urllib.parse import quote
from os import path
from os.path import join
import traceback
import re
import time
from datetime import datetime
from requests import Response
from bgstally.constants import FOLDER_OTHER_DATA, FOLDER_DATA, BuildState, CommodityOrder, ProgressUnits, ProgressView, RequestMethod
from bgstally.requestmanager import BGSTallyRequest
from bgstally.debug import Debug
from bgstally.utils import _, get_by_path
from config import config

FILENAME = "colonisation.json"
BASE_TYPES_FILENAME = 'base_types.json'
BASE_COSTS_FILENAME = 'base_costs.json'
CARGO_FILENAME = 'Cargo.json'
MARKET_FILENAME = 'Market.json'
COMMODITY_FILENAME = 'commodity.csv'
EDSM_BODIES = 'https://www.edsm.net/api-system-v1/bodies?systemName='
EDSM_STATIONS = 'https://www.edsm.net/api-system-v1/stations?systemName='
EDSM_SYSTEM = 'https://www.edsm.net/api-v1/system?showInformation=1&systemName='
EDSM_DELAY = (3600 * 24)
class Colonisation:
    ''' Manages colonisation data and events for Elite Dangerous colonisation '''
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.system_id:str = None
        self.current_system:str = None
        self.body:str = None
        self.station:str = None
        self.marketid:str = None
        self.docked:bool = False
        self.base_types:dict = {}  # Loaded from base_types.json
        self.base_costs:dict = {}  # Loaded from base_costs.json
        self.commodities:dict = {} # Loaded from commodity.csv
        self.systems:list = []     # Systems with colonisation
        self.progress:list = []    # Construction progress data
        self.dirty:bool = False

        self.cargo:dict = {}       # Local store of our current cargo
        self.carrier_cargo:dict = {} # Local store of our current carrier cargo
        self.market:dict = {}      # Local store of the current market data
        self.cargo_capacity:int = 784 # Default cargo capacity

        # Load base commodities, types, costs, and saved data
        self.load_commodities()
        self.load_base_types()
        self.load_base_costs()
        self.load()
        self.update_carrier()


    def load_base_types(self) -> None:
        ''' Load base type definitions from base_types.json '''
        try:
            base_types_path = path.join(self.bgstally.plugin_dir, FOLDER_DATA, BASE_TYPES_FILENAME)
            with open(base_types_path, 'r') as f:
                self.base_types = json.load(f)
                Debug.logger.info(f"Loaded {len(self.base_types)} base types for colonisation")
        except Exception as e:
            Debug.logger.error(f"Error loading base types: {e}")
            self.base_types = {}


    def load_base_costs(self) -> None:
        '''
        Load base cost definitions from base_costs.json
        The 'All' category is used to list all the colonisation commodities and their inara IDs
        '''
        try:
            base_costs_path:str = path.join(self.bgstally.plugin_dir, FOLDER_DATA, BASE_COSTS_FILENAME)
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


    def load_commodities(self) -> None:
        ''' Load the commodities from the CSV file. This is used to map the internal name to the local name. '''
        try:
            file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, COMMODITY_FILENAME)
            with open(file, encoding = 'utf-8') as csv_file_handler:
                csv_reader = csv.DictReader(csv_file_handler)
                comm:dict = {}
                for rows in csv_reader:
                    comm[f"${rows.get('symbol', '').lower()}_name;"] = {'Name' : rows.get('name', ''), 'Category': rows.get('category', '')}
                Debug.logger.info(f"Loaded {len(comm)} commodities for colonisation")

                self.commodities = dict(sorted(comm.items(), key=lambda item: item[1]['Name']))

        except Exception as e:
            Debug.logger.error(f"Unable to load {file} {e}")
            Debug.logger.debug(traceback.format_exc())


    def journal_entry(self, cmdr, is_beta, system, station, entry, state) -> None:
        ''' Parse and process incoming journal entries '''
        try:
            if state.get('CargoCapacity', 0) != None and state.get('CargoCapacity', 0) > 16 and state.get('CargoCapacity', 0) != self.cargo_capacity:
                self.cargo_capacity = state.get('CargoCapacity')
                self.dirty = True

            match entry.get('event'):
                case 'StartUp': # Synthetic event.
                    #Debug.logger.debug(f"StartUp event: {entry}")
                    self.system_id = entry.get('SystemAddress', None)
                    self.current_system = entry.get('StarSystem', None)
                    self.body = entry.get('Body', None)
                    self.station = entry.get('StationName', None)
                    self.marketid = entry.get('MarketID', None)

                    self.update_cargo(state.get('Cargo'))
                    self.update_market(self.marketid)
                    self.update_carrier()

                case 'Cargo':
                    self.update_cargo(state.get('Cargo'))
                    if self.marketid == str(self.bgstally.fleet_carrier.carrier_id):
                        self.update_carrier()

                case 'CargoTransfer':
                    self.update_cargo(state.get('Cargo'))
                    self.update_carrier()

                case 'ColonisationSystemClaim':
                    Debug.logger.info(f"System claimed: {entry.get('StarSystem', '')}")
                    system:dict = self.find_or_create_system(entry.get('StarSystem', ''), entry.get('SystemAddress', ''))
                    system['StarSystem'] = entry.get('StarSystem', '')
                    system['SystemAddress'] = entry.get('SystemAddress', '')
                    system['Claimed'] = entry.get('timestamp', datetime.now().isoformat())
                    self.dirty = True

                case 'ColonisationConstructionDepot':
                    if not entry.get('MarketID'):
                        Debug.logger.info(f"Invalid ColonisationConstructionDepot event: {entry}")
                        return

                    progress:dict = self.find_or_create_progress(entry.get('MarketID'))
                    progress['Updated'] = entry.get('timestamp')
                    for f in ['ConstructionProgress', 'ConstructionFailed', 'ConstructionComplete', 'ResourcesRequired']:
                        progress[f] = entry.get(f)
                    self.dirty = True

                case 'Docked':
                    build_state:BuildState = None
                    self.update_market(entry.get('MarketID'))
                    self.station = entry.get('StationName')
                    self.docked = True

                    # Figure out the station name, location, and if it's one we are or should have recorded
                    name:str = ''; type:str = ''; state:BuildState = None
                    if 'Construction Site' in entry.get('StationName', '') or 'ColonisationShip' in entry.get('StationName', '') or 'MULTIPLAYER_SCENARIO' in entry.get('StationName', ''):
                        build_state = BuildState.PROGRESS
                        name = re.sub('^.* Construction Site: ', '', entry['StationName'])
                        type = re.sub('^(.*) Construction Site: .*$', '\1', entry['StationName'])
                        if entry.get('StationName', '') == '$EXT_PANEL_ColonisationShip:#index=1;':
                            type = 'Orbital'
                            name = entry.get('StationName_Localised')

                    elif self.find_system(entry.get('StarSystem'), entry.get('SystemAddress')) != None:
                        name = entry.get('StationName')
                        build_state = BuildState.COMPLETE

                    # If this isn't a colonisation ship or a system we're building, or a carrier, ignore it.
                    if build_state == None or entry.get('StationType') == 'FleetCarrier':
                        self.bgstally.ui.window_progress.update_display()
                        #Debug.logger.debug(f"Not a construction or a system we're building")
                        return

                    system:dict = self.find_or_create_system(entry.get('StarSystem', ''), entry.get('SystemAddress', ''))
                    if not 'Name' in system: system['Name'] = entry.get('StarSystem')
                    system['StarSystem'] = entry.get('StarSystem')
                    system['SystemAddress'] = entry.get('SystemAddress')

                    build:dict = self.find_or_create_build(system, entry.get('MarketID'), name)
                    build['Name'] = name
                    build['MarketID'] = entry.get('MarketID')
                    build['StationEconomy'] = entry.get('StationEconomy_Localised', '')
                    if type != '':
                        build['Location'] = type
                    build['State'] = build_state
                    build['Track'] = (build_state != BuildState.COMPLETE)
                    if self.body and entry.get('StarSystem') in self.body: # Sometimes the "body" is the body sometimes it's just the name of the base.
                        build['Body'] = self.body.replace(entry.get('StarSystem') + ' ', '')

                    #Debug.logger.debug(f"Setting {name} build state {build_state} and track {(build_state != BuildState.COMPLETE)}")
                    self.dirty = True

                case 'Market'|'MarketBuy'|'MarketSell':
                    self.update_market(entry.get('MarketID'))
                    self.update_cargo(state.get('Cargo'))
                    if entry.get('MarketID') == self.bgstally.fleet_carrier.carrier_id:
                        self.update_carrier()

                case 'SuperCruiseEntry' | 'FSDJump':
                    self.system_id = entry.get('SystemAddress')
                    self.current_system = entry.get('StarSystem', None)
                    self.market = {}
                    self.body = None
                    self.station = None
                    self.marketid = None

                case 'SupercruiseDestinationDrop':
                    self.station = entry.get('Type')
                    self.marketid = entry.get('MarketID')

                case 'ApproachBody':
                    self.current_system = entry.get('StarSystem')
                    self.system_id = entry.get('SystemAddress')
                    self.body = entry.get('Body', None)


                case 'SupercruiseExit' | 'ApproachSettlement':
                    self.system_id = entry.get('SystemAddress')
                    if entry.get('StarSystem', None): self.current_system = entry.get('StarSystem')
                    if entry.get('BodyType', 'Station') != 'Station': self.body = entry.get('Body', None)
                    if entry.get('BodyType', None) == 'Station': self.station = entry.get('Body')
                    if entry.get('Name', None) != None: self.station = entry.get('Name')
                    if entry.get('MarketID', None) != None: self.marketid = entry.get('MarketID')

                    # If it's a construction site or colonisation ship wait til we dock.
                    # If it's a carrier or other non-standard location we ignore it. Bet there are other options!
                    if self.station == None or 'Construction Site' in self.station or 'ColonisationShip' in self.station or \
                        re.search('^$', self.station) or re.search('[A-Z0-9]{3}-[A-Z0-9]{3}$', self.station):
                        return

                    # If we don't have this system in our list, we don't care about it.
                    system:dict = self.find_system(entry.get('StarSystem'), entry.get('SystemAddress'))
                    if system == None: return

                    Debug.logger.debug(f"SuperCruiseExit finding or adding build {self.station}")
                    # It's in a system we're building in, so we should create it.
                    build:dict = self.find_or_create_build(system, self.marketid, self.station)

                    # We update them here because it's not possible to land at installations once they're complete so
                    # you may miss their completion.
                    if build.get('MarketID', None) == None: build['MarketID'] = self.marketid
                    build['State'] = BuildState.COMPLETE
                    build['Name'] = self.station
                    if self.body != None and entry.get('StarSystem') in self.body: # Sometimes the "body" is the body sometimes it's just the name of the base.
                        build['Body'] = self.body.replace(entry.get('StarSystem') + ' ', '')
                    build['Track'] = False
                    Debug.logger.debug(f"Updating build info for: {entry.get('StarSystem')} {self.body} {self.station} {build}")
                    self.dirty = True

                case 'Undocked':
                    self.market = {}
                    self.marketid = None
                    self.docked = False
                    self.dirty = True

            # Save immediately to ensure we don't lose any data
            if self.dirty == True:
                self.save(entry.get('event'))
            self.bgstally.ui.window_progress.update_display()

        except Exception as e:
            Debug.logger.error(f"Error processing event: {e}")
            Debug.logger.error(traceback.format_exc())


    def get_base_type(self, type_name:str) -> dict:
        ''' Return the details of a particular type of base '''
        return self.base_types.get(type_name, {})


    def get_base_types(self, category:str = 'Any') -> list[str]:
        ''' Get a list of base type names '''
        if category in ['Any', 'All']:
            return list(self.base_types.keys())

        if category == 'Initial': # Just the inital build starports
            return [base_type for base_type in self.base_types if self.base_types[base_type].get('Category') in ['Starport', 'Outpost']]

        # Category (Settlement, Outpost, Starport, etc)
        return [base_type for base_type in self.base_types if self.base_types[base_type].get('Category') == category]


    def get_all_systems(self) -> list[dict]:
        ''' Get all systems being tracked for colonisation '''
        return self.systems


    def get_system(self, key:str, value:str) -> dict:
        ''' Get a system by any attribute '''
        for i, system in enumerate(self.systems):
            if system.get(key) != None and system.get(key) == value:
                return system

        return None


    def get_system_tracking(self, system:dict) -> str:
        ''' Get the tracking status of a system (All, Partial or None) '''
        status:str = 'All'
        any:bool = False
        for b in system['Builds']:
            if b.get('Track', False) == True:
                any = True
            else:
                status = 'Partial'

        if any == False:
            return 'None'

        return status


    def find_system(self, name:str = None, addr:str = None) -> dict:
        ''' Find a system by address, name, or 'plan' name '''
        system:dict = self.get_system('SystemAddress', addr)
        if system == None:
            system = self.get_system('StarSystem', name)
        if system == None:
            system = self.get_system('Name', name)

        return system


    def find_or_create_system(self, name:str, addr:str) -> dict:
        ''' Find a system by name or plan, or create it if it doesn't exist '''
        system:dict = self.find_system(name, addr)
        if system is None:
            return self.add_system(name, name, addr)

        return system


    def add_system(self, plan_name:str, system_name:str = None, system_address:str = None) -> dict:
        ''' Add a new system for colonisation planning '''

        if self.get_system('Name', plan_name) is not None or self.get_system('StarSystem', system_name) is not None:
            Debug.logger.warning(f"Cannot add system - already exists: {plan_name} {system_name}")
            return False

        # Create new system
        system_data:dict = {
            'Name': plan_name,
            'Claimed': '',
            'Builds': []
        }
        if system_name != None: system_data['StarSystem'] = system_name
        if system_address != None: system_data['SystemAddress'] = system_address
        self.systems.append(system_data)

        # If we have a system address, we can try to get the bodies from EDSM
        if system_name != None:
            Debug.logger.debug(f"Requesting EDSM bodies for {system_name}")
            self.bgstally.request_manager.queue_request(EDSM_STATIONS+quote(system_name), RequestMethod.GET, callback=self._edsm_stations)
            self.bgstally.request_manager.queue_request(EDSM_BODIES+quote(system_name), RequestMethod.GET, callback=self._edsm_bodies)

        self.dirty = True
        self.save()
        return system_data


    def _edsm_stations(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        ''' Process the results of querying ESDM for the stations in a system '''
        Debug.logger.debug(f"EDSM discovery response received: {success}")
        try:
            data:dict = response.json()
            if data.get('name', None) == None:
                Debug.logger.debug(f"EDSM stations did not contain a name, ignoring")
                return
            system:dict = self.find_system(data.get('name'))
            if system == None:
                Debug.logger.debug(f"Didn't find system {data.get('name')}")
                return

            Debug.logger.debug(f"Received stations: {data.get('stations')}")
            stations:list = list(k for k in sorted(data.get('stations', []), key=lambda item: item['id']))
            for base in stations:
                # Ignore these
                if base.get('type', '') in ['Fleet Carrier'] or 'Construction Site' in base.get('name', '') or 'ColonisationShip' in base.get('name', ''):
                    continue

                name:str = base.get('name', '')
                type:str = base.get('type', '')
                state:BuildState = BuildState.COMPLETE
                if name == '$EXT_PANEL_ColonisationShip:#index=1;':
                    if len(stations) != 1: # This hangs around but only matters if it's the only station in the system.
                        continue
                    type = 'Orbital'
                    name = 'Unknown'
                    state = BuildState.PROGRESS

                if 'Construction Site' in name:
                    name = re.sub('^.* Construction Site: ', '', name)
                    type = re.sub('^(.*) Construction Site: .*$', '\1', name)
                    state = BuildState.PROGRESS

                if self.find_build(system, base.get('marketId'), name) != None:
                    Debug.logger.debug(f"Build {name} already exists in system {data.get('name')}, skipping")
                    continue

                body:str = get_by_path(base, ['body', 'name'], '')
                body = body.replace(system.get('StarSystem', '') + ' ', '')

                build:dict = {
                    'Base Type': base.get('type'),
                    'StationEconomy': base.get('economy'),
                    'State': state,
                    'Name': name,
                    'MarketID': base.get('marketId'),
                    'Location': type,
                    'Body': body,
                    }
                system['Builds'].append(build)
                Debug.logger.debug(f"Added station {build} to system {data.get('name')}")

            Debug.logger.debug(f"System: {system['Builds']}")
            self.bgstally.ui.window_colonisation.update_display()
            self.dirty = True
            self.save()

        except JSONDecodeError:
            Debug.logger.warning(f"Event discovery data is invalid, falling back to defaults")
            return
        except Exception as e:
            Debug.logger.info(f"Error recording stations")
            Debug.logger.error(traceback.format_exc())


    def _edsm_system(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        ''' Process the results of querying ESDM for the system details '''
        Debug.logger.debug(f"EDSM system response received: {success}")
        try:
            data:dict = response.json()
            if data.get('name', None) == None:
                Debug.logger.debug(f"EDSM system did not contain a name, ignoring")
                return
            system:dict = self.find_system(data.get('name'))
            if system == None:
                Debug.logger.debug(f"Didn't find system {data.get('name')}")
                return

            Debug.logger.debug(f"system: {data}")
            system['Population'] = get_by_path(data, ['information', 'population'], None)
            system['Economy'] = get_by_path(data, ['information', 'economy'], None)
            Debug.logger.debug(f"{data}")
            if get_by_path(data, ['information', 'secondEconomy'], 'None') != 'None':
                system['Economy'] += "/" + get_by_path(data, ['information', 'secondEconomy'])
            system['Security'] = get_by_path(data, ['information', 'security'], None)
            system['EDSMUpdated'] = int(time.time())

            self.dirty = True
            self.save()

        except JSONDecodeError:
            Debug.logger.warning(f"Event discovery data is invalid, falling back to defaults")
            return
        except Exception as e:
            Debug.logger.info(f"Error recording response")
            Debug.logger.error(traceback.format_exc())


    def _edsm_bodies(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        ''' Process the results of querying ESDM for the bodies in a system '''
        Debug.logger.debug(f"EDSM bodies response received: {success}")
        try:
            data:dict = response.json()
            if data.get('name', None) == None:
                Debug.logger.debug(f"EDSM bodies did not contain a name, ignoring")
                return
            system:dict = self.find_system(data.get('name'))
            if system == None:
                Debug.logger.debug(f"Didn't find system {data.get('name')}")
                return

            # Only record the body details that we need since EDSM returns an enormous amount of data.
            system['Bodies'] = []
            for b in data.get('bodies'):
                v:dict = {}
                for k in ['name', 'type', 'subType', 'terraformingState', 'isLandable', 'atmosphereType', 'volcanismType', 'rings', 'reserveLevel', 'distanceToArrival']:
                    if b.get(k, None): v[k] = b.get(k)
                if b.get('parents', None) != None:
                    v['parents'] = len(b.get('parents', []))
                system['Bodies'].append(v)
            self.dirty = True
            self.save()

        except JSONDecodeError:
            Debug.logger.warning(f"Event discovery data is invalid, falling back to defaults")
            return
        except Exception as e:
            Debug.logger.info(f"Error recording bodies")
            Debug.logger.error(traceback.format_exc())


    def get_bodies(self, system:dict) -> list:
        ''' Return a list of bodies in the system '''
        bodies:list = []
        for b in system.get('Bodies', []):
            name = b.get('name') if b.get('name') != system['StarSystem'] else 'A'
            bodies.append(name.replace(system['StarSystem'] + ' ', ''))

        return bodies


    def remove_system(self, index:int) -> bool:
        ''' Delete a system '''
        systems = self.get_all_systems() # It's a sorted list, index isn't reliable unless sorted!
        del systems[index]
        self.dirty = True
        self.save()
        return True


    def get_all_builds(self) -> list[dict]:
        ''' Get all builds from all systems '''
        all:list = []
        for system in self.systems:
            b = self.get_system_builds(system)
            if b != None:
                all += b

        return all


    def get_build_state(self, build:dict) -> BuildState:
        ''' Get the state of a build from either the build or the progress data '''
        if build.get('State', None) == BuildState.COMPLETE or build.get('MarketID', None) == None:
            return build.get('State', BuildState.PLANNED)

        # If we have a progress entry, use that
        for p in self.progress:
            if p.get('MarketID') == build.get('MarketID'):
                if p.get('ConstructionComplete', False) == True or p.get('ConstructionFailed', False) == True:
                    build['State'] = BuildState.COMPLETE
                    build['Track'] = False
                    self.dirty = True
                    return BuildState.COMPLETE
                return BuildState.PROGRESS

        # Otherwise, use the state of the build
        return build.get('State', BuildState.PLANNED)


    def get_tracked_builds(self) -> list[dict]:
        ''' Get all builds that are being tracked '''
        tracked:list = []
        for build in self.get_all_builds():
            if build.get("Track", False) == True and self.get_build_state(build) != BuildState.COMPLETE:
                tracked.append(build)

        return tracked


    def get_system_builds(self, system:dict) -> list[dict]:
        ''' Get all builds for a system '''
        return system.get('Builds', [])


    def find_build(self, system:dict, marketid:int = None, name:str = None) -> dict:
        ''' Get a build by marketid or name '''
        builds:list = self.get_system_builds(system)

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


    def find_or_create_build(self, system:dict, marketid:int = None, name:str = None) -> dict:
        ''' Find a build by marketid or name, or create it if it doesn't exist '''
        build:dict = self.find_build(system, marketid, name)

        if build == None:
            return self.add_build(system, marketid, name)

        return build


    def add_build(self, system:dict, marketid:int = None, name:str = '') -> dict:
        ''' Add a new build to a system '''
        Debug.logger.debug(f"Adding build {name}")
        build:dict = {
                'Name': name,
                'Plan': system.get('Name'),
                'State': BuildState.PLANNED
                }
        if marketid != None: build['MarketID'] = marketid
        system['Builds'].append(build)

        self.dirty = True
        self.save()
        return build


    def remove_build(self, system:dict, build_index:int) -> bool:
        ''' Remove a build from a system '''
        if system is None:
            Debug.logger.warning(f"Cannot remove build - unknown system")
            return False

        if build_index >= len(system['Builds']):
            Debug.logger.warning(f"Cannot remove build - invalid build index: {build_index} {len(system['Builds'])} {system['Builds']}")
            return False

        # Remove build
        system['Builds'].pop(build_index)
        self.dirty = True

        return True


    def update_build_tracking(self, build:dict, state:bool) -> None:
        ''' Change a build's tracked status '''
        if build.get('Track') != state:
            build['Track'] = state
            self.dirty = True
            self.bgstally.ui.window_progress.update_display()


    def get_commodity_list(self, base_type:str, order:CommodityOrder = CommodityOrder.ALPHA) -> list:
        ''' Return an ordered list of base commodity costs for a base type '''
        try:
            comms = self.base_costs.get(base_type, None)
            if comms == None:
                return []

            match order:
                case CommodityOrder.CATEGORY:
                    # dict(sorted(dict_of_dicts.items(), key=lambda item: item[1][key_to_sort_by]))
                    ordered = list(k for k, v in sorted(self.commodities.items(), key=lambda item: item[1]['Category']))
                case _:
                    ordered = list(k for k, v in sorted(self.commodities.items(), key=lambda item: item[1]['Name']))

            return [c for c in ordered if c in comms.keys()]

        except Exception as e:
            Debug.logger.info(f"Error retrieving costs")
            Debug.logger.error(traceback.format_exc())


    def _get_progress(self, builds:list[dict], type:str) -> dict:
        ''' Internal function to get progress details '''
        try:
            prog:list = []
            found:int = 0
            for b in builds:
                res:dict = {}
                # See if we have actual data
                if b.get('MarketID') != None:
                    for p in self.progress:
                        if p.get('MarketID') == b.get('MarketID') and p.get('ConstructionComplete', False) == False and p.get('ConstructionFailed', False) != True:
                            for c in p.get('ResourcesRequired', []):
                                res[c.get('Name')] = c.get(type)
                            break
                #Debug.logger.debug(f"Progress for {b.get('Name')} {b.get('MarketID')} {type} {res}")
                # No actual data so we use the estimates from the base costs
                if res == {} and type != 'ProvidedAmount': res = self.base_costs.get(b.get('Base Type'), {})
                if res != {}: found += 1
                prog.append(res)

            # Add an 'All' total at the end of the list if there's more than one build found.
            if found > 1:
                total:dict = {}
                for res in prog:
                    for c, v in res.items():
                        if c not in total: total[c] = 0
                        total[c] += v
                prog.append(total)

            return prog

        except Exception as e:
            Debug.logger.info(f"Unable to get required commodities")
            Debug.logger.error(traceback.format_exc())


    def get_required(self, builds:list[dict]) -> dict:
        ''' Return the commodities required for the builds listed '''
        return self._get_progress(builds, 'RequiredAmount')


    def get_delivered(self, builds:list[dict]) -> dict:
        ''' Return the commodities delivered for the builds listed '''
        return self._get_progress(builds, 'ProvidedAmount')


    def find_or_create_progress(self, id:str) -> dict:
        ''' Find or if necessary create progress for a given market '''
        p:dict = self.find_progress(id)
        if p != None:
            return p

        prog:dict = { 'MarketID': id }
        self.progress.append(prog)

        self.dirty = True
        return prog


    def find_progress(self, id:str) -> dict:
        ''' Find and return progress for a given market '''
        for p in self.progress:
            if p.get('MarketID') == id:
                return p

        return None


    def update_carrier(self) -> None:
        ''' Update the carrier cargo data. '''
        try:
            carrier:dict = {}
            if self.bgstally.fleet_carrier.available() == True:
                for item in self.bgstally.fleet_carrier.cargo:
                    n = item.get('commodity')
                    n = f"${n.lower().replace(' ', '')}_name;"
                    if n not in carrier:
                        carrier[n] = 0
                    carrier[n] += int(item['qty'])
            self.carrier_cargo = carrier

        except Exception as e:
            Debug.logger.info(f"Carrier update error")
            Debug.logger.error(traceback.format_exc())


    def update_cargo(self, cargo:dict) -> None:
        ''' Update the cargo data. '''
        try:
            tmp:dict = {}
            for k, v in cargo.items():
                if v > 0:
                    k = f"${k.lower()}_name;"
                    tmp[k] = v
            self.cargo = tmp

        except Exception as e:
            Debug.logger.info(f"Unable update the cargo data")
            Debug.logger.error(traceback.format_exc())


    def update_market(self, marketid:str = None) -> None:
        ''' Update market info from the market object or directly '''
        try:
            if marketid == None or self.docked == False:
                self.market = {}
                return

            market:dict = {}
            if self.bgstally.market.available(marketid):
                for name, item in self.bgstally.market.commodities.items():
                    if item.get('Stock') > 0:
                        market[item.get('Name')] = item.get('Stock')
                if market != {}:
                    self.market = market
                    return

            # The market object doesn't have a market for us so we'll try loading it ourselves.
            # Ideally we wouldn't do this but it seems necessary
            journal_dir:str = config.get_str('journaldir') or config.default_journal_dir
            if not journal_dir: return

            with open(join(journal_dir, MARKET_FILENAME), 'rb') as file:
                json_data = json.load(file)
                if marketid == json_data['MarketID']:
                    for item in json_data['Items']:
                        if item.get('Stock') > 0:
                            market[item.get('Name')] = item.get('Stock')
            self.market = market
            Debug.logger.debug(f"Market loaded directly: {market}")

        except Exception as e:
            Debug.logger.info(f"Unable to load {MARKET_FILENAME} from the player journal folder")
            Debug.logger.error(traceback.format_exc())


    def load(self) -> None:
        ''' Load state from file '''
        file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        if path.exists(file):
            try:
                with open(file) as json_file:
                    self._from_dict(json.load(json_file))
            except Exception as e:
                Debug.logger.warning(f"Unable to load {file}")
                Debug.logger.error(traceback.format_exc())

        # Update the EDSM data if appropriate and no more than once a day.
        for system in self.systems:
            if system.get('StarSystem', '') != '' and time.time() > int(system.get('EDSMUpdated', 0)) + EDSM_DELAY:
                if system.get('Bodies', None) == None:
                    self.bgstally.request_manager.queue_request(EDSM_BODIES+quote(system.get('StarSystem')), RequestMethod.GET, callback=self._edsm_bodies)

                # Currently disabled. There are so many shortcomings with trying to do this I'm not sure it's helpful.
                #self.bgstally.request_manager.queue_request(EDSM_STATIONS+quote(system.get('StarSystem')), RequestMethod.GET, callback=self._edsm_stations)
                self.bgstally.request_manager.queue_request(EDSM_SYSTEM+quote(system.get('StarSystem')), RequestMethod.GET, callback=self._edsm_system)


    def save(self, cause:str = 'Unknown') -> None:
        ''' Save state to file '''

        file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self._as_dict(), outfile, indent=4)

        self.dirty = False

        #Debug.logger.debug(f"Saved {cause}.")
        #if cause == 'Unknown':
        #    STACK_FMT = "%s, line %d in function %s."
        #    Debug.logger.debug(f"Saved.")
        #    for frame in inspect.stack():
        #        file, line, func = frame[1:4]
        #        Debug.logger.debug(STACK_FMT % (file, line, func))


    def _as_dict(self) -> dict:
        ''' Return a Dictionary representation of our data, suitable for serializing '''

        def sort_order(item:dict):
            state:BuildState = BuildState.COMPLETE
            for b in item['Builds']:
                bs = self.get_build_state(b)
                if bs == BuildState.PLANNED and state != BuildState.PROGRESS:
                    state = BuildState.PLANNED
                if bs == BuildState.PROGRESS and b.get('Track', False) == True:
                    state = BuildState.PROGRESS
            return state.value

        # We sort the order of systems when saving so that in progress systems are first, then planned, then complete.
        # Fortuitously our desired order matches the reverse alpha of the states
        systems:list = list(sorted(self.systems, key=sort_order, reverse=True))
        units:dict = {}
        for k, v in self.bgstally.ui.window_progress.units.items():
            units[k] = v.value

        return {
            'Docked': self.docked,
            'SystemID': self.system_id,
            'CurrentSystem': self.current_system,
            'Body': self.body,
            'Station': self.station,
            'MarketID': self.marketid,
            'Progress': self.progress,
            'Systems': systems,
            'CargoCapacity': self.cargo_capacity,
            'ProgressView' : self.bgstally.ui.window_progress.view.value,
            'ProgressUnits': units
            }


    def _from_dict(self, dict:dict) -> None:
        ''' Populate our data from a Dictionary that has been deserialized '''
        self.docked = dict.get('Docked', False)
        self.system_id = dict.get('SystemID', None)
        self.current_system = dict.get('CurrentSystem', None)
        self.body = dict.get('Body', None)
        self.station = dict.get('Station', None)
        self.marketid = dict.get('MarketID', None)
        self.progress = dict.get('Progress', [])
        self.systems = dict.get('Systems', [])
        self.cargo_capacity = dict.get('CargoCapacity', 784)
        self.bgstally.ui.window_progress.view = ProgressView(dict.get('ProgressView', 0))
        units = dict.get('ProgressUnits', {})
        for k, v in units.items():
            self.bgstally.ui.window_progress.units[k] = ProgressUnits(v)
