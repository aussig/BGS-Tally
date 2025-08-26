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
from config import config
from bgstally.constants import FOLDER_OTHER_DATA, FOLDER_DATA, BuildState, CommodityOrder, ProgressUnits, ProgressView, RequestMethod
from bgstally.requestmanager import BGSTallyRequest
from bgstally.debug import Debug
from bgstally.utils import _, get_by_path
from bgstally.ravencolonial import RavenColonial


FILENAME = "colonisation.json"
BASE_TYPES_FILENAME = 'base_types.json'
BASE_COSTS_FILENAME = 'base_costs.json'
CARGO_FILENAME = 'Cargo.json'
MARKET_FILENAME = 'Market.json'
COMMODITY_FILENAME = 'commodity.csv'
class Colonisation:
    '''
    Manages colonisation data and events for Elite Dangerous colonisation

    The colonisation module is responsible for tracking systems, builds, and progress related to colonisation.
    This class handles all the data processing for colonisation:
      - the loading and saving of colonisation data
      - processing journal entries related to colonisation
      - managing systems and builds
      - tracking progress of builds
      - providing methods to retrieve and manipulate colonisation data

    It is used by windows/colonisation.py which enables the creation, modification, and display of colonisation plans and by
    windows/progress.py which displays the progress of builds and the resources required for colonisation.

    It also interacts with the Fleet Carrier module to track cargo and market data related to colonisation.

    Colonisation uses the following data files:
      - otherdata/colonisation.json: Stores the current state of colonisation data, including systems, builds, and progress.
    and the following readonly data files:
      - data/base_types.json: Contains definitions of base types for colonisation.
      - data/base_costs.json: Contains the costs of commodities required for each base type.
      - data/commodity.csv: Contains the list of commodities and their categories.
      - data/colonisation_legend.txt and L10n/ localized legends: Contains text for the colonisation legend popup.
    '''
    def __init__(self, bgstally):
        self.bgstally:BGSTally = bgstally
        self.rc:RavenColonial = RavenColonial(self)
        self.system_id:int|None = None
        self.current_system:str|None = None
        self.body:str|None = None
        self.station:str|None = None
        self.location:str|None = None # Orbital, Surface, etc.
        self.market_id:int|None = None
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

        self.cmdr:str|None = None

        # Load base commodities, types, costs, and saved data
        self._load_commodities()
        self._load_base_types()
        self._load_base_costs()
        self._load()


    def _load_base_types(self) -> None:
        ''' Load base type definitions from base_types.json '''
        try:
            base_types_path = path.join(self.bgstally.plugin_dir, FOLDER_DATA, BASE_TYPES_FILENAME)
            with open(base_types_path, 'r') as f:
                self.base_types = json.load(f)
                Debug.logger.info(f"Loaded {len(self.base_types)} base types for colonisation")
        except Exception as e:
            Debug.logger.error(f"Error loading base types: {e}")
            self.base_types = {}


    def _load_base_costs(self) -> None:
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


    def _load_commodities(self) -> None:
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


    def journal_entry(self, cmdr, is_beta, sys, station, entry, state) -> None:
        '''
        Parse and process incoming journal entries
        This method is called by the bgstally plugin when a journal entry is received.
        '''
        try:
            self.cmdr = cmdr
            if state.get('CargoCapacity', 0) != None and state.get('CargoCapacity', 0) > 16 and state.get('CargoCapacity', 0) != self.cargo_capacity:
                self.cargo_capacity = state.get('CargoCapacity')
                self.dirty = True

            if entry.get('StarSystem', None): self.current_system = entry.get('StarSystem')
            if entry.get('SystemAddress', None): self.system_id = int(entry.get('SystemAddress'))
            if entry.get('MarketID', None) != None: self.market_id = entry.get('MarketID')
            if entry.get('Type', None) != None: self.station = entry.get('Type')
            if entry.get('BodyType', None) == 'Station': self.station = entry.get('Body')
            if entry.get("StationName", None): self.station = entry.get('StationName')
            if self.current_system != None and self.current_system in entry.get('Body', ' '): self.body = self.body_name(entry.get('Body'))

            #Debug.logger.debug(f"Event: {entry.get('event')} -- ID: {self.system_id} Sys: {self.current_system} body: {self.body} station: {self.station} market: {self.market_id}")

            match entry.get('event'):
                case 'StartUp': # Synthetic event.
                    self._update_cargo(state.get('Cargo'))
                    self._update_market(self.market_id)
                    self._update_carrier()

                    # Update systems with external data if required
                    for sysnum, system in enumerate(self.systems):
                        self.rc.load_system(system.get('SystemAddress'))

                        if system.get('Bodies', None) == None: # In case we didn't get them for some reason
                            self.rc.import_bodies(system.get('StarSystem', ''))

                        if system.get('RCSync', 0) == 1:
                            if self.rc == None: self.rc = RavenColonial(self)

                        self.rc.import_system(system.get('StarSystem', '')) # Update the system stats

                    for progress in self.progress:
                        if progress.get('ProjectID', None) != None and progress.get('ConstructionComplete', False) == False:
                            self.rc.load_project(progress)

                case 'Cargo' | 'CargoTransfer':
                    self._update_cargo(state.get('Cargo'))
                    self._update_carrier()

                case 'ColonisationContribution':
                    if not self.current_system or not self.system_id or not self.market_id:
                        Debug.logger.warning(f"Invalid ColonisationContribution event: {entry}")
                        return

                    system:dict|None = self.find_system({'StarSystem' : self.current_system, 'SystemAddress': self.system_id})
                    if system != None and system.get('RCSync', 0) == 1:
                        for progress in self.progress:
                            if progress.get('MarketID', None) == self.market_id and progress.get('ProjectID', None) != None:
                                self.rc.record_contribution(progress.get('ProjectID', 0), entry.get('Contributions', []))
                                break


                case 'ColonisationSystemClaim':
                    if not self.current_system or not self.system_id:
                        Debug.logger.warning(f"Invalid ColonisationSystemClaim event: {entry}")
                        return
                    Debug.logger.info(f"System claimed: {self.current_system}")
                    system = self.find_or_create_system({'StarSystem': self.current_system, 'SystemAddress' : self.system_id})
                    system['StarSystem'] = self.current_system
                    system['SystemAddress'] = self.system_id
                    system['Claimed'] = entry.get('timestamp', datetime.now().isoformat())
                    system['Architect'] = self.cmdr
                    self.dirty = True

                case 'ColonisationConstructionDepot':
                    if not self.market_id:
                        Debug.logger.warning(f"Invalid ColonisationConstructionDepot event: {entry}")
                        return

                    progress:dict = self.find_or_create_progress(self.market_id)
                    self.update_progress(self.market_id, entry)
                    self.dirty = True

                case 'Docked':
                    self._update_market(self.market_id)
                    self.docked = True
                    system:dict = self.find_system({'StarSystem' : self.current_system, 'SystemAddress': self.system_id})
                    build_state:BuildState = None
                    build:dict = {}

                     # Colonisation ship is always the first build. find/add system. find/add build
                     # Construction site can be any build, so find/add system, find/add build
                    if '$EXT_PANEL_ColonisationShip' in f"{self.station}" or 'Construction Site' in f"{self.station}":
                        Debug.logger.debug(f"Docked at construction site. Finding/creating system and build")
                        if system == None: system = self.find_or_create_system({'StarSystem': self.current_system, 'SystemAddress' : self.system_id})
                        build = self.find_or_create_build(system, {'MarketID': self.market_id,
                                                                   'Name': self.station})
                        build_state = BuildState.PROGRESS
                    # Complete station so find it and add/update as appropriate.
                    elif system != None and self.station != 'FleetCarrier' and re.search(r"^\$", f"{self.station}") == None:
                        build = self.find_or_create_build(system, {'MarketID': self.market_id,
                                                                   'Name': self.station})
                        build_state = BuildState.COMPLETE

                    # If this isn't a colonisation ship or a system we're building, or it's a carrier, scenario, etc. then ignore it.
                    if build == {}:
                        return

                    # Update the system details
                    if not 'Name' in system: system['Name'] = self.current_system

                    # Update the build details
                    Debug.logger.debug(f"Updating build {self.station} in system {self.current_system}")
                    data:dict = {}
                    if self.station != None and build.get('Name', None) != self.station: data['Name'] = self.station
                    if self.market_id != None and build.get('MarketID', None)  != self.market_id: data['MarketID'] = self.market_id
                    if build['State'] != build_state: data['State'] = build_state
                    if self.body != None and build.get('Body', None) != self.body: data['Body'] = self.body
                    if self.location != None and build.get('Location', None) != self.location: data['Location'] = self.location
                    if build_state == BuildState.PROGRESS and build.get('Track') != (build_state != BuildState.COMPLETE): data['Track'] = True
                    if data != {}:
                        self.modify_build(system, system['Builds'].index(build), data)
                        self.bgstally.ui.window_progress.update_display()
                        self.dirty = True

                case 'Market'|'MarketBuy'|'MarketSell':
                    self._update_market(self.market_id)
                    self._update_cargo(state.get('Cargo'))
                    if self.market_id == self.bgstally.fleet_carrier.carrier_id:
                        self._update_carrier()

                case 'SuperCruiseEntry' | 'FSDJump':
                    self.market = {}
                    self.body = None
                    self.station = None
                    self.location = None
                    self.market_id = None

                case 'SupercruiseDestinationDrop':
                    self.location = 'Orbital'

                case 'ApproachBody':
                    self.location = 'Surface'

                case 'SupercruiseExit' | 'ApproachSettlement':
                    if entry.get('event') == 'ApproachSettlement': self.location == 'Surface'

                    # If it's a construction site or colonisation ship wait til we dock.
                    # If it's a carrier or other non-standard location we ignore it. Bet there are other options!
                    if self.station == None or 'Construction Site' in self.station or 'ColonisationShip' in self.station or \
                        re.search('^$', self.station) or re.search('[A-Z0-9]{3}-[A-Z0-9]{3}$', self.station):
                        return

                    # If we don't have this system in our list, we don't care about it.
                    system:dict = self.find_system({'StarSystem' : self.current_system, 'SystemAddress': self.system_id})
                    if system == None: return

                    # It's in a system we're building in, so we should create it.
                    build:dict = self.find_or_create_build(system, {'MarketID': self.market_id,
                                                                   'Name': self.station})

                    # We update them here because it's not possible to dock at installations once they're complete so
                    # you may miss their completion.
                    if build.get('MarketID', None) == None: build['MarketID'] = self.market_id
                    build['State'] = BuildState.COMPLETE
                    build['Name'] = self.station
                    if self.body != None: build['Body'] = self.body
                    build['Track'] = False
                    self.dirty = True

                case 'Undocked':
                    self.market = {}
                    self.station = None
                    self.market_id = None
                    self.body = None
                    self.docked = False

            # Save immediately to ensure we don't lose any data
            if self.dirty == True:
                self.save(entry.get('event'))
            self.bgstally.ui.window_progress.update_display()

        except Exception as e:
            Debug.logger.error(f"Error processing event: {e}")
            Debug.logger.error(traceback.format_exc())


    def body_name(self, body:str) -> str|None:
        """ Get the body name without the system bits or ring suffix"""
        if self.current_system == None: return None
        body = body.replace(self.current_system + ' ', '')
        body = re.sub(r"( [A-Z]){0,1} Ring$", "", body).strip()
        return body


    def get_base_type(self, type_name:str) -> dict:
        ''' Return the details of a particular type of base '''
        if type_name in self.base_types:
            return self.base_types.get(type_name, {})

        for base_type in self.base_types:
            if type_name in self.base_types[base_type].get('Layouts', '').split(', '):
                return self.base_types[base_type]

        return {}

    def get_base_types(self, category:str = 'Any') -> list[str]:
        ''' Get a list of base type names '''
        match category:
            case 'Any' | 'All':
                return list(self.base_types.keys())
            case 'Initial' | 'Starports': # Just the inital build starports
                return [base_type for base_type in self.base_types if self.base_types[base_type].get('Category') in ['Starport', 'Outpost']]
            case 'Ports': # Ports that have the multiple cost penalty
                return [base_type for base_type in self.base_types if self.base_types[base_type].get('Category') in ['Starport', 'Planetary Port']]
            case _:
                # Category (Settlement, Outpost, etc)
                return [base_type for base_type in self.base_types if self.base_types[base_type].get('Category') == category]


    def get_base_layouts(self, category:str = 'All') -> list[str]:
        ''' Get a list of base layout names '''
        layouts:list = []

        if category in self.base_types.keys():
            return list(self.base_types[category]['Layouts'].split(', '))

        for type in self.get_base_types(category):
            if type in self.base_types.keys():
                layouts.extend(self.base_types[type]['Layouts'].split(', '))

        return list(set(layouts))  # Remove duplicates just in case


    def get_all_systems(self) -> list[dict]:
        ''' Get all systems being monitored/planned for colonisation '''
        return self.systems


    def get_system(self, key:str, value) -> dict | None:
        ''' Get a system by any attribute '''
        for i, system in enumerate(self.systems):
            if system.get(key) != None and system.get(key) == value:
                return system
        return


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


    def find_system(self, data:dict) -> dict|None:
        ''' Find a system by address, system name, or plan name '''
        system:dict|None = None
        for m in ['SystemAddress', 'StarSystem', 'Name']:
            if data.get(m, None) != None:
                for i, system in enumerate(self.systems):
                    if system.get(m) != None and system.get(m) == data.get(m):
                        return system
        return None


    def find_or_create_system(self, data:dict) -> dict:
        ''' Find a system by name or plan, or create it if it doesn't exist '''
        system:dict = self.find_system(data)
        if system == None:
            return self.add_system(data)

        return system


    def add_system(self, plan_name:str, system_name:str = None, system_address:int = None, prepop:bool = False, rcsync:bool = False) -> dict|None:
        ''' Add a new system for colonisation planning '''

        if self.find_system({'StarSystem': system_name, 'Name': plan_name}) != None:
            Debug.logger.warning(f"Cannot add system - already exists: {plan_name} {system_name}")
            return

        # Create new system
        system_data:dict = {
            'Name': plan_name,
            'Claimed': '',
            'Builds': []
        }
        if system_name != None: system_data['StarSystem'] = system_name
        if system_address != None: system_data['SystemAddress'] = system_address
        self.systems.append(system_data)
        if rcsync == True:
            if self.rc == None: self.rc = RavenColonial(self)
            self.rc.add_system(system_name)
            system_data['RCSync'] = 1

        # If we have a system address, we get the bodies and maybe stations
        if rcsync == False and system_name != None:
            self.rc.import_bodies(system_name)
            if prepop == True: self.rc.import_stations(system_name)
            self.rc.import_system(system_name)

        self.dirty = True
        self.save('Add system')
        return system_data


    def modify_system(self, ind:int, data:dict) -> dict|None:
        ''' Update a system for colonisation planning '''

        if ind < 0 or ind >= len(self.systems):
            Debug.logger.warning(f"Cannot update system, not found: {ind}")
            return

        system:dict = self.systems[ind]
        Debug.logger.debug(f"{system.get('Name')}")
        # If they change which star system, we need to clear the system address
        if data.get('StarSystem', None) != None and data.get('StarSystem', None) != system.get('StarSystem'):
            system['SystemAddress'] = None
            system['StarSystem'] = data.get('StarSystem')

        for k, v in data.items():
            system[k] = v

        # Add a system if the flag has switched from zero to one
        if data.get('RCSync', 0) == 1 and system.get('RCSync', 0) == 0 and \
            data.get('StarSystem', None) != None:
            if self.rc == None: self.rc = RavenColonial(self)
            self.rc.add_system(system.get('StarSystem'))
            system['RCSync'] = 1

        # If we have a system name but not its address, we can get the bodies from EDSM
        if system.get('StarSystem') != None and system.get('Bodies', None) == None:
            self.rc.import_bodies(system.get('StarSystem', ''))

        self.dirty = True
        self.save('Modify system')
        return system


    def get_body(self, system:dict, body) -> dict|None:
        ''' Get a body by name or id from a system '''
        for b in system.get('Bodies', []):
            if isinstance(body, str) and body in [b.get('name', None), b.get('name', '').replace(system['StarSystem'] + ' ', '')]:
                return b
            if isinstance(body, int) and body == b.get('bodyId', None):
                return b
        return

    def get_bodies(self, system:dict, bt:str = 'All') -> list:
        ''' Return a list of bodies in the system filtered by type if required '''
        bodies:list = []
        for b in system.get('Bodies', []):
            name = b.get('name') if b.get('name') != system['StarSystem'] else 'A'
            name = name.replace(system['StarSystem'] + ' ', '').strip()
            match bt:
                case 'Surface':
                    if b.get('isLandable', False) == True:
                        bodies.append(name)
                case _:
                    bodies.append(name)

        return bodies


    def remove_system(self, sysnum:int) -> None:
        ''' Delete a system '''
        systems = self.get_all_systems() # It's a sorted list, index isn't reliable unless sorted!
        del systems[sysnum]
        self.dirty = True
        self.save('System removed')


    def get_build_state(self, build:dict) -> BuildState:
        ''' Get the state of a build from either the build or the progress data '''
        if build.get('State', None) == BuildState.COMPLETE or build.get('MarketID', None) == None:
            return build.get('State', BuildState.PLANNED)

        # If we have a progress entry, use that
        for p in self.progress:
            if p.get('MarketID') == build.get('MarketID'):
                if p.get('ConstructionComplete', False) == True:
                    Debug.logger.debug(f"Finished build {build.get('Name', 'Unknown')} {build.get('MarketID', 'Unknown')}")
                    self.try_complete_build(p.get('MarketID'))
                    return BuildState.COMPLETE
                return BuildState.PROGRESS

        # Otherwise, use the state of the build
        return build.get('State', BuildState.PLANNED)


    def get_tracked_builds(self) -> list[dict]:
        ''' Get all builds that are being tracked '''
        tracked:list = []
        for system in self.systems:
            for build in self.get_system_builds(system):
                if build.get("Track", False) == True and self.get_build_state(build) != BuildState.COMPLETE:
                    b:dict = build.copy()
                    b['Plan'] = system.get('Name', '')
                    b['StarSystem'] = system.get('StarSystem', '')
                    tracked.append(b)

        return tracked


    def get_system_builds(self, system:dict) -> list[dict]:
        ''' Get all builds for a system '''
        return system.get('Builds', [])


    def find_build(self, system:dict, data:dict) -> dict|None:
        '''
        Get a build by a range and/or combinatino of attributes.
        Marketid, RCID or name are preferred but we use fuzzy matching for weird fdev cases
        '''
        builds:list = self.get_system_builds(system)

        if data.get('Name', '') == '' or data.get('Name', '') == ' ': data['Name'] = None

        # Colonisation ship must be build 0
        if data.get('Name', None) != None and 'System Colonisation Ship' in data.get('Name', '') and len(builds) > 0:
            return builds[0]

        # An existing/known build?
        for m in ['MarketID', 'RCID', 'Name']:
            if data.get(m, None) != None:
                for build in builds:
                    if build.get(m, None) == data.get(m, None):
                        return build

        # Match the first planned build with the right body and location (orbital or surface)
        if data['Name'] != None and 'Construction Site' in data['Name'] and data.get('Body', None) != None:
            loc:str = re.sub(r" Construction Site:.*$", "", data['Name'])
            if loc == 'Planetary': loc = 'Surface'
            Debug.logger.debug(f"Find build matching construction: {data.get('Name')} {data.get('Body')} {loc}")

            for build in builds:
                if build.get('RCID', None) == None and build.get('MarketID', None) == None and \
                    data.get('Body') and build.get('Body', '').lower() == data['Body'].lower() and \
                    build.get('State', None) == BuildState.PLANNED and build.get('Location', None) == loc:
                    Debug.logger.debug(f"Matched on {data['Body']} {build.get('State', None)} {loc} Build: {build}")
                    return build

        # Match a completed but as yet unknown build.
        # This is used to find the new base that's created once a build completes
        for build in builds:
            if build.get('State', None) == BuildState.COMPLETE and build.get('MarketID', '') == '' and \
                data.get('Body', None) and build.get('Body', '').lower() == data.get('Body', '').lower() and \
                build.get('Location') == data.get('Location', None):
                Debug.logger.debug(f"Matched on {build.get('Body')} {build.get('State', None)} {build.get('Location', '')} Build: {build}")
                return build

        Debug.logger.debug(f"Build not found for: {data}")
        return None


    def find_or_create_build(self, system:dict, data:dict) -> dict:
        ''' Find a build by marketid or name, or create it if it doesn't exist '''
        build:dict|None = self.find_build(system, data)
        if build == None:
            return self.add_build(system, data)

        return build


    def add_build(self, system, data:dict, silent:bool = False) -> dict:
        ''' Add a new build to a system '''

        # Yea this is terrible but it works for now.
        if isinstance(system, int):
            system = self.systems[system]

        Debug.logger.info(f"Adding build {data.get('Name')}")

        if 'State' not in data: data['State'] = BuildState.PLANNED
        if 'Name' not in data: data['Name'] = ""

        # If we have a body name or id set the corresponding value.
        body:dict|None
        if data.get('BodyNum', None) != None:
            body = self.get_body(system, data.get('BodyNum', None))
            if body != None and body.get('name', None) != None:
                data['Body'] = body['name'].replace(system.get('StarSystem', '') + ' ', '')
        elif data.get('Body', None) != None:
            body = self.get_body(system, data.get('Body', None))
            if body != None and body.get('bodyId', None) != None:
                data['BodyNum'] = body['bodyId']

        if data.get('Base Type', '') == '' and data.get('Layout', None) != None:
            data['Base Type'] = self.get_base_type(data.get('Layout', ''))

        system['Builds'].append(data)

        # Update RC if appropriate and we have enough data about the system.
        if silent == False and system.get('RCSync') == 1 and system.get('SystemAddress', None) != None and \
            data.get('Layout', None) != None and data.get('BodyNum', None) != None:
            if self.rc == None: self.rc = RavenColonial(self)
            self.rc.upsert_site(system, data)

        self.dirty = True
        self.save('Build added')

        return data


    def remove_build(self, system, ind:int) -> None:
        ''' Remove a build from a system '''
        if isinstance(system, int):
            system = self.systems[system]

        if system == None:
            Debug.logger.warning(f"Cannot remove build - unknown system")
            return

        # Support marketid or index
        if ind > len(system['Builds']):
            for i, build in enumerate(system['Builds']):
                if build.get('MarketID') == ind:
                    ind = i
                    break

        if ind >= len(system['Builds']):
            Debug.logger.warning(f"Cannot remove build - invalid build index: {ind} {len(system['Builds'])} {system['Builds']}")
            return

        if system.get('RCSync', 0) == 1:
            if self.rc == None: self.rc = RavenColonial(self)
            self.rc.remove_site(system, ind)

        # Remove build
        system['Builds'].pop(ind)
        self.dirty = True
        self.save('Build removed')


    def set_base_type(self, system, ind:int, type:str) -> None:
        """ Set/update the type of a given base using type or layout """

        Debug.logger.debug(f"Seting base type {type}")

        data = {'Base Type' : '', 'Layout' : '', 'Location': '' }
        if type != ' ':
            bt = self.get_base_type(type)
            data = {'Base Type' : bt['Type'], 'Location': bt['Location'] }
            layouts:list = self.get_base_layouts(bt['Type'])
            if len(layouts) == 1: data['Layout'] = layouts[0]
            if type in layouts: data['Layout'] = type

        if ind >= len(system['Builds']):
            data['State'] = BuildState.PLANNED
            self.add_build(system, data)
            return

        self.modify_build(system, ind, data)


    def modify_build(self, system, ind:int, data:dict, silent:bool = False) -> None:
        ''' Modify a build in a system '''
        try:

            Debug.logger.debug(f"Modifying build {data}")
            if isinstance(system, int):
                system = self.systems[system]

            if ind >= len(system['Builds']):
                Debug.logger.error(f"modify_build called for non-existent build: {ind}")
                return

            build:dict = system['Builds'][ind]

            # If the body number is changing update the body name to match.
            if data.get('BodyNum', None) != None:
                body:dict = self.get_body(system, data.get('BodyNum'))
                if body != None and body.get('name', None) != None:
                    data['Body'] = body['name'].replace(system.get('StarSystem', '') + ' ', '')

            # If the Body is set but the body number isn't then set it.
            if build.get('BodyNum', None) == None and build.get('Body'):
                body:dict = self.get_body(system, build['Body'])
                if body != None and body.get('name', None) != None:
                    data['BodyNum'] = body['bodyId']

            # If the base type isn't set, try to get it from the layout
            if data.get('Base Type', '') == '' and data.get('Layout', None) != None:
                data['Base Type'] = self.get_base_type(data.get('Layout', ''))

            changed:bool = False
            for k, v in data.items():
                if k == 'Track' and build.get(k, '') != v:
                    build[k] = v
                    self.bgstally.ui.window_progress.update_display()

                if build.get(k, None) != v:
                    build[k] = v.strip() if isinstance(v, str) else v
                    changed = True

            # Send our updates back to RavenColonial if we're tracking this system and have the details required
            if silent == False and changed == True and \
                system.get('RCSync') == 1 and system.get('SystemAddress', None) != None and \
                build.get('Layout', None) != None and build.get('BodyNum', None) != None:
                if self.rc == None: self.rc = RavenColonial(self)
                self.rc.upsert_site(system, build)
                for p in self.progress:
                    if p.get('ProjectID', None) != None and p.get('MarketID', None) == build.get('MarketID'):
                        self.rc.upsert_project(system, build, p)

            self.dirty = True
            self.save('Build modified')
            return
        except Exception as e:
            Debug.logger.error(f"Error modifying build: {e}")
            Debug.logger.error(traceback.format_exc())


    def try_complete_build(self, market_id:int) -> bool:
        ''' Determine if a build has just been completed and if so mark it as such '''
        try:
            system = self.find_system({'StarSystem' : self.current_system, 'SystemAddress': self.system_id})
            if system == None:
                return False
            build:dict|None = self.find_build(system, {'MarketID' : market_id})
            if build == None:
                return False
            if build.get('State') == BuildState.COMPLETE:
                return False

            Debug.logger.debug(f"Completing build {self.current_system} {self.system_id} {market_id}")
            # If we get here, the build is (newly) complete.
            # Since on completion the construction depot is removed/goes inactive and a new station is created
            # we need to clear some fields.
            self.modify_build(system, system['Builds'].index(build), {
                'State': BuildState.COMPLETE,
                'Track': False,
                'MarketID': None,
                'Name': re.sub(r"(\w+ Construction Site:|$EXT_PANEL_ColonisationShip;) ", "", build.get('Name'))
            })
            return True

        except Exception as e:
            Debug.logger.error(f"Error completing build: {e}")
            Debug.logger.error(traceback.format_exc())
            return False


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
            return []

    def _get_progress(self, builds:list[dict], type:str) -> list[dict]:
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
                            res = p.get(type)
                            break
                # No actual data so we use the estimates from the base costs
                if res == {} and type != 'Delivered': res = self.base_costs.get(b.get('Base Type'), {})
                found += 1
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
            return []

    def get_required(self, builds:list[dict]) -> list:
        ''' Return the commodities required for the builds listed '''
        return self._get_progress(builds, 'Required')


    def get_delivered(self, builds:list[dict]) -> list:
        ''' Return the commodities delivered for the builds listed '''
        return self._get_progress(builds, 'Delivered')


    def find_or_create_progress(self, id:int) -> dict:
        ''' Find or if necessary create progress for a given market '''
        p:dict|None = self.find_progress(id)
        if p != None:
            return p

        prog:dict = { 'MarketID': id }
        self.progress.append(prog)

        self.dirty = True
        return prog


    def find_progress(self, id:int) -> dict|None:
        ''' Find and return progress for a given market '''
        for p in self.progress:
            if p.get('MarketID') == id:
                return p

        return None


    def update_progress(self, id:int, data:dict) -> None:
        ''' Update a progress record '''
        try:
            progress:dict|None = self.find_progress(id)
            if progress == None: return
            changed:bool = False

            # Handle a ColonisationConstructionDepot event
            if data.get('ResourcesRequired', None) != None:
                req = {comm['Name'] : comm['RequiredAmount'] for comm in data.get('ResourcesRequired', [])}
                if progress.get('Required', None) != req:
                    progress['Required'] = req
                    changed = True
                deliv = {comm['Name'] : comm['ProvidedAmount'] for comm in data.get('ResourcesRequired', [])}
                if progress.get('Delivered', None) != deliv:
                    progress['Delivered'] = deliv
                    changed = True
                del data['ResourcesRequired']
                changed = True

            # Copy over whatever data we receive
            for k, v in data.items():
                # Recalculate the provided amount based on what RC says remains to be delivered
                if k == 'Remaining':
                    deliv = {f"${key}_name;" : progress['Required'][key] - val for key,val in v}
                    if progress.get('Delivered', None) != deliv:
                        progress['Delivered'] = deliv
                        changed = True
                    continue

                if progress.get(k) != v:
                    progress[k] = v
                    changed = True

            if changed != True:
                return

            self.dirty = True

            # If it's complete mark it as complete
            if data.get('ConstructionComplete', False) == True:
                self.try_complete_build(progress.get('MarketID', 0))
                if progress.get('ProjectID', None) != None:
                    self.rc.complete_site(progress.get('ProjectID', 0))
                return

            system:dict|None = self.find_system({'StarSystem' : self.current_system, 'SystemAddress': self.system_id})
            if system != None and system.get('RCSync', 0) == 1: build = self.find_build(system, {'MarketID' : self.market_id})
            if system == None or build == None:
                Debug.logger.warning(f"System {self.current_system} not found for build {self.market_id}")
                return

            # RC Sync if appropriate
            if system.get('RCSync', 0) == 1:
                self.rc.upsert_project(system, build, progress)

            return

        except Exception as e:
            Debug.logger.info(f"update progress error {id} {data}")
            Debug.logger.error(traceback.format_exc())


    def _update_carrier(self) -> None:
        ''' Update the carrier cargo data. '''
        try:
            if self.bgstally.fleet_carrier.available() == False:
                return
            cargo:dict = {}

            for item in self.bgstally.fleet_carrier.cargo:
                n = item.get('commodity')
                n = f"${n.lower().replace(' ', '')}_name;"
                if n not in cargo:
                    cargo[n] = 0
                cargo[n] += int(item['qty'])

            if cargo != self.carrier_cargo and self.rc != None:
                self.rc.update_carrier(self.bgstally.fleet_carrier.carrier_id, cargo)
                self.dirty = True

            self.carrier_cargo = cargo

        except Exception as e:
            Debug.logger.info(f"Carrier update error")
            Debug.logger.error(traceback.format_exc())


    def _update_cargo(self, cargo:dict) -> None:
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


    def _update_market(self, market_id:int = None) -> None:
        ''' Update market info from the market object or directly '''
        try:
            if market_id == None or self.docked == False:
                self.market = {}
                return

            market:dict = {}
            if self.bgstally.market.available(market_id):
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
                if market_id == json_data['MarketID']:
                    for item in json_data['Items']:
                        if item.get('Stock') > 0:
                            market[item.get('Name')] = item.get('Stock')
            self.market = market
            return

        except Exception as e:
            Debug.logger.info(f"Unable to load {MARKET_FILENAME} from the player journal folder")
            Debug.logger.error(traceback.format_exc())


    def _load(self) -> None:
        ''' Load state from file '''
        try:
            file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
            if path.exists(file):
                with open(file) as json_file:
                    self._from_dict(json.load(json_file))

        except Exception as e:
            Debug.logger.warning(f"Unable to load {file}")
            Debug.logger.error(traceback.format_exc())


    def save(self, cause:str = 'Unknown') -> None:
        ''' Save state to file '''

        file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self._as_dict(), outfile, indent=4)

        self.dirty = False


    def _as_dict(self) -> dict:
        ''' Return a Dictionary representation of our data, suitable for serializing '''

        # System tab order
        def sort_order(item:dict) -> str:
            state:BuildState = BuildState.COMPLETE
            for b in item['Builds']:
                bs = self.get_build_state(b)
                if bs == BuildState.PLANNED and state != BuildState.PROGRESS:
                    state = BuildState.PLANNED
                if bs == BuildState.PROGRESS and b.get('Track', False) == True:
                    state = BuildState.PROGRESS
            return state.value

        # Builds order
        def build_order(item:dict) -> int:
            match self.get_build_state(item):
                case BuildState.COMPLETE: return 0
                case BuildState.PROGRESS: return 1
                case _: return 2

        # We sort the order of systems when saving so that in progress systems are first, then planned, then complete.
        # Fortuitously our desired order matches the reverse alpha of the states
        systems:list = list(sorted(self.systems, key=sort_order, reverse=True))
        for system in systems:
            if len(system['Builds']) > 1:
                system['Builds'] = [system['Builds'][0]] + list(sorted(system['Builds'][1:], key=build_order))

        # Migrate the project progress. This can be removed in the future
        for progress in self.progress:
            if progress.get('ResourcesRequired', None) != None:
                progress['Required'] = {comm['Name'] : comm['RequiredAmount'] for comm in progress.get('ResourcesRequired')}
                progress['Delivered'] = {comm['Name'] : comm['ProvidedAmount'] for comm in progress.get('ResourcesRequired')}
                del progress['ResourcesRequired']

        # Remove empty build entries
        #for system in systems:
        #    for i, b in enumerate(system.get('Builds', [])):
        #        if b.get('Base Type', '') == '' and b.get('Name', '') == '':
        #            del system['Builds'][i]

        units:list = []
        for v in self.bgstally.ui.window_progress.units:
            units.append(v.value)

        return {
            'Docked': self.docked,
            'SystemID': self.system_id,
            'CurrentSystem': self.current_system,
            'Body': self.body,
            'Station': self.station,
            'MarketID': self.market_id,
            'Progress': self.progress,
            'Systems': systems,
            'CargoCapacity': self.cargo_capacity,
            'ProgressView' : self.bgstally.ui.window_progress.view.value,
            'ProgressUnits': units,
            'ProgressColumns': self.bgstally.ui.window_progress.columns,
            'BuildIndex'   : self.bgstally.ui.window_progress.build_index
            }


    def _from_dict(self, dict:dict) -> None:
        ''' Populate our data from a Dictionary that has been deserialized '''
        self.docked = dict.get('Docked', False)
        self.system_id = dict.get('SystemID', None)
        self.current_system = dict.get('CurrentSystem', None)
        self.body = dict.get('Body', None)
        self.station = dict.get('Station', None)
        self.market_id = dict.get('MarketID', None)
        self.progress = dict.get('Progress', [])
        self.systems = dict.get('Systems', [])
        self.cargo_capacity = dict.get('CargoCapacity', 784)
        self.bgstally.ui.window_progress.view = ProgressView(dict.get('ProgressView', 0))

        units = dict.get('ProgressUnits', [])
        for i, v in enumerate(units):
            self.bgstally.ui.window_progress.units[i] = ProgressUnits(v)
        self.bgstally.ui.window_progress.build_index = dict.get('BuildIndex', 0)