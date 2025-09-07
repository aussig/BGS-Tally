import csv
import json
from os import path
from os.path import join
import time
import traceback
import re
import functools
from datetime import datetime
from config import config # type: ignore
from bgstally.constants import FOLDER_OTHER_DATA, FOLDER_DATA, BuildState, CommodityOrder, ProgressUnits, ProgressView
from bgstally.debug import Debug
from bgstally.utils import _, get_by_path, get_localised_filepath, catch_exceptions
from bgstally.ravencolonial import RavenColonial, EDSM, Spansh

FILENAME = "colonisation.json"
BASE_TYPES_FILENAME = 'base_types.json'
BASE_COSTS_FILENAME = 'base_costs.json'
CARGO_FILENAME = 'Cargo.json'
MARKET_FILENAME = 'Market.json'

# Services we use for different types of import
SYSTEM_SERVICE = Spansh()
BODY_SERVICE = EDSM()
STATION_SERVICE = Spansh()


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
    def __init__(self, bgstally) -> None:
        self.bgstally:BGSTally = bgstally # type: ignore
        self.system_id:int|None = None
        self.current_system:str|None = None
        self.body:str|None = None
        self.station:str|None = None
        self.location:str|None = None # Orbital, Surface, etc.
        self.market_id:int|None = None
        self.docked:bool = False
        self.base_types:dict = {}  # Loaded from base_types.json
        self.base_costs:dict = {}  # Loaded from base_costs.json
        self.systems:list = []     # Systems with colonisation
        self.progress:list = []    # Construction progress data
        self.dirty:bool = False

        self.cargo:dict = {}       # Local store of our current cargo
        self.carrier_cargo:dict = {} # Local store of our current carrier cargo
        self.market:dict = {}      # Local store of the current market data
        self.cargo_capacity:int = 784 # Default cargo capacity

        self.cmdr:str|None = None

        # Valid keys for colonisation.json entries. These help avoid sending unnecessary data to third parties or storing unncessary data in the save file.
        self.system_keys:list = ['Name', 'StarSystem', 'SystemAddress', 'Claimed', 'Builds', 'Notes', 'Population', 'Economy', 'Security' 'RScync', 'Architect', 'Rev', 'Bodies', 'EDSMUpdated', 'Hidden', 'SpanshUpdated', 'RCSync']
        self.build_keys:list = ['Name', 'Plan', 'State', 'Base Type', 'Body', 'BodyNum', 'MarketID', 'Track', 'StationEconomy', 'Layout', 'Location', 'BuildID', 'ProjectID']
        self.progress_keys:list = ['MarketID', 'Updated', 'ConstructionProgress', 'ConstructionFailed', 'ConstructionComplete', 'ProjectID', 'Required', 'Delivered']

        # Load base commodities, types, costs, and saved data
        self._load_base_types()
        self._load_base_costs()
        self._load()


    @catch_exceptions
    def _load_base_types(self) -> None:
        ''' Load base type definitions from base_types.json '''
        base_types_path = path.join(self.bgstally.plugin_dir, FOLDER_DATA, BASE_TYPES_FILENAME)
        with open(base_types_path, 'r') as f:
            self.base_types = json.load(f)
            Debug.logger.info(f"Loaded {len(self.base_types)} base types for colonisation")


    @catch_exceptions
    def _load_base_costs(self) -> None:
        '''
        Load base cost definitions from base_costs.json
        The 'All' category is used to list all the colonisation commodities and their inara IDs
        '''
        base_costs_path:str = path.join(self.bgstally.plugin_dir, FOLDER_DATA, BASE_COSTS_FILENAME)
        with open(base_costs_path, 'r') as f:
            self.base_costs = json.load(f)
            Debug.logger.info(f"Loaded {len(self.base_costs)} base costs for colonisation")

            # Update base_types with total commodity counts from base_costs
            for base_type in self.base_costs.keys():
                if base_type in self.base_types:
                    self.base_types[base_type]['Total Comm'] = sum(self.base_costs[base_type].values())


    @catch_exceptions
    def journal_entry(self, cmdr, is_beta, sys, station, entry, state) -> None:
        '''
        Parse and process incoming journal entries
        This method is called by the bgstally plugin when a journal entry is received.
        '''
        rc:RavenColonial = RavenColonial(self)
        if state.get('CargoCapacity', 0) != None and state.get('CargoCapacity', 0) > 16 and state.get('CargoCapacity', 0) != self.cargo_capacity:
            self.cargo_capacity = state.get('CargoCapacity')
            self.dirty = True

        if entry.get('StarSystem', None): self.current_system = entry.get('StarSystem')
        if entry.get('SystemAddress', None): self.system_id = int(entry.get('SystemAddress'))
        if entry.get('MarketID', None) != None: self.market_id = entry.get('MarketID')
        if entry.get('Type', None) != None: self.station = entry.get('Type')
        if entry.get('BodyType', None) == 'Station': self.station = entry.get('Body')
        if entry.get("StationName", None): self.station = entry.get('StationName')
        if self.current_system != None and self.current_system in entry.get('Body', ' '): self.body = self.body_name(self.current_system, entry.get('Body'))

        Debug.logger.debug(f"Event: {entry.get('event')} -- SystemID: {self.system_id} Sys: {self.current_system} body: {self.body} station: {self.station} market: {self.market_id}")

        match entry.get('event'):
            case 'StartUp': # Synthetic event.
                self._update_cargo(state.get('Cargo'))
                self._update_market(self.market_id)
                self._update_carrier()

                # Update systems with external data if required
                for system in self.systems:
                    if system.get('Hidden', False) == True: continue

                    if system.get('RCSync', False) == True:
                        self.cmdr = cmdr # Used in RavenColonial sync
                        rc.load_system(system.get('SystemAddress', 0), system.get('Rev', 0))

                    if system.get('Bodies', None) == None: # In case we didn't get them for some reason
                        BODY_SERVICE.import_bodies(system.get('StarSystem', ''))

                    SYSTEM_SERVICE.import_system(system.get('StarSystem', '')) # Update the system stats from Spansh/EDSM

                for progress in self.progress:
                    if progress.get('ProjectID', None) != None and progress.get('ConstructionComplete', False) == False:
                        rc.load_project(progress)

            case 'Cargo' | 'CargoTransfer':
                self._update_cargo(state.get('Cargo'))
                self._update_carrier()

            case 'ColonisationContribution':
                if not self.current_system or not self.system_id or not self.market_id:
                    Debug.logger.warning(f"Invalid ColonisationContribution event: {entry}")
                    return

                system:dict|None = self.find_system({'StarSystem' : self.current_system, 'SystemAddress': self.system_id})
                if system != None and system.get('RCSync', False) == True:
                    for progress in self.progress:
                        if progress.get('MarketID', None) == self.market_id and progress.get('ProjectID', None) != None:
                            rc.record_contribution(progress.get('ProjectID', 0), entry.get('Contributions', []))
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
                    Debug.logger.warning(f"Invalid ColonisationConstructionDepot event (no market): {entry}")
                    return

                system = self.find_system({'StarSystem': self.current_system, 'SystemAddress' : self.system_id})
                if system == None:
                    Debug.logger.warning(f"Invalid ColonisationConstructionDepot event (no system): {entry}")
                    return
                progress:dict = self.find_or_create_progress(self.market_id)
                self.update_progress(self.market_id, entry)

            case 'Docked':
                self._update_market(self.market_id)
                self.docked = True
                system = self.find_system({'StarSystem' : self.current_system, 'SystemAddress': self.system_id})
                build_state:BuildState|None = None
                build = {}

                    # Colonisation ship is always the first build. find/add system. find/add build
                    # Construction site can be any build, so find/add system, find/add build
                if '$EXT_PANEL_ColonisationShip' in f"{self.station}" or 'Construction Site' in f"{self.station}":
                    Debug.logger.debug(f"Docked at construction site. Finding/creating system and build")
                    if system == None: system = self.find_or_create_system({'StarSystem': self.current_system, 'SystemAddress' : self.system_id})
                    build = self.find_or_create_build(system, {'MarketID': self.market_id, 'Name': self.station, 'Body': self.body})
                    build_state = BuildState.PROGRESS
                # Complete station so find it and add/update as appropriate.
                elif system != None and self.station != 'FleetCarrier' and \
                    re.search(r"^...\-...$", f"{self.station}") == None and \
                    re.search(r"^\$", f"{self.station}") == None:
                    Debug.logger.debug(f"Docked at site. Finding/creating system and build {self.market_id} {self.station}")
                    build = self.find_or_create_build(system, {'MarketID': self.market_id, 'Name': self.station, 'Body': self.body})
                    build_state = BuildState.COMPLETE

                # If this isn't a colonisation ship or a system we're building, or it's a carrier, scenario, etc. then ignore it.
                if system == None or build == {}:
                    return

                # Update the system details
                if system.get('Name', None) != None: system['Name'] = self.current_system

                # Update the build details
                data:dict = {}
                if self.station != None and build.get('Name', None) != self.station: data['Name'] = self.station
                if build['State'] != build_state: data['State'] = build_state
                if self.market_id != None and build.get('MarketID', None) != self.market_id: data['MarketID'] = self.market_id
                if self.market_id != None and build.get('BuildID', None) == None: build['BuildID'] = f"x{int(time.time())}" if build_state == BuildState.COMPLETE else f"&{int(time.time())}"
                if self.body != None and build.get('Body', None) != self.body: data['Body'] = self.body
                if self.location != None and build.get('Location', None) != self.location: data['Location'] = self.location
                if build_state == BuildState.PROGRESS and build.get('Track') != (build_state != BuildState.COMPLETE): data['Track'] = True
                if data != {}:
                    Debug.logger.debug(f"Docked updating build {self.station} in system {self.current_system} {data}")
                    self.modify_build(system, build.get('BuildID', ''), data)
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
                if entry.get('event') == 'ApproachSettlement': self.location = 'Surface'

                # If it's a construction site or colonisation ship wait til we dock.
                # If it's a carrier or other non-standard location we ignore it.
                if self.station == None or 'Construction Site' in self.station or 'ColonisationShip' in self.station or \
                    re.search(r"^\$", self.station) or re.search("[A-Z0-9]{3}-[A-Z0-9]{3}$", self.station):
                    return

                # If we don't have this system in our list, we don't care about it.
                system:dict|None = self.find_system({'StarSystem' : self.current_system, 'SystemAddress': self.system_id})
                if system == None: return

                # It's in a system we're building in, so we should create it.
                Debug.logger.debug(f"Finding build {self.market_id} {self.station} {self.body}")
                build:dict = self.find_or_create_build(system, {'MarketID': self.market_id,
                                                                'Name': self.station,
                                                                'Body': self.body})
                Debug.logger.debug(f"Supercruise exit, build: {build}")
                # We update them here because it's not possible to dock at installations once they're complete so
                # you may miss their completion.

                # If we matched on a construction site and this is not one then we complete the build because
                # someone else finished it
                if build.get('State') == BuildState.PROGRESS and 'Construction Site' in build.get('Name', ''):
                    Debug.logger.debug(f"Trying to complete build")
                    self.try_complete_build(build.get('MarketID', 0))
                build['MarketID'] = self.market_id
                build['State'] = BuildState.COMPLETE
                build['Name'] = self.station
                build['Body'] = self.body
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


    @catch_exceptions
    def body_name(self, sysname:str, body:str) -> str|None:
        """ Get the body name without the system prefix or ring suffix"""

        if body == None or body == '': return
        body = body.replace(sysname + ' ', '').strip()
        body = re.sub(r"( [A-Z]){0,1} Ring$", "", body)
        if body == sysname: return 'A'
        return body


    @catch_exceptions
    def get_base_type(self, type_name:str) -> dict:
        ''' Return the details of a particular type of base '''
        if type_name == None or type_name == '': return {}

        # By Type
        if self.base_types.get(type_name, None) != None:
            return self.base_types.get(type_name, {})

        # By layout
        for bt in self.base_types.values():
            if type_name in bt.get('Layouts', '').split(', '):
                return bt

        return {}


    @catch_exceptions
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


    @catch_exceptions
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


    @catch_exceptions
    def get_system(self, key:str, value) -> dict | None:
        ''' Get a system by any attribute '''
        for i, system in enumerate(self.get_all_systems()):
            if system.get(key) != None and system.get(key) == value:
                return system
        return


    @catch_exceptions
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


    @catch_exceptions
    def find_system(self, data:dict) -> dict|None:
        ''' Find a system by address, system name, or plan name '''
        system:dict|None = None
        for m in ['SystemAddress', 'StarSystem', 'Name']:
            if data.get(m, None) != None:
                for i, system in enumerate(self.get_all_systems()):
                    if system.get(m) != None and system.get(m) == data.get(m):
                        return system
        return None


    @catch_exceptions
    def find_or_create_system(self, data:dict) -> dict:
        ''' Find a system by name or plan, or create it if it doesn't exist '''
        system:dict|None = self.find_system(data)
        if system == None:
            return self.add_system(data)

        return system


    @catch_exceptions
    def add_system(self, data:dict, prepop:bool = False, rcsync:bool = False) -> dict:
        ''' Add a new system for colonisation planning '''

        if data.get('StarSystem', None) == None and data.get('Name', None) == None:
            Debug.logger.warning(f"Cannot add system - no name or system: {data}")
            return {}

        # Create new system
        if data.get('Name', None) == None: data['Name'] = data.get('StarSystem', '')
        if data.get('Builds', None) == None: data['Builds'] = []
        self.systems.append(data)
        if rcsync == True and data.get('StarSystem', None) != None:
            RavenColonial(self).add_system(data.get('StarSystem', ''))
            data['RCSync'] = True

        # If we have a system address, we get the bodies and maybe stations
        if rcsync == False and data.get('StarSystem', None) != None:
            BODY_SERVICE.import_bodies(data.get('StarSystem', ''))
            if prepop == True: STATION_SERVICE.import_stations(data.get('StarSystem', ''))
            SYSTEM_SERVICE.import_system(data.get('StarSystem', ''))

        self.save('Add system')
        return data


    @catch_exceptions
    def modify_system(self, system, data:dict) -> dict|None:
        ''' Update a system for colonisation planning '''

        if isinstance(system, int): system = self.systems[system]
        Debug.logger.debug(f"modify_system: {system.get('StarSystem')} {data}")
        if system == None:
            Debug.logger.warning(f"Cannot update system, not found: {system}")
            return

        # If they change which star system, we need to clear the system address
        if data.get('StarSystem', None) != None and data.get('StarSystem', None) != system.get('StarSystem'):
            system['SystemAddress'] = None
            system['StarSystem'] = data.get('StarSystem')

        for k, v in data.items():
            if k not in self.system_keys: continue
            system[k] = v

        # Add a system if the flag has switched from zero to one
        if data.get('RCSync', False) == True and system.get('RCSync', False) == False and \
            data.get('StarSystem', None) != None:
            RavenColonial(self).add_system(system.get('StarSystem', ''))
            system['RCSync'] = True

        # If we have a system name but not its address, we can get the bodies from EDSM
        if system.get('StarSystem') != None and system.get('Bodies', None) == None:
            BODY_SERVICE.import_bodies(system.get('StarSystem', ''))

        self.save('Modify system')

        return system


    @catch_exceptions
    def get_body(self, system:dict, body:str|int) -> dict|None:
        ''' Get a body by name or id from a system '''
        for b in system.get('Bodies', []):
            # EDSM uses bodyId & name
            if isinstance(body, str) and body == self.body_name(system['StarSystem'], b.get('name', '')):
                return b
            if isinstance(body, int) and body == b.get('bodyId', None):
                return b
        return None


    @catch_exceptions
    def get_bodies(self, system:dict, bt:str = 'All') -> list:
        ''' Return a list of bodies in the system filtered by type if required '''
        bodies:list = []
        for b in system.get('Bodies', []):
            name:str|None = self.body_name(system['StarSystem'], b.get('name', ''))
            match bt:
                case 'Surface':
                    if b.get('isLandable', False) == True:
                        bodies.append(name)
                case _:
                    bodies.append(name)

        return bodies


    @catch_exceptions
    def remove_system(self, sysnum:int) -> None:
        ''' Delete a system '''
        systems = self.get_all_systems() # It's a sorted list, index isn't reliable unless sorted!
        del systems[sysnum]
        self.save('System removed')


    @catch_exceptions
    def get_build_state(self, build:dict) -> BuildState:
        ''' Get the state of a build from either the build or the progress data '''
        if build.get('State', None) == BuildState.COMPLETE or build.get('MarketID', None) == None:
            return build.get('State', BuildState.PLANNED)

        # If we have a progress entry, use that
        for p in self.progress:
            if p.get('MarketID') == build.get('MarketID') and p.get('ConstructionComplete', False) == True:
                    self.try_complete_build(p.get('MarketID'))
                    return BuildState.COMPLETE
            if p.get('MarketID') == build.get('MarketID'):
                return BuildState.PROGRESS

        # Otherwise, use the state of the build
        return build.get('State', BuildState.PLANNED)


    @catch_exceptions
    def get_tracked_builds(self) -> list[dict]:
        ''' Get all builds that are being tracked '''
        tracked:list = []
        for system in self.get_all_systems():
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


    @catch_exceptions
    def find_build_any(self, data:dict) -> list:
        ''' Find a build in any system and return the system and build '''
        for system in self.get_all_systems():
            build:dict|None = self.find_build(system, data)
            if build != None: return [system, build]
        return [None, None]


    @catch_exceptions
    def find_build(self, system:dict, data:dict) -> dict|None:
        '''
        Get a build by a range and/or combinatino of attributes.
        Marketid, BuildID or name are preferred but we use fuzzy matching for weird fdev cases
        '''
        builds:list = self.get_system_builds(system)

        if data.get('Name', '') == '' or data.get('Name', '') == ' ': data['Name'] = None

        # Colonisation ship must be build 0
        if data.get('Name', None) != None and 'System Colonisation Ship' in data.get('Name', '') and len(builds) > 0:
            return builds[0]

        # An existing/known build?
        for m in ['BuildID', 'Name', 'MarketID']:
            if data.get(m, None) != None:
                for build in builds:
                    if build.get(m, None) == data.get(m, None):
                        return build

        # Do some fuzzy matching on name similarity, body, etc. for things that may have changed while we were away.
        loc:str = ''
        if data.get('Name', None) != None and 'Construction Site' in data.get('Name', ''):
            loc = re.sub(r" Construction Site:.*$", "", data.get('Name', ''))
            if loc == 'Planetary': loc = 'Surface'

        for build in builds:
            # A build that was planned but is now a construction site
            if build.get('State', None) == BuildState.PLANNED and build.get('BuildID', None) == None and \
                build.get('MarketID', None) == None and build.get('Location', None) == loc and \
                    data.get('Body') and build.get('Body', '').lower() == data['Body'].lower():
                Debug.logger.debug(f"Matched planned build {data['Body']} {build.get('State', None)} {loc} Build: {build}")
                return build

            # A build that was in progress but is now completed
            if build.get('State', None) == BuildState.PROGRESS and \
                f"Construction Site: {data.get('Name', '')}" in build.get('Name', '') and \
                data.get('Body', None) and build.get('Body', '').lower() == data.get('Body', '').lower():
                Debug.logger.debug(f"Matched construction {build.get('Body')} {build.get('State', None)} {build.get('Location', '')} Build: {build}")
                return build

            # A completed but as yet unknown build.
            if build.get('State', None) == BuildState.COMPLETE and build.get('MarketID', '') == '' and \
                data.get('Body', None) and build.get('Body', '').lower() == data.get('Body', '').lower and \
                build.get('Location') == data.get('Location', None):
                Debug.logger.debug(f"Matched completed on {build.get('Body')} {build.get('State', None)} {build.get('Location', '')} Build: {build}")
                return build

        return None


    @catch_exceptions
    def find_or_create_build(self, system:dict, data:dict) -> dict:
        ''' Find a build by marketid or name, or create it if it doesn't exist '''
        build:dict|None = self.find_build(system, data)
        if build != None:
            Debug.logger.debug(f"Build found")
            return build

        return self.add_build(system, data)


    @catch_exceptions
    def add_build(self, system, data:dict, silent:bool = False) -> dict:
        ''' Add a new build to a system '''

        # Yea this is terrible but it works for now.
        if isinstance(system, int): system = self.systems[system]

        Debug.logger.info(f"Adding build {data.get('Name')} {data}")

        if 'State' not in data: data['State'] = BuildState.PLANNED
        if 'Name' not in data: data['Name'] = ""
        if 'BuildID' not in data and 'MarketID' in data:
            data['BuildID'] = f"x{int(time.time())}" if data['State'] == BuildState.COMPLETE else f"&{int(time.time())}"

        # If we have a body name or id set the corresponding value.
        body:dict|None = self.get_body(system, data.get('BodyNum', data.get('Body', '')))
        if body != None:
            data['Body'] = self.body_name(system.get('StarSystem'), body.get('name', ''))
            data['BodyNum'] = body['bodyId']

        if data.get('Base Type', '') == '' and data.get('Layout', None) != None:
            bt:dict = self.get_base_type(data.get('Layout', ''))
            data['Base Type'] = bt.get('Type', '')

        system['Builds'].append(data)

        # Update RC if appropriate and we have enough data about the system.
        if silent == False and system.get('RCSync', False) == True and system.get('SystemAddress', None) != None and \
            data.get('Layout', None) != None and data.get('BodyNum', None) != None:
            RavenColonial(self).upsert_site(system, data)

        self.save('Build added')

        return data


    @catch_exceptions
    def remove_build(self, system, ind:int) -> None:
        ''' Remove a build from a system '''
        if isinstance(system, int): system = self.systems[system]

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

        if system.get('RCSync', False) == True:
            RavenColonial(self).remove_site(system, ind)

        # Remove build
        system['Builds'].pop(ind)
        self.save('Build removed')


    @catch_exceptions
    def set_base_type(self, system:dict, buildid:str|int, type:str) -> None:
        """ Set/update the type of a given base using type or layout """

        Debug.logger.debug(f"Seting base type for {buildid} {type}")

        data:dict = {'Base Type' : '', 'Layout' : '', 'Location': '' }
        if type != ' ':
            bt:dict = self.get_base_type(type)
            data = {'Base Type' : bt['Type'], 'Location': bt['Location'] }
            layouts:list = self.get_base_layouts(bt['Type'])
            if len(layouts) == 1: data['Layout'] = layouts[0]
            if type in layouts: data['Layout'] = type

        build:dict|None = system['Builds'][buildid] if isinstance(buildid, int) and buildid < len(system['Builds']) else self.find_build(system, {'BuildID' : buildid})
        if build == None:
            data['State'] = BuildState.PLANNED
            self.add_build(system, data)
            return

        self.modify_build(system, build.get('BuildID', ''), data)


    @catch_exceptions
    def modify_build(self, system, buildid:str, data:dict, silent:bool = False) -> None:
        ''' Modify a build in a system '''
        Debug.logger.debug(f"Modifying build {buildid} {data}")
        build:dict|None = None

        if isinstance(system, int): system = self.systems[system]
        if isinstance(buildid, int): build = system['Builds'][buildid]
        if build == None: build = self.find_build(system, {'BuildID' : buildid})
        if build == None:
            Debug.logger.error(f"modify_build called for non-existent build: {buildid}")
            return

        # If we have a body name or id set the corresponding value.
        body:dict|None = self.get_body(system, data.get('BodyNum', data.get('Body', 'Unknown')))
        if body != None:
            data['Body'] = self.body_name(system['StarSystem'], body.get('name', ''))
            data['BodyNum'] = body.get('bodyId', None)

        # If the base type isn't set, try to get it from the layout
        if data.get('Base Type', '') == '' and data.get('Layout', '') != '':
            bt:dict = self.get_base_type(data.get('Layout', ''))
            data['Base Type'] = bt.get('Type', '')

        changed:bool = False
        for k, v in data.items():
            if k not in self.build_keys: continue

            if k == 'Track' and build.get(k, False) != v:
                build[k] = v
                self.bgstally.ui.window_progress.update_display()

            if build.get(k, '') != v:
                Debug.logger.debug(f"Build {buildid} {k} {v}")
                build[k] = v.strip() if isinstance(v, str) else v
                changed = True

        # Send our updates back to RavenColonial if we're tracking this system and have the details required
        if silent == False and changed == True and \
            system.get('RCSync', False) == True and system.get('SystemAddress', None) != None and \
            build.get('Layout', None) != None and build.get('BodyNum', None) != None:
            RavenColonial(self).upsert_site(system, build)
            for p in self.progress:
                if p.get('ProjectID', None) != None and p.get('MarketID', None) == build.get('MarketID'):
                    RavenColonial(self).upsert_project(system, build, p)

        self.save('Build modified')


    @catch_exceptions
    def try_complete_build(self, market_id:int) -> bool:
        ''' If a build has been completed but isn't yet marked as such do so and clear the
            tracking, construction name and construction marketid '''
        [system, build] = self.find_build_any({'MarketID' : market_id})
        # Not found or already completed there's nothing to do.
        if build == None or build.get('State') == BuildState.COMPLETE:
            return False

        Debug.logger.debug(f"Completing build {self.current_system} {self.system_id} {market_id}")
        p:dict|None = self.find_progress(market_id)
        if p.get('ProjectID', None) != None:
            RavenColonial(self).complete_site(p.get('ProjectID', 0))

        # If we get here, the build is (newly) complete.
        # Since on completion the construction depot is removed/goes inactive and a new station is created
        # we need to clear some fields.
        self.modify_build(system, build.get('BuildID', ''), {
            'State': BuildState.COMPLETE,
            'Track': False,
            'MarketID': None,
            'Name': re.sub(r"(\w+ Construction Site:|\$EXT_PANEL_ColonisationShip;) ", "", build.get('Name', ''))
        })
        return True


    @catch_exceptions
    def get_commodity_list(self, base_type:str, order:CommodityOrder = CommodityOrder.ALPHA) -> list:
        ''' Return an ordered list of base commodity costs for a base type '''
        comms = self.base_costs.get(base_type, None)
        if comms == None: return []

        match order:
            case CommodityOrder.CATEGORY:
                # dict(sorted(dict_of_dicts.items(), key=lambda item: item[1][key_to_sort_by]))
                ordered = list(k for k, v in sorted(self.bgstally.ui.commodities.items(), key=lambda item: item[1]['Category']))
            case _:
                ordered = list(k for k, v in sorted(self.bgstally.ui.commodities.items(), key=lambda item: item[1]['Name']))

        return [f"${c_symbol}_name;" for c_symbol in ordered if f"${c_symbol}_name;" in comms.keys()]


    @catch_exceptions
    def get_commodity(self, symbol:str, which:str='name') -> str:
        ''' Return a localised commodity name or category '''
        if symbol in self.bgstally.ui.commodities:
            return self.bgstally.ui.commodities[symbol].get(which.title(), symbol)
        n:str = re.sub(r"\$(.*)_name;$", r"\1", symbol)
        if n in self.bgstally.ui.commodities:
            return self.bgstally.ui.commodities[n].get(which.title(), symbol)
        return 'Unknown'


    @catch_exceptions
    def _get_progress(self, builds:list[dict], type:str) -> list[dict]:
        ''' Internal function to get progress details '''
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


    def get_required(self, builds:list[dict]) -> list:
        ''' Return the commodities required for the builds listed '''
        return self._get_progress(builds, 'Required')


    def get_delivered(self, builds:list[dict]) -> list:
        ''' Return the commodities delivered for the builds listed '''
        return self._get_progress(builds, 'Delivered')


    @catch_exceptions
    def find_or_create_progress(self, id:int) -> dict:
        ''' Find or if necessary create progress for a given market '''
        p:dict|None = self.find_progress(id)
        if p != None:
            return p

        prog:dict = { 'MarketID': id }
        self.progress.append(prog)

        self.dirty = True
        return prog


    @catch_exceptions
    def find_progress(self, id:int|str) -> dict|None:
        ''' Find and return progress for a given market '''
        for p in self.progress:
            if p.get('MarketID', 0) == id or p.get('ProjectID', '') == id:
                return p

        return None


    @catch_exceptions
    def update_progress(self, id:int, data:dict, silent:bool = False) -> None:
        ''' Update a progress record '''
        progress:dict|None = self.find_progress(id)
        if progress == None:
            Debug.logger.debug(f"Progress not found {id}")
            return

        # Copy over changed/updated data
        for k, v in data.items():
            if k == 'ResourcesRequired': # Handle a ColonisationConstructionDepot event
                req:dict = {comm['Name'] : comm['RequiredAmount'] for comm in v}
                deliv:dict = {comm['Name'] : comm['ProvidedAmount'] for comm in v}
                if progress.get('Required', None) != req or progress.get('Delivered', None) != deliv:
                    progress['Required'] = req
                    progress['Delivered'] = deliv
                    self.dirty = True
                continue

            if k == 'Remaining': # Handle an RC project event
                deliv:dict = {f"${key}_name;" : progress['Required'][f"${key}_name;"] - val for key, val in v.items()}
                pd:dict = progress.get('Delivered', {})
                # Maybe unnecessary but we only take RC delivered numbers if they're ahead
                for comm, amt in deliv.items():
                    if amt > progress['Delivered'][comm]:
                        self.dirty = True
                        progress['Delivered'][comm] = amt
                continue

            if progress.get(k) != v and k in self.progress_keys:
                progress[k] = v
                self.dirty = True

        if self.dirty == False: return
        self.save('Progress update')

        if silent == True: return

        # If it's complete mark it as complete
        if data.get('ConstructionComplete', False) == True:
            self.try_complete_build(progress.get('MarketID', 0))
            return

        # RC Sync if appropriate
        [system, build] = self.find_build_any({'MarketID': progress.get('MarketID', 0)})
        if system != None and build != None and system.get('RCSync', False) == True:
            RavenColonial(self).upsert_project(system, build, progress)


    @catch_exceptions
    def _update_carrier(self) -> None:
        ''' Update the carrier cargo data. '''
        if self.bgstally.fleet_carrier.available() == False:
            return
        cargo:dict = {}

        for item in self.bgstally.fleet_carrier.cargo:
            n:str = item.get('commodity', '')
            n = f"${n.lower().replace(' ', '')}_name;"
            if n not in cargo:
                cargo[n] = 0
            cargo[n] += int(item['qty'])

        if cargo != self.carrier_cargo and self.cmdr != None:
            RavenColonial(self).update_carrier(self.bgstally.fleet_carrier.carrier_id, cargo)
            self.dirty = True

        self.carrier_cargo = cargo


    @catch_exceptions
    def _update_cargo(self, cargo:dict) -> None:
        ''' Update the cargo data. '''
        tmp:dict = {}
        for k, v in cargo.items():
            if v > 0:
                k:str = f"${k.lower()}_name;"
                tmp[k] = v
        self.cargo = tmp


    @catch_exceptions
    def _update_market(self, market_id:int|None = None) -> None:
        ''' Update market info from the market object or directly '''
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


    @catch_exceptions
    def _load(self) -> None:
        ''' Load state from file '''
        file:str = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        if path.exists(file):
            with open(file) as json_file:
                self._from_dict(json.load(json_file))


    @catch_exceptions
    def save(self, cause:str = 'Unknown') -> None:
        ''' Save state to file '''

        Debug.logger.debug(f"Saving: {cause}")
        file:str = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self._as_dict(), outfile, indent=4)

        self.dirty = False


    @catch_exceptions
    def _as_dict(self) -> dict:
        ''' Return a Dictionary representation of our data, suitable for serializing '''

        # System tab order
        def sort_order(item:dict) -> str:
            state:BuildState = BuildState.COMPLETE
            for b in item['Builds']:
                bs:BuildState = self.get_build_state(b)
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
        # We also clean up the system and build entires.
        systems:list = []
        progress:list = []
        markets:list = [0]
        for s in list(sorted(self.get_all_systems(), key=sort_order, reverse=True)):
            system:dict = {k: v for k, v in s.items() if k in self.system_keys}
            builds:list = []
            if len(system['Builds']) > 1:
                system['Builds'] = [system['Builds'][0]] + list(sorted(system['Builds'][1:], key=build_order))
            for i, b in enumerate(system['Builds']):
                if i > 0 and b.get('Base Type', '') == '' and b.get('Name', '') == '': continue
                build:dict = {k: v for k, v in b.items() if k in self.build_keys and v not in ['', "\u0001"]}
                builds.append(build)
                markets += [v for k, v in b.items() if k == 'MarketID' and v != None and v != '']
            system['Builds'] = builds
            systems.append(system)

        # Migrate the project progress and cleanup entries
        for p in self.progress:
            # Remove complete builds that we've recorded as complete
            if p.get('MarketID', 0) not in markets and p.get('ConstructionComplete', '') == True: continue
            site:dict = {k: v for k, v in p.items() if k in self.progress_keys}
            # Migrate old style progress
            if p.get('ResourcesRequired', None) != None:
                site['Required'] = {comm['Name'] : comm['RequiredAmount'] for comm in p.get('ResourcesRequired')}
                site['Delivered'] = {comm['Name'] : comm['ProvidedAmount'] for comm in p.get('ResourcesRequired')}
            progress.append(site)

        units:list = [v.value for v in self.bgstally.ui.window_progress.units]

        return {
            'Docked': self.docked,
            'SystemID': self.system_id,
            'CurrentSystem': self.current_system,
            'Body': self.body,
            'Station': self.station,
            'MarketID': self.market_id,
            'Progress': progress,
            'Systems': systems,
            'CargoCapacity': self.cargo_capacity,
            'ProgressView' : self.bgstally.ui.window_progress.view.value,
            'ProgressUnits': units,
            'ProgressColumns': self.bgstally.ui.window_progress.columns,
            'BuildIndex'   : self.bgstally.ui.window_progress.build_index
            }


    @catch_exceptions
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
        self.bgstally.ui.window_progress.units = [ProgressUnits(v) for v in dict.get('ProgressUnits', [])]
        self.bgstally.ui.window_progress.columns = dict.get('ProgressColumns')
        self.bgstally.ui.window_progress.build_index = dict.get('BuildIndex', 0)

        # Migration to ubiquitous buildids
        for system in self.systems:
            for build in system.get('Builds', []):
                if 'BuildID' not in build:
                    build['BuildID'] = f"x{int(time.time())}" if build.get('State') == BuildState.COMPLETE else f"&{int(time.time())}"
                    self.dirty = True
