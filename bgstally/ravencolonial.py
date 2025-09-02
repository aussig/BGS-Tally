import json
from json import JSONDecodeError
from urllib.parse import quote
from os import path
from os.path import join
import traceback
import re
import time
from functools import partial
import requests
from requests import Response
from bgstally.constants import RequestMethod, BuildState
from bgstally.requestmanager import BGSTallyRequest
from bgstally.debug import Debug
from bgstally.utils import _, get_by_path

RC_API = 'https://ravencolonial100-awcbdvabgze4c5cq.canadacentral-01.azurewebsites.net/api'
RC_COOLDOWN = 300

EDSM_BODIES = 'https://www.edsm.net/api-system-v1/bodies?systemName='
EDSM_STATIONS = 'https://www.edsm.net/api-system-v1/stations?systemName='
EDSM_SYSTEM = 'https://www.edsm.net/api-v1/system?showInformation=1&systemName='
EDSM_COOLDOWN = (3600 * 24)

SPANSH_API = 'https://spansh.co.uk/api'
SPANSH_COOLDOWN = (3600 * 24)

class RavenColonial:
    """
    Class to handle all the data syncing between the colonisation system and RavenColonial.com. It also handles retrieving
    system and body data from Spansh/EDSM as required

    It syncs systems and sites, projects, contributions and fleet carrier cargo.
    Many requests are queued to the request manager to avoid blocking EDMC but some are done synchronously where appropriate.
    """
    _instance = None

    # Singleton pattern
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self, colonisation) -> None:
        # Only initialize if it's the first time
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.colonisation:Colonisation = colonisation # type: ignore
        self.bgstally:BGSTally = colonisation.bgstally # type: ignore

        self.system_service:Spansh = Spansh(self)  # Site to use for system lookups
        self.body_service:EDSM = EDSM(self)    # Site to use for body lookups
        #self.station_service:EDSM = EDSM(self) # Site to use for station lookups
        self.station_service:Spansh = Spansh(self) # Site to use for station lookups

        self.headers:dict = {
            'User-Agent': f"BGSTally/{self.bgstally.version} (RavenColonial)",
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            "appName": 'BGSally',
            "appVersion": f"{self.bgstally.version}",
            "appDevelopment": 'True'
        }

        # map system parameters between colonisation & raven.
        self.sys_params:dict = {
            'id64': 'SystemAddress',
            'name': 'StarSystem',
            'architect': 'Architect',
            'rev': 'Rev'
        }

        # map site/build parameters between colonisation & raven.
        self.site_params:dict = {'id' : 'BuildID',
                                 'name' : 'Name',
                                 'bodyNum' : 'BodyNum',
                                 'buildType' : 'Layout',
                                 'status' : 'State',
                                 'buildId' : 'ProjectID',
                                 'architectName' : 'Architect'
                                 }
        # Project parameter mapping between colonisation & raven.
        self.project_params:dict = {
            'timestamp': 'Updated',
            'marketId': 'MarketID',
            'systemAddress': 'SystemAddress',
            'buildName': 'Name',
            'buildId': 'ProjectID',
            'commodities': 'Remaining',
            'buildType': 'Layout',
            'bodyNum': 'BodyNum',
            'architectName': 'Architect',
            'timeDue': 'Deadline',
            'bodyType': 'BodyType',
            'complete': 'ConstructionComplete'
            }

        # build state parameters between colonisation & raven.
        self.status_map:dict = {
            'plan': BuildState.PLANNED.value,
            'build': BuildState.PROGRESS.value,
            'complete': BuildState.COMPLETE.value
        }

        self._cache:dict = {} # Cache of responses and response times used to reduce API calls


    def load_system(self, id64:str|None = None, rev:str|None = None) -> None:
        """ Retrieve the rcdata data with the latest system data from RC when we start. """

        # Implement cooldown and revision tracking
        if self._cache.get(id64, None) == None: self._cache[id64] = {}

        if self._cache[id64].get('ts', 0) > int(time.time()) - RC_COOLDOWN:
            Debug.logger.info(f"Not refreshing {id64}, too soon {int(time.time()) - self._cache[id64].get('ts', 0)}")
            return

        self._cache[id64]['rev'] = rev
        self._cache[id64]['ts'] = int(time.time())

        # This just returns a commanders list of project (or system?) revisions.
        #url:str = f"{RC_API}/v2/system/revs"
        #response:Response = requests.get(url, headers=self.headers,timeout=5)
        #Debug.logger.info(f"Response for /revs {id64}: {response.status_code} {response}")
        #data:dict = response.json()

        url:str = f"{RC_API}/v2/system/{id64}"
        self.bgstally.request_manager.queue_request(url, RequestMethod.GET, callback=self._load_response)
        return


    def add_system(self, system_name:str) -> None:
        """ Add a system to RC. """

        url:str = f"{RC_API}/v2/system/{quote(system_name)}"
        self.headers["rcc-cmdr"] = self.colonisation.cmdr
        response:Response = requests.get(url, headers=self.headers,timeout=5)
        Debug.logger.info(f"Query system response for {system_name}: {response.status_code}")

        # Add a new system to RavenColonial
        if response.status_code == 404:
            url:str = f"{RC_API}/v2/system/{quote(system_name)}/import/"
            response:Response = requests.post(url, headers=self.headers, timeout=5)

            if response.status_code != 200:
                Debug.logger.error(f"Failed to import system {system_name}: {response.status_code}")
                return

        # Merge RC data with system data
        data:dict = response.json()
        self._merge_system_data(data)

        payload:dict = {'architect': self.colonisation.cmdr, 'update': [], 'delete':[]}

        url:str = f"{RC_API}/v2/system/{quote(system_name)}/sites"
        response:Response = requests.put(url, json=payload, headers=self.headers, timeout=5)
        if response.status_code != 200:
            Debug.logger.error(f"{url} {response} {response.content}")
        return


    def complete_site(self, project_id:str) -> None:
        """ Complete a site """
        try:
            url:str = f"{RC_API}/project/{project_id}/complete"

            response:Response = requests.post(url, headers=self.headers, timeout=5)
            if response.status_code not in [200, 202]:
                Debug.logger.error(f"{url} {response} {response.content}")
                return

            Debug.logger.info(f"RavenColonial project completed {project_id}")
            return

        except Exception as e:
            Debug.logger.info(f"Error completing site")
            Debug.logger.error(traceback.format_exc())


    def upsert_site(self, system:dict, data:dict) -> None:
        """ Modify a site (build) in RavenColonial """
        try:
            if self.colonisation.cmdr == None:
                Debug.logger.info(f"Cannot upsert site, no cmdr")
                return

            if data.get('Name')== 'T9M-33M': raise

            # Create an ID if necessary
            if data.get('BuildID', None) == None and data.get('MarketID', None) != None:
                data['BuildID'] = f"&{data['MarketID']}"

            if data.get('BuildID', None) == None and data.get('State', None) == BuildState.PLANNED:
                data['BuildID'] = f"x{int(time.time())}"

            update:dict = {}
            rev_map = {value: key for key, value in self.status_map.items()}
            for p, m in self.site_params.items():
                if data.get(m, None) == None:
                    continue
                rcval = data.get(m, '').strip().lower().replace(' ', '_') if isinstance(data.get(m, None), str) and 'name' not in p.lower() else data.get(m, None)
                if p == 'status' and data.get(m, None) != None: rcval = rev_map[data.get(m, '')]
                update[p] = rcval

            payload:dict = {'update': [update], 'delete':[]}

            url:str = f"{RC_API}/v2/system/{system.get('SystemAddress')}/sites"
            self.headers["rcc-cmdr"] = system.get('Architect')

            Debug.logger.info(f"RavenColonial upserting site:{payload}")

            response:Response = requests.put(url, json=payload, headers=self.headers, timeout=5)
            if response.status_code != 200:
                Debug.logger.error(f"{url} {response} {response.content}")

            # Refresh the system info
            self.load_system(system.get('SystemAddress', 0), system.get('Rev', 0))
            return

        except Exception as e:
            Debug.logger.info(f"Error upserting site")
            Debug.logger.error(traceback.format_exc())


    def remove_site(self, system:dict, ind:int) -> None:
        """ Remove a site from RavenColonial """
        try:
            if system.get('Architect') == None:
                Debug.logger.info("Cannot remove site no commander")
                return

            build:dict = system['Builds'][ind]

            if build.get('BuildID', None) == None:
                Debug.logger.warning("RavenColonial modify_site called for non-RC site")
                return

            payload:dict = {'update': [], 'delete':[build.get('BuildID')]}
            Debug.logger.info(f"RavenColonial removing site {payload}")
            url:str = f"{RC_API}/v2/system/{system.get('SystemAddress')}/sites"
            self.headers["rcc-cmdr"] = system.get('Architect')
            response:Response = requests.put(url, json=payload, headers=self.headers, timeout=5)
            if response.status_code != 200:
                Debug.logger.error(f"{url} {response} {response.content}")
            return

        except Exception as e:
            Debug.logger.info(f"Error recording remove_site response")
            Debug.logger.error(traceback.format_exc())


    def _merge_system_data(self, data:dict) -> None:
        """ Merge the data from RavenColonial into the system data """
        try:
            #Debug.logger.debug(f"Merging data: {json.dumps(data, indent=4)}")
            system:dict = self.colonisation.find_system({'SystemAddress' : data.get('id64', None),
                                                         'StarSystem': data.get('name', None)})
            if system == None:
                Debug.logger.info(f"Can't merge, system {data.get('name', None)} not found")
                return

            mod:dict = {}
            for k, v in self.sys_params.items():
                if k != 'rev' and data.get(k, '') != '' and \
                    data.get(k, None) != system.get(v, None):
                    mod[v] = data.get(k, None).strip() if isinstance(data.get(k, None), str) else data.get(k, None)

            if mod != {}:
                Debug.logger.debug(f"Changes found, modifyng system {mod}")
                self.colonisation.modify_system(system, mod)

            for site in data.get('sites', []):
                # A project not a site (this is how we find projectids if we're missing them
                if not re.match(r"^[&x]\d+$", site.get('id')):
                    if self.colonisation.find_progress(site.get('id')) != None: continue
                    build = self.colonisation.find_build(system, {'Name': site.get('name')})
                    if build != None and build.get('MarketID', None) != None: self.colonisation.update_progress(build.get('MarketID'), {'ProjectID' : site.get('id')}, True)
                    continue

                # A site
                build:dict = self.colonisation.find_build(system, {'MarketID': site.get('id', -1)[1:],
                                                                   'Name': site.get('name', -1),
                                                                   'BuildID' : site.get('id', -1)})
                # Avoid creating leftover construction sites
                if build == None and 'Construction Site' in site.get('name', ''):
                    if self.colonisation.find_build(system, {'Name': re.sub(r".* Construction Site: ", "", site.get('name'))}) != None:
                        continue

                if build == None: build = {}
                deets:dict = {}
                for p, m in self.site_params.items():
                    # Skip placeholder responses
                    if p == 'bodyNum' and site.get(p, -1) == -1: continue
                    #if p == 'buildType' and '?' in site.get(p, '?') : continue

                    #strip, initcap and replace spaces in strings except for id and buildid and name
                    rcval = site.get(p, '').strip().title().replace('_', ' ') if isinstance(site.get(p, None), str) and p not in ['id', 'buildId', 'name'] else site.get(p, None)
                    if p == 'status' and site[p] in self.status_map.keys(): rcval = self.status_map[site[p]]
                    if rcval != None and rcval != build.get(m, None):
                        deets[m] = rcval

                if deets != {}:
                    if build == {}:
                        Debug.logger.info(f"Adding build {system} {deets}")
                        self.colonisation.add_build(system, deets, True)
                    else:
                        Debug.logger.info(f"Updating build {system['Builds'].index(build)} {deets}")
                        self.colonisation.modify_build(system, build.get('BuildID', ''), deets, True)
            return

        except Exception as e:
            Debug.logger.info(f"Error recording _rc_system response")
            Debug.logger.error(traceback.format_exc())


    def _load_response(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        """ Process the results of querying RavenColonial for the system details """
        try:
            if success == False:
                Debug.logger.error(f"System load failed {response.content}")
                return

            data:dict = response.json()
            system:dict = self.colonisation.find_system({'SystemAddress': data.get('id64', None),
                                                         'StarSystem': data.get('name', None)})
            if system == None:
                Debug.logger.info(f"RavenColonial system {data.get('id64', None)} not found")
                return

            if self._cache[data['id64']].get('rev', -1) == data['rev']:
                Debug.logger.debug(f"System hasn't changed no update required")
                return

            self._cache[data['id64']]['rev'] = data['rev']
            self._merge_system_data(data)

            # Submit any missing sites to RC
            for b in system['Builds']:
                if b.get('Layout', None) == None or b.get('BodyNum', None) == None:
                    continue

                site:dict = {}
                for site in data.get('sites', {}):
                    if site.get('id', None) == b.get('BuildID', None):
                        break

                # Only add the site if we didn't match it.
                if site.get('id', None) != b.get('BuildID', None):
                    self.upsert_site(system, b)

            return

        except Exception as e:
            Debug.logger.info(f"Error recording _rc_system response")
            Debug.logger.error(traceback.format_exc())


    def _add_response(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        """ Add a system to RavenColonial """
        try:
            if success == False:
                Debug.logger.error(f"Request failed {response.content}")
                return

            data:dict = response.json()
            system:dict = self.colonisation.find_system({'StarSystem': data.get('name', None)})

            if system == None:
                Debug.logger.info(f"RavenColonial system {data.get('id64', None)} not found")
                return

            self.colonisation.modify_system(system, {
                'SystemAddress': data.get('id64', None),
                'StarSystem': data.get('name', None),
                'Name': data.get('name', None),
                'Architect': data.get('architect', None)
            })

            # Update the system's builds with the data from RC
            for build in system.get('Builds', []):
                site:dict = {}
                for site in data.get('sites', []):
                    if site.get('name', None) == build.get('name', None):
                        break

                deets:dict = {}
                for p, m in self.site_params.items():
                    if site.get(p, None) != None:
                        deets[m] = self.status_map[site[p]] if p == 'status' else site.get(p)
                if deets != {}:
                    self.colonisation.modify_build(system, build.get('BuildID', ''), deets, True)
                    self.colonisation.dirty = True

            self.colonisation.save('RC system data updated')
            return

        except Exception as e:
            Debug.logger.info(f"Error recording _rc_system response")
            Debug.logger.error(traceback.format_exc())


    def create_project(self, system:dict, build:dict, progress:dict) -> None:
        # Required: marketid, systemaddress, buildname, commodities (required)
        # Opt: colonisationConstructionDepot (event details), buildType, bodyNum, architectName, timeDue, isPrimaryPort, bodyType
        payload:dict = {}
        for k, v in self.project_params.items():
            rcval = None
            if progress.get(v, None) != None:
                rcval = progress.get(v, '').strip().lower().replace(' ', '_') if isinstance(progress.get(v, None), str) and 'name' not in k.lower() else progress.get(v, None)
            elif build.get(v, None) != None:
                rcval = build.get(v, '').strip().lower().replace(' ', '_') if isinstance(build.get(v, None), str) and 'name' not in k.lower() else build.get(v, None)
            elif system.get(v, None) != None:
                rcval = system.get(v, '').strip().lower().replace(' ', '_') if isinstance(system.get(v, None), str) and 'name' not in k.lower() else system.get(v, None)
            elif k == 'commodities' and  progress != {}:
                rcval = {re.sub(r"\$(.*)_name;", r"\1", k).lower() : v for k,v in progress.get('Required').items()}

            if rcval != None:
                payload[k] = rcval

        url:str = f"{RC_API}/project/"
        response:Response = requests.put(url, json=payload, headers=self.headers, timeout=5)
        if response.status_code == 409:
            Debug.logger.error(f"{url} already exists: {response.content}")
            return

        if response.status_code not in [200, 202]:
            Debug.logger.error(f"{url} {response} {response.content}")
            return

        # Set the project ID in the progress
        data:dict = response.json()
        self.colonisation.update_progress(progress.get('MarketID'), {'ProjectID': data.get('buildId')}, True)

        # Link the project to us.
        url:str = f"{RC_API}/project/{data.get('buildId')}/link/{self.colonisation.cmdr}"
        response:Response = requests.put(url, headers=self.headers, timeout=5)
        if response.status_code not in [200, 202]:
            Debug.logger.error(f"{url} {response} {response.content}")
            return

        return


    def upsert_project(self, system:dict, build:dict, progress:dict) -> None:
        """ Update build progress """
        # Required: buildId (though maybe not if you use )
        try:
            if progress.get('Updated', None) != None: del progress['Updated'] # Don't send this

            # Create project if we don't have an id.
            if progress.get('ProjectID', None) == None:
                self.create_project(system, build, progress)
                return

            # Update project
            payload:dict = {}
            for k, v in self.project_params.items():
                rcval = None
                if progress.get(v, None) != None:
                    rcval = progress.get(v, '').strip().lower().replace(' ', '_') if isinstance(progress.get(v, None), str) and 'name' not in k.lower() else progress.get(v, None)
                elif build.get(v, None) != None:
                    rcval = build.get(v, '').strip().lower().replace(' ', '_') if isinstance(build.get(v, None), str) and 'name' not in k.lower() else build.get(v, None)
                elif system.get(v, None) != None:
                    rcval = system.get(v, '').strip().lower().replace(' ', '_') if isinstance(system.get(v, None), str) and 'name' not in k.lower() else system.get(v, None)
                elif k == 'commodities' and progress != {}:
                    rcval = {re.sub(r"\$(.*)_name;", r"\1", k).lower() : v - progress['Delivered'].get(k) for k,v in progress.get('Required').items()}

                if rcval != None:
                    payload[k] = rcval

            if payload == self._cache.get(progress.get('ProjectID', ''), {}):return
            self._cache[progress.get('ProjectID', '')] = payload

            #Debug.logger.debug(f"RC: Submitting project update {system.get('StarSystem', None)} {payload}")
            url:str = f"{RC_API}/project/{progress.get('ProjectID')}"
            self.headers["rcc-cmdr"] = self.colonisation.cmdr
            self.bgstally.request_manager.queue_request(url, RequestMethod.PATCH, payload=payload, headers=self.headers, callback=self._project_callback)
            return

        except Exception as e:
            Debug.logger.info(f"Error upserting project")
            Debug.logger.error(traceback.format_exc())


    def _project_callback(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        """ Process the results of querying RavenColonial """
        data:dict = response.json()

        if success == True:
            self.colonisation.update_progress(data.get('buildId'), {'Updated': re.sub(r"\.\d+\+00:00$", "Z", str(data.get('timestamp')))}, True)
            return

        Debug.logger.warning(f"Project submission failed {success} {response.status_code} {response.content} {request}")


    def load_project(self, progress:dict) -> None:
        try:
            projectid:str|None = progress.get('ProjectID', None)
            if projectid == None: return

            url:str = f"{RC_API}/project/{projectid}/last"
            response:Response = requests.get(url, headers=self.headers,timeout=5)
            if response.status_code != 200:
                Debug.logger.error(f"Error for {url} {response} {response.content}")
                return

            if response.content == '0001-01-01T00:00:00+00:00':
                Debug.logger.error(f"Error with load project, doesn't exist")
                return

            if response.content != progress.get('Updated', ''):
                url = f"{RC_API}/project/{projectid}"
                self.bgstally.request_manager.queue_request(url, RequestMethod.GET, callback=self._load_project_response)

            return

        except Exception as e:
            Debug.logger.info(f"Error loading project")
            Debug.logger.error(traceback.format_exc())


    def _load_project_response(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        """ Process the results of querying RavenColonial for the project details """
        try:
            if success == False:
                Debug.logger.error(f"Project load failed {response}")
                return

            data:dict = response.json()
            self._cache[data.get('buildId')] = data.get('timestamp')
            update:dict = {}
            for k, v in self.project_params.items():
                if data.get(k, None) == None:
                    continue
                if k == 'timestamp':
                    update[v] = re.sub(r"\.\d+\+00:00$", "Z", str(data.get(k, None)))
                    continue
                update[v] = data.get(k, '') if isinstance(data.get(k, None), str) and 'name' not in k.lower() else data.get(k, None)

            if update != {}:
                self.colonisation.update_progress(data.get('marketId'), update, True)
            return

        except Exception as e:
            Debug.logger.info(f"Error loading project")
            Debug.logger.error(traceback.format_exc())


    def record_contribution(self, project_id:int, contributions:list) -> None:
        """ Record colonisation contributions made """
        try:
            payload:dict = {}
            for c in contributions:
                match = re.match(r'^\$(.*)_name;', c.get('Name', '').lower())
                comm:str = match.group(0)
                qty:int = c.get('Amount', 0)
                payload[comm] = qty

            # Which of the following to use?
            url:str = f"{RC_API}/project/{project_id}/contribute/{self.colonisation.cmdr}"
            response:Response = requests.post(url, json=payload, headers=self.headers, timeout=5)
            if response.status_code not in [200, 202]:
                Debug.logger.error(f"{url} {response} {response.content}")
                return

            Debug.logger.debug(f"Project contribution accepted")
            return

        except Exception as e:
            Debug.logger.info(f"Error recording contribution")
            Debug.logger.error(traceback.format_exc())


    def update_carrier(self, marketid:int, cargo:dict) -> None:
        """ Update the cargo of a fleet carrier """
        try:
            if self.colonisation.cmdr == None:
                Debug.logger.info("Cannot update carrier no cmdr")
                return

            all:dict = self.colonisation.base_costs.get('All')
            payload:dict = {re.sub(r"\$(.*)_name;", r"\1", comm).lower() : cargo.get(comm, 0) for comm in all.keys()}
            Debug.logger.debug(f"Carrier cargo: {marketid} {payload}")
            url:str = f"{RC_API}/fc/{marketid}/cargo"
            self.headers["rcc-cmdr"] = self.colonisation.cmdr
            self.bgstally.request_manager.queue_request(url, RequestMethod.POST, payload=payload, headers=self.headers, callback=self._carrier_callback)
            return

        except Exception as e:
            Debug.logger.info(f"Error updating carrier")
            Debug.logger.error(traceback.format_exc())


    def _carrier_callback(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        """ Process the results of querying RavenColonial """
        data:dict = response.json()
        if success == False or response.status_code != 200:
            Debug.logger.warning(f"Error updating carrier {response} {response.content}")
            return
        Debug.logger.debug(f"Carrier updated: {response}")
        return


    def import_stations(self, system_name:str) -> None:
        """ Retrieve the stations in a system """
        return self.station_service.import_stations(system_name)
    def import_system(self, system_name:str) -> None:
        """ Retrieve the details of a system """
        return self.system_service.import_system(system_name)
    def import_bodies(self, system_name:str) -> None:
        """ Retrieve the bodies in a system """
        return self.body_service.import_bodies(system_name)


class EDSM:
    """
    Class to retrieve system, body and station data from EDSM.

    It's called from the RavenColonial class so that we can switch between EDSM and Spansh.
    """
    _instance = None

    # Singleton pattern
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, rc):
        # Only initialize if it's the first time
        if hasattr(self, '_initialized'): return
        self.rc:RavenColonial = rc
        self._initialized = True
        # Details to retrieve for bodies from EDSM
        self.body_details:list = ['name', 'bodyId', 'type', 'subType', 'terraformingState', 'isLandable', 'rotationalPeriodTidallyLocked', 'atmosphereType', 'volcanismType', 'rings', 'reserveLevel', 'distanceToArrival']


    def import_stations(self, system_name:str) -> None:
        """ Retrieve the stations in a system """
        if system_name == None or system_name == '':
            Debug.logger.info("no system name")
            return

        # Check when we last updated this system
        systems:list = self.rc.colonisation.get_all_systems()
        system:dict|None = self.rc.colonisation.find_system({'StarSystem': system_name})
        if system == None:
            Debug.logger.info(f"unknown system {system_name}")
            return

        if system.get('Updated', 0) > int(time.time()) - EDSM_COOLDOWN:
            Debug.logger.info(f"Not refreshing stations for {system_name}, too soon {int(time.time()) - system.get('Updated', 0)}")
            return

        url:str = f"{EDSM_STATIONS}{quote(system_name)}"
        self.rc.bgstally.request_manager.queue_request(url, RequestMethod.GET, callback=self._stations)
        return

    def _stations(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        ''' Process the results of querying ESDM for the stations in a system '''
        Debug.logger.info(f" discovery response received: {success}")
        try:
            data:dict = response.json()
            if data.get('name', None) == None:
                Debug.logger.warning(f"stations response did not contain a name, ignoring")
                return
            system:dict|None = self.rc.colonisation.find_system({'StarSystem': data.get('name')})
            if system == None:
                Debug.logger.warning(f"stations didn't find system {data.get('name')}")
                return

            stations:list = list(k for k in sorted(data.get('stations', []), key=lambda item: item['marketId']))
            for base in stations:
                # Ignore these
                if base.get('type', '') in ['Fleet Carrier'] or 'ColonisationShip' in base.get('name', ''):
                    continue

                name:str = base.get('name', '')
                type:str = base.get('type', 'Unknown')
                state:BuildState = BuildState.COMPLETE
                if name == '$EXT_PANEL_ColonisationShip:#index=1;':
                    if len(stations) > 1: # This hangs around but only matters if it's the only station in the system.
                        continue
                    type = 'Orbital'
                    name = ''
                    state = BuildState.PROGRESS

                if self.rc.colonisation.find_build(system, {'MarketID': base.get('marketId'), 'Name': name}) != None:
                    Debug.logger.debug(f"Build {name} already exists in system {data.get('name')}, skipping")
                    continue

                                # Avoid creating leftover construction sites
                if 'Construction Site' in name:
                    if self.rc.colonisation.find_build(system, {'Name': re.sub(r".* Construction Site: ", "", name)}) != None:
                        Debug.logger.debug(f"Skipping build {name}")
                        continue

                if 'Construction Site' in name:
                    build = self.rc.colonisation.find_build(system, {'MarketID': base.get('marketId'), 'Name': name})
                    state = BuildState.PROGRESS

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
                self.rc.colonisation.add_build(system, build)
                Debug.logger.info(f"Added station {build} to system {data.get('name')}")

            self.rc.bgstally.ui.window_colonisation.update_display()
            self.rc.colonisation.dirty = True
            self.rc.colonisation.save('stations updated')

        except Exception as e:
            Debug.logger.info(f"Error recording stations")
            Debug.logger.error(traceback.format_exc())


    def import_system(self, system_name:str) -> None:
        """ Retrieve the details of a system """
        if system_name == None or system_name == '':
            Debug.logger.info("no system name")
            return

        # Check when we last updated this system
        system:dict|None = self.rc.colonisation.find_system({'StarSystem': system_name})
        if system == None:
            Debug.logger.info(f"unknown system {system_name}")
            return

        if system.get('EDSMUpdated', 0) > int(time.time()) - EDSM_COOLDOWN:
            Debug.logger.info(f"Not refreshing {system_name}, too soon")
            return

        url:str = f"{EDSM_SYSTEM}{quote(system_name)}"
        self.rc.bgstally.request_manager.queue_request(url, RequestMethod.GET, callback=self._system)
        return


    def _system(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        ''' Process the results of querying ESDM for the system details '''
        try:
            data:dict = response.json()
            if data.get('name', None) == None:
                Debug.logger.warning(f"system didn't contain a name, ignoring")
                return
            system:dict = self.rc.colonisation.find_system({'StarSystem' : data.get('name')})
            if system == None:
                Debug.logger.warning(f"system didn't find system {data.get('name')}")
                return

            system['Population'] = get_by_path(data, ['information', 'population'], None)
            system['Economy'] = get_by_path(data, ['information', 'economy'], None)
            if get_by_path(data, ['information', 'secondEconomy'], 'None') != 'None':
                system['Economy'] += "/" + get_by_path(data, ['information', 'secondEconomy'])
            system['Security'] = get_by_path(data, ['information', 'security'], None)
            system['EDSMUpdated'] = int(time.time())

            self.rc.colonisation.dirty = True
            self.rc.colonisation.save('System updated')

        except Exception as e:
            Debug.logger.info(f"Error recording response")
            Debug.logger.error(traceback.format_exc())


    def import_bodies(self, system_name:str) -> None:
        """ Retrieve the bodies in a system """
        if system_name == None or system_name == '':
            Debug.logger.info("no system name")
            return

        # Check when we last updated this system
        system:dict|None = self.rc.colonisation.find_system({'StarSystem': system_name})
        if system == None:
            Debug.logger.info(f"unknown system {system_name}")
            return

        if system.get('Bodies', None) != None:
            Debug.logger.info(f"Already have body info for {system_name}")
            return

        url:str = f"{EDSM_BODIES}{quote(system_name)}"
        # We're going to do this synchronously since we need the data before we can proceed and it's a one-time call.
        response:Response = requests.get(url, headers=self.rc.headers, timeout=5)
        if response.status_code == 200:
            self._bodies(True, response)

        #self.rc.bgstally.request_manager.queue_request(url, RequestMethod.GET, callback=self._bodies)
        return


    def _bodies(self, success:bool, response:Response, request:BGSTallyRequest|None = None) -> None:
        ''' Process the results of querying ESDM for the bodies in a system '''
        Debug.logger.info(f"bodies response received: {success}")
        try:
            data:dict = response.json()
            if data.get('name', None) == None:
                Debug.logger.warning(f"bodies didn't contain a name, ignoring")
                return
            system:dict = self.rc.colonisation.find_system({'StarSystem' : data.get('name')})
            if system == None:
                Debug.logger.warning(f"bodies didn't find system {data.get('name')}")
                return

            # Only record the body details that we need since returns an enormous amount of data.
            system['Bodies'] = []
            for b in data.get('bodies', []):
                v:dict = {}
                for k in self.body_details:
                    if b.get(k, None): v[k] = b.get(k)
                if b.get('parents', None) != None:
                    v['parents'] = len(b.get('parents', []))
                system['Bodies'].append(v)
            self.rc.colonisation.dirty = True
            self.rc.colonisation.save('Bodies updated')

        except Exception as e:
            Debug.logger.info(f"Error recording bodies")
            Debug.logger.error(traceback.format_exc())


class Spansh:
    """
    Class to retrieve system, body and station data from Spansh.

    It's called from the RavenColonial class so that we can switch between EDSM and Spansh
    """
    _instance = None

    # Singleton pattern
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, rc):
        # Only initialize if it's the first time
        if not hasattr(self, '_initialized'):
            self.rc:RavenColonial = rc
            self.system_cache:dict = {} # Spansh has a single endpoint for all system data so cache it here rather than requerying.
            self._initialized = True

    def import_stations(self, system_name:str) -> None:
        return self._get_details(system_name, 'stations')

    def import_system(self, system_name:str) -> None:
        return self._get_details(system_name, 'system')

    def import_bodies(self, system_name:str) -> None:
        return self._get_details(system_name, 'bodies')

    def _get_by_name(self, system_name:str) -> dict|None:
        """ Retrieve the system address from Spansh """
        try:

            system:dict|None = self.rc.colonisation.find_system({'StarSystem': system_name})
            if system == None:
                Debug.logger.info(f"unknown system {system_name}")
                return

            system_address:int|None = system.get('SystemAddress', None)
            if system_address != None:
                Debug.logger.info(f"System {system_name} has address {system_address} in local data")
                return system_address

            url:str = f"{SPANSH_API}/search?q={quote(system_name)}"
            response:Response = requests.get(url, headers=self.rc.headers, timeout=5)
            if response.status_code != 200:
                Debug.logger.error(f"Query system response for {system_name}: {response.status_code}")
                return None
            data:dict = response.json()

            return get_by_path(data.get('results',[])[0], ['record'], None)

        except Exception as e:
            Debug.logger.info(f"Error retrieving system by name")
            Debug.logger.error(traceback.format_exc())
            return None


    def _get_details(self, system_name:str, which:str) -> None:
        """ Retrieve a system's details """
        if system_name == None or system_name == '':
            Debug.logger.info("No system name given")
            return

        if which == 'stations':
            raise NameError('Querying stations')

        # Check when we last updated this system
        system:dict|None = self.rc.colonisation.find_system({'StarSystem': system_name})
        if system == None:
            Debug.logger.info(f"unknown system {system_name}")
            return

        # In cache? Then use it.
        if self.system_cache.get(system_name, None) != None and system.get('SpanshUpdated', 0) < int(time.time()) - SPANSH_COOLDOWN:
            match which:
                case 'bodies': return self._update_bodies(system, self.system_cache[system_name])
                case 'stations': return self._update_stations(system, self.system_cache[system_name])
                case 'system': return self._update_system(system, self.system_cache[system_name])

        # Too soon? Don't re-query
        if system.get('SpanshUpdated', 0) > int(time.time()) - SPANSH_COOLDOWN:
            return

        # Do it the efficient way since we have the address
        if system.get('SystemAddress', None) != None:
            url:str = f"{SPANSH_API}/system/{system.get('SystemAddress', None)}"
            self.rc.bgstally.request_manager.queue_request(url, RequestMethod.GET, callback=partial(self._callback, system, which))
            return

        url:str = f"{SPANSH_API}/search?q={quote(system_name)}"
        response:Response = requests.get(url, headers=self.rc.headers, timeout=5)
        self.rc.bgstally.request_manager.queue_request(url, RequestMethod.GET, callback=partial(self._callback, system, which))
        return


    def _callback(self, system:dict, which: str, success:bool, response:Response, request:BGSTallyRequest) -> None:
        ''' Process the results of querying ESDM for the system details '''
        try:
            if success == False:
                Debug.logger.error(f"system load failed {response.content}")
                return

            data:dict = response.json()
            if isinstance(data.get('results', None), list):
                for d in data.get('results', []):
                    if d.get('type', None) == 'system':
                        data = d
                        break

            if data.get('record', None) == None:
                Debug.logger.error("failed to get system record")
                return

            data = data.get('record', {})

            if data.get('name', None) == None:
                Debug.logger.warning(f"system didn't contain a name, ignoring {data}")
                return

            self.system_cache[data.get('id64', None)] = data
            match which:
                case 'bodies': return self._update_bodies(system, data)
                case 'stations': return self._update_stations(system, data)
                case 'system': return self._update_system(system, data)

        except Exception as e:
            Debug.logger.info(f"Error recording response")
            Debug.logger.error(traceback.format_exc())


    def _update_system(self, system:dict, data:dict) -> None:
        """ Update the system details"""
        try:
            update:dict = {}
            update['Population'] = data.get('population', None)
            update['Economy'] = data.get('primary_economy', None)
            if data.get('secondary_economy', 'None') != None:
                update['Economy'] += "/" + data.get('secondary_economy', '')
            update['Security'] = data.get('security', None)
            update['SystemAddress'] = data.get('id64', None)
            update['SpanshUpdated'] = int(time.time())

            self.rc.colonisation.modify_system(system, update)
            return
        except Exception as e:
            Debug.logger.info(f"Error recording response")
            Debug.logger.error(traceback.format_exc())


    def _update_stations(self, system:dict, data:dict) -> None:
        ''' Process the results of querying for the stations in a system '''
        try:
            if data.get('stations', 'None') == 'None':
                Debug.logger.debug(f"No stations")
                return

            Debug.logger.debug(f"Updating stations in {system.get('StarSystem')}")
            stations:list = list(k for k in sorted(data.get('stations', []), key=lambda item: item['market_id']))
            for base in stations:
                # Ignore these
                if base.get('type', '') in ['Drake-Class Carrier'] or \
                    '$EXT_PANEL_ColonisationShip;' in base.get('name', '') or \
                        ('ColonisationShip' in base.get('name', '') and len(stations) > 1):
                    continue

                name:str = base.get('name', '')
                market_id:int = base.get('market_id', 0)
                state:BuildState = BuildState.PROGRESS if 'Construction Site' in name else BuildState.COMPLETE

                if self.rc.colonisation.find_build(system, {'MarketID': market_id, 'Name': name}) != None:
                    Debug.logger.debug(f"Build {name} already exists in system {data.get('name')}, skipping")
                    continue

                # Look for a completed base with the same name since depots sometimes hang around.
                if 'Construction Site' in base.get('name', '') and \
                    self.rc.colonisation.find_build(system, {'Name': re.sub(r".* Construction Site: ", "", base.get('name'))}) != None:
                        Debug.logger.debug(f"Skipping construction site {base.get('name')}")
                        continue

                build:dict = {
                    'Base Type': base.get('type'),
                    'StationEconomy': base.get('economy'),
                    'State': state,
                    'Name': name,
                    'MarketID': market_id
                    }
                Debug.logger.info(f"Adding station base.get('name', '') to system {data.get('name')} {build}")
                self.rc.colonisation.add_build(system, build)


        except Exception as e:
            Debug.logger.info(f"Error recording stations")
            Debug.logger.error(traceback.format_exc())


    def _update_bodies(self, system:dict, data:dict) -> None:
        ''' Process the results of querying Spansh for the bodies in a system '''
        try:
            if data.get('name', None) == None:
                Debug.logger.warning(f"bodies didn't contain a name, ignoring")
                return

            # Only record the body details that we need since returns an enormous amount of data.
            bodies:list = []
            for b in data.get('bodies', []):
                v:dict = {}
                for k in ['name', 'bodyId', 'type', 'subType', 'terraformingState', 'isLandable', 'rotationalPeriodTidallyLocked', 'atmosphereType', 'volcanismType', 'rings', 'reserveLevel', 'distanceToArrival']:
                    if b.get(k, None): v[k] = b.get(k)
                if b.get('parents', None) != None:
                    v['parents'] = len(b.get('parents', []))
                bodies.append(v)

            if bodies != []:
                self.rc.colonisation.modify_system(system, {'Bodies': bodies})

        except Exception as e:
            Debug.logger.info(f"Error recording bodies")
            Debug.logger.error(traceback.format_exc())
