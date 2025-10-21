from urllib.parse import quote
import re
import time
from functools import partial
import requests
from requests import Response
from bgstally.constants import RequestMethod, BuildState
from bgstally.requestmanager import BGSTallyRequest
from bgstally.debug import Debug
from bgstally.utils import _, get_by_path, catch_exceptions

RC_API = 'https://ravencolonial100-awcbdvabgze4c5cq.canadacentral-01.azurewebsites.net/api'
RC_COOLDOWN = 30

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
        if hasattr(self, '_initialized'): return

        self.colonisation:Colonisation = colonisation # type: ignore
        if not hasattr(self.colonisation, 'bgstally'):
            return
        self.bgstally:BGSTally = colonisation.bgstally # type: ignore

        # map system parameters between colonisation & raven.
        self.sys_params:dict = {
            'id64': 'SystemAddress',
            'name': 'StarSystem',
            'architect': 'Architect',
            'rev': 'Rev',
            'slots': 'BuildSlots'
        }
        # map site/build parameters between colonisation & raven.
        self.site_params:dict = {'id' : 'BuildID',
                                 'name' : 'Name',
                                 'bodyNum' : 'BodyNum',
                                 'buildType' : 'Layout',
                                 'status' : 'State',
                                 'buildId' : 'ProjectID',
                                 'marketId' : 'MarketID',
                                 'architectName' : 'Architect'
                                 }
        # Project parameter mapping between colonisation & raven.
        self.project_params:dict = {
            'timestamp': 'Updated',
            'marketId': 'MarketID',
            'systemAddress': 'SystemAddress',
            'buildName': 'Name',
            'buildId': 'ProjectID',
            'systemSiteId': 'BuildID',
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

        self.base_headers:dict = {
            'User-Agent': f"BGSTally/{self.bgstally.version} (RavenColonial)",
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            "appName": 'BGSally',
            "appVersion": f"{self.bgstally.version}",
            "appDevelopment": 'True'
        }

        self._cache:dict = {} # Cache of responses and response times used to reduce API calls
        self._initialized = True


    def _headers(self) -> dict:
        """ Return the headers to use for RavenColonial API calls """
        headers:dict = self.base_headers
        if self.colonisation.cmdr != None: headers["rcc-cmdr"] = self.colonisation.cmdr
        if self.bgstally.state.ColonisationRCAPIKey.get() != None: headers["rcc-key"] = self.bgstally.state.ColonisationRCAPIKey.get()
        return headers


    @catch_exceptions
    def load_system(self, id64:str|None = None, rev:str|None = None, sync:bool = False) -> None:
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
        if sync == True:  # For requested refreshes only
            response:Response = requests.get(url, headers=self._headers(), timeout=5)
            self._load_callback(response.status_code == 200, response)
            return

        self.bgstally.request_manager.queue_request(url, RequestMethod.GET, headers=self._headers(), callback=self._load_callback)


    @catch_exceptions
    def add_system(self, system_name:str) -> None:
        """ Add a system to RC. """

        # Query the system to see if it exists
        url:str = f"{RC_API}/v2/system/{quote(system_name)}"
        response:Response = requests.get(url, headers=self._headers(), timeout=5)

        # Add a new system to RavenColonial
        if response.status_code == 404:
            url:str = f"{RC_API}/v2/system/{quote(system_name)}/import/"
            response:Response = requests.post(url, headers=self._headers(), timeout=5)

            if response.status_code != 200:
                Debug.logger.error(f"Failed to import system {system_name}: {response.status_code}")
                return

            # Add Builds
            system:dict = self.colonisation.find_system({'StarSystem': system_name})
            for b in system.get('Builds', []):
                self.upsert_site(system, b)

        # Merge RC data (either from the original get or from the import) with system data
        data:dict = response.json()
        self._merge_system_data(data)

        if data.get('architect', None) not in [None, self.colonisation.cmdr]:
            Debug.logger.info(f"Not architect, not updating system")
            return

        payload:dict = {'architect': self.colonisation.cmdr, 'update': [], 'delete':[]}

        url:str = f"{RC_API}/v2/system/{quote(system_name)}/sites"
        response:Response = requests.put(url, json=payload, headers=self._headers(), timeout=5)
        if response.status_code != 200:
            Debug.logger.error(f"{url} {response} {response.content}")

        Debug.logger.info(f"RavenColonial system added {system_name}")


    @catch_exceptions
    def complete_project(self, project_id:str) -> None:
        """ Complete a site """
        url:str = f"{RC_API}/project/{project_id}/complete"

        response:Response = requests.post(url, headers=self._headers(), timeout=5)
        if response.status_code not in [200, 202]:
            Debug.logger.error(f"{url} {response} {response.content}")
            return

        Debug.logger.info(f"RavenColonial project completed {project_id}")


    @catch_exceptions
    def delete_project(self, project_id:str) -> None:
        """ Delete a project """
        url:str = f"{RC_API}/project/{project_id}"

        response:Response = requests.delete(url, headers=self._headers(), timeout=5)
        if response.status_code not in [200, 202]:
            Debug.logger.error(f"{url} {response} {response.content}")
            return

        Debug.logger.info(f"RavenColonial project deleted {project_id}")


    @catch_exceptions
    def upsert_site(self, system:dict, data:dict) -> None:
        """ Modify a site (build) in RavenColonial """

        if self.colonisation.cmdr == None:
            Debug.logger.info(f"Cannot upsert site, no cmdr")
            return
        if system.get('Architect', '') != self.colonisation.cmdr:
            Debug.logger.info(f"Not architect, not updating")
            return

        # Create an ID if necessary
        if data.get('BuildID', None) == None:
            data['BuildID'] = self.colonisation._generate_buildid(data.get('MarketID', None))

        # Add a name since RC requires one at creation but not later
        if data.get('Name', None) == None:
            data['Name'] = ' '

        update:dict = {}
        rev_map:dict = {value: key for key, value in self.status_map.items()}
        for p, m in self.site_params.items():
            if data.get(m, None) == None:
                continue
            rcval = data.get(m, '').strip().lower().replace(' ', '_') if isinstance(data.get(m, None), str) and 'name' not in p.lower() else data.get(m, None)
            if p == 'status' and data.get(m, None) != None: rcval = rev_map[data.get(m, '')]
            update[p] = rcval

        payload:dict = {'update': [update], 'delete':[]}

        url:str = f"{RC_API}/v2/system/{system.get('SystemAddress')}/sites"
        response:Response = requests.put(url, json=payload, headers=self._headers(), timeout=5)
        if response.status_code != 200:
            Debug.logger.error(f"{url} {response} {response.content}")

        # Refresh the system info
        self.load_system(system.get('SystemAddress', 0), system.get('Rev', 0))
        Debug.logger.debug(f"RavenColonial site upserted {data.get('Name', '')} {update}")


    @catch_exceptions
    def remove_site(self, system:dict, ind:int) -> None:
        """ Remove a site from RavenColonial """
        if system.get('Architect', '') != self.colonisation.cmdr:
            Debug.logger.info(f"Not architect, not updating")
            return

        build:dict = system['Builds'][ind]

        if build.get('BuildID', None) == None:
            Debug.logger.warning("RavenColonial modify_site called for non-RC site")
            return

        payload:dict = {'update': [], 'delete':[build.get('BuildID')]}
        url:str = f"{RC_API}/v2/system/{system.get('SystemAddress')}/sites"
        response:Response = requests.put(url, json=payload, headers=self._headers(), timeout=5)
        if response.status_code != 200:
            Debug.logger.error(f"{url} {self._headers()} {response} {response.content}")

        Debug.logger.info(f"RavenColonial site removed {build.get('Name', '')}")


    def _merge_system_data(self, data:dict) -> None:
        """ Merge the data from RavenColonial into the system data """

        system:dict = self.colonisation.find_system({'SystemAddress' : data.get('id64', None),
                                                     'StarSystem': data.get('name', None)})
        if system == None:
            Debug.logger.info(f"Can't merge, system {data.get('name', None)} not found")
            return

        mod:dict = {}
        for k, v in self.sys_params.items():
            if k != 'rev' and data.get(k, None) != None and data.get(k, None) != system.get(v, None):
                mod[v] = data.get(k, None).strip() if isinstance(data.get(k, None), str) else data.get(k, None)

        if get_by_path(data, ['pop', 'pop'], 0) > system.get('Population', 0):
            mod['Population'] = get_by_path(data, ['pop', 'pop'], 0)

        if mod != {}:
            Debug.logger.debug(f"Changes found, modifyng system {mod}")
            self.colonisation.modify_system(system, mod)

        tmp:list = system.get('Builds', []).copy()
        for site in data.get('sites', []):
            # A site whose id has become the project id (this is how we find projectids if we're missing them)
            if not re.match(r"^[&x]\d+$", site.get('id', '')) and self.colonisation.find_progress(site.get('id')) != None:
                build = self.colonisation.find_build(system, {'Name': site.get('name')})
                if build != None and build.get('MarketID', None) != None:
                    self.colonisation.update_progress(build.get('MarketID'), {'ProjectID' : site.get('id')}, True)
            else:
                build = self.colonisation.find_build(system, {'BuildID' : site.get('id', -1), 'Name': site.get('name', -1), 'BodyNum': site.get('bodyNum', -1)})

            if build != None:
                for i, b in enumerate(tmp):
                    if b.get('BuildID', None) == build.get('BuildID', None):
                        tmp.remove(b)
                        break

            # Avoid creating leftover construction sites
            if build == None and 'Construction Site' in site.get('name', ''):
                if self.colonisation.find_build(system, {'Name': re.sub(r".* Construction Site: ", "", site.get('name'))}) != None:
                    continue

            self._sync_build(system, build if build != None else {}, site)

        # Remove any planned builds that are no longer in RC, leave in progress or completed alone
        for b in tmp:
            if b.get('State', '') != BuildState.PLANNED: continue
            self.colonisation.remove_build(system, b.get('BuildID', ''), True)

        self._reorder_builds(system, data.get('sites', []))


    def _sync_build(self, system:dict, build:dict, site:dict) -> None:
        """ Update our records with the latest RavenColonial build details """

        deets:dict = {}
        for p, m in self.site_params.items():
            # Skip placeholder responses
            if p == 'bodyNum' and site.get(p, -1) == -1: continue

            # strip, initcap and replace spaces in strings except for id and buildid, name and architectName
            rcval = site.get(p, '').strip().title().replace('_', ' ') if isinstance(site.get(p, None), str) and p not in ['id', 'buildId', 'name', 'architectName'] else site.get(p, None)
            if p == 'status' and site[p] in self.status_map.keys(): rcval = self.status_map[site[p]]
            if rcval != None and rcval != build.get(m, None):
                deets[m] = rcval

        if deets == {}:
            return

        if build == {}:
            self.colonisation.add_build(system, deets, True)
            return

        self.colonisation.modify_build(system, build.get('BuildID', ''), deets, True)


    def _reorder_builds(self, system:dict, sites:list) -> None:
        """ Reorder the builds in the system to match the order from RavenColonial """
        new_order:list = []
        for s in sites:
            build:dict|None = self.colonisation.find_build(system, {'BuildID' : s.get('id', -1), 'Name': s.get('name', -1), 'BodyNum': s.get('bodyNum', -1)})
            if build != None:
                new_order.append(build)

        if new_order == [] or new_order == system.get('Builds', []):
            return

        for build in system.get('Builds', []):
            if build not in new_order:
                new_order.append(build)

        Debug.logger.debug(f"New build order: {[k.get('Name', '') for k in new_order]} old: {[k.get('Name', '') for k in system.get('Builds', [])]}")
        self.colonisation.modify_system(system, {'Builds': new_order})


    @catch_exceptions
    def _load_callback(self, success:bool, response:Response, request:BGSTallyRequest|None = None) -> None:
        """ Process the results of querying RavenColonial for the system details """

        if success == False:
            Debug.logger.error(f"System load failed {response.content}")
            return

        data:dict = response.json()
        system:dict = self.colonisation.find_system({'SystemAddress': data.get('id64', None),
                                                        'StarSystem': data.get('name', None)})
        if system == None:
            Debug.logger.info(f"System {data.get('id64', None)} not found")
            return

        if self._cache[data['id64']].get('rev', -1) == data['rev']:
            Debug.logger.debug(f"System hasn't changed no update required")
            return

        self._cache[data['id64']]['rev'] = data['rev']
        self._merge_system_data(data)


    @catch_exceptions
    def create_project(self, system:dict, build:dict, progress:dict) -> None:
        """ Create a new project in RavenColonial """
        payload:dict = {}
        for k, v in self.project_params.items():
            rcval:dict|None = None

            if progress.get(v, None) != None:
                rcval = progress.get(v, '').strip().lower().replace(' ', '_') if isinstance(progress.get(v, None), str) and 'name' not in k.lower() else progress.get(v, None)
            elif build.get(v, None) != None:
                rcval = build.get(v, '').strip().lower().replace(' ', '_') if isinstance(build.get(v, None), str) and 'name' not in k.lower() else build.get(v, None)
            elif system.get(v, None) != None:
                rcval = system.get(v, '').strip().lower().replace(' ', '_') if isinstance(system.get(v, None), str) and 'name' not in k.lower() else system.get(v, None)
            elif k == 'commodities' and  progress != {}:
                rcval = {re.sub(r"\$(.*)_name;", r"\1", k).lower() : v for k,v in progress.get('Required').items()}

            if rcval != None and v not in ['ProjectID', 'Updated']:
                payload[k] = rcval

        url:str = f"{RC_API}/project/"
        response:Response = requests.put(url, json=payload, headers=self._headers(), timeout=5)
        projectid:str|None = None

        if response.status_code in [200, 202]:
            data:dict = response.json()
            projectid = data.get('buildId', None)

        if response.status_code == 409:
            # This probably only happens if someone's done something weird like deleting & recreating a build.
            projectid = build.get('ProjectID', None)

        if projectid == None:
            Debug.logger.error(f"Project not found {response} {response.content}")
            return

        self.colonisation.update_progress(progress.get('MarketID'), {'ProjectID': data.get('buildId')}, True)

        # Link the project to us.
        url:str = f"{RC_API}/project/{data.get('buildId')}/link/{self.colonisation.cmdr}"
        response:Response = requests.put(url, headers=self._headers(), timeout=5)
        if response.status_code not in [200, 202]:
            Debug.logger.error(f"{url} {response} {response.content}")
            return

        Debug.logger.info(f"RavenColonial project created {data.get('buildName', 'Unknown')}")


    @catch_exceptions
    def upsert_project(self, system:dict, build:dict, progress:dict) -> None:
        """ Update build progress """

        # Create project if we don't have an id.
        if progress.get('ProjectID', None) == None:
            self.create_project(system, build, progress)

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

            if rcval != None and v != 'Updated':
                payload[k] = rcval

        if payload == self._cache.get(progress.get('ProjectID', ''), {}):return
        self._cache[progress.get('ProjectID', '')] = payload

        url:str = f"{RC_API}/project/{progress.get('ProjectID')}"
        self.bgstally.request_manager.queue_request(url, RequestMethod.PATCH, payload=payload, headers=self._headers(), callback=self._project_callback)


    @catch_exceptions
    def _project_callback(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        """ Process the results of querying RavenColonial """
        if response.status_code == 404:
            Debug.logger.info(f"Project not found, cannot update {response} Response.content [{response.content}] Request [{request}]")
            # Get projectid from request endpoint
            pid:str = re.search(r"/project/([^/]+)", request.endpoint).group(1)
            # Remove this project ID from progress
            self.colonisation.update_progress(pid, {'ProjectID': None}, True)
            return

        if success == False:
            Debug.logger.warning(f"Project submission failed {success} {response.status_code} response.content [{response.content}] request [{request}]")
            return

        data:dict = response.json()
        self.colonisation.update_progress(data.get('buildId'), {'Updated': re.sub(r"\.\d+\+00:00$", "Z", str(data.get('timestamp')))}, True)


    @catch_exceptions
    def load_project(self, progress:dict) -> None:
        projectid:str|None = progress.get('ProjectID', None)
        if projectid == None: return

        url:str = f"{RC_API}/project/{projectid}/last"
        response:Response = requests.get(url, headers=self._headers(),timeout=5)
        if response.status_code != 200:
            Debug.logger.error(f"Error for {url} {response} {response.content}")
            return

        if response.content == '0001-01-01T00:00:00+00:00':
            Debug.logger.error(f"Error with load project, doesn't exist")
            return

        if response.content != progress.get('Updated', ''):
            url = f"{RC_API}/project/{projectid}"
            self.bgstally.request_manager.queue_request(url, RequestMethod.GET, headers=self._headers(), callback=self._load_project_callback)


    @catch_exceptions
    def _load_project_callback(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        """ Process the results of querying RavenColonial for the project details """
        if response.status_code == 404:
            Debug.logger.info(f"Project not found, {response} Response.content [{response.content}] Request [{request}]")
            # Remove this project ID from progress
            pid:str = re.search(r"/project/([^/]+)", request.endpoint).group(1)
            self.colonisation.update_progress(pid, {'ProjectID': None}, True)
            return
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


    @catch_exceptions
    def record_contribution(self, project_id:int, contributions:list[dict]) -> None:
        """ Record colonisation contributions made """
        payload:dict = {re.sub(r"\$(.*)_name;$", r"\1", c.get('Name', '').lower()): c.get('Amount', 0) for c in contributions}

        # Which of the following to use?
        url:str = f"{RC_API}/project/{project_id}/contribute/{self.colonisation.cmdr}"
        response:Response = requests.post(url, json=payload, headers=self._headers(), timeout=5)
        if response.status_code not in [200, 202]:
            Debug.logger.error(f"{url} {response} {response.content}")
            return

        Debug.logger.debug(f"RavenColonial project contribution accepted {project_id}")


    @catch_exceptions
    def update_carrier(self, marketid:int, cargo:dict) -> None:
        """ Update the cargo of a fleet carrier """
        if self.colonisation.cmdr == None:
            Debug.logger.info("Cannot update carrier no cmdr")
            return

        payload:dict = {comm : cargo.get(comm, 0) for comm in self.bgstally.ui.commodities.keys()}
        url:str = f"{RC_API}/fc/{marketid}/cargo"
        self.bgstally.request_manager.queue_request(url, RequestMethod.POST, payload=payload, headers=self._headers(), callback=self._carrier_callback)
        return


    @catch_exceptions
    def _carrier_callback(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        """ Process the results of querying RavenColonial """
        data:dict = response.json()
        if success == False or response.status_code != 200:
            Debug.logger.warning(f"Error updating carrier {response} {response.content}")
            return

        Debug.logger.debug(f"RavenColonial carrier updated: {response}")



class EDSM:
    """
    Class to retrieve system, body and station data from EDSM.
    """
    _instance = None

    # Singleton pattern
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize if it's the first time
        if hasattr(self, '_initialized'): return
        self._initialized = True
        # Details to retrieve for bodies from EDSM
        self.body_details:list = ['name', 'bodyId', 'type', 'subType', 'terraformingState', 'isLandable', 'rotationalPeriodTidallyLocked', 'atmosphereType', 'volcanismType', 'rings', 'reserveLevel', 'distanceToArrival']


    @catch_exceptions
    def import_stations(self, system_name:str) -> None:
        """ Retrieve the stations in a system """
        if system_name == None or system_name == '':
            Debug.logger.info("No system name")
            return

        # Check when we last updated this system
        if not hasattr(RavenColonial(self), '_initialized'): return
        system:dict|None = RavenColonial(self).colonisation.find_system({'StarSystem': system_name})
        if system == None:
            Debug.logger.info(f"Unknown system {system_name}")
            return

        if system.get('Updated', 0) > int(time.time()) - EDSM_COOLDOWN:
            Debug.logger.info(f"Not refreshing stations for {system_name}, too soon {int(time.time()) - system.get('Updated', 0)}")
            return

        url:str = f"{EDSM_STATIONS}{quote(system_name)}"
        RavenColonial(self).bgstally.request_manager.queue_request(url, RequestMethod.GET, callback=self._stations)


    @catch_exceptions
    def _stations(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        ''' Process the results of querying ESDM for the stations in a system '''

        data:dict = response.json()
        if data.get('name', None) == None:
            Debug.logger.warning(f"Stations response did not contain a name, ignoring")
            return
        system:dict|None = RavenColonial(self).colonisation.find_system({'StarSystem': data.get('name')})
        if system == None:
            Debug.logger.warning(f"Stations didn't find system {data.get('name')}")
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

            if RavenColonial(self).colonisation.find_build(system, {'MarketID': base.get('marketId'), 'Name': name}) != None:
                Debug.logger.debug(f"Build {name} already exists in system {data.get('name')}, skipping")
                continue

                            # Avoid creating leftover construction sites
            if 'Construction Site' in name:
                if RavenColonial(self).colonisation.find_build(system, {'Name': re.sub(r".* Construction Site: ", "", name)}) != None:
                    Debug.logger.debug(f"Skipping build {name}")
                    continue

            if 'Construction Site' in name:
                build = RavenColonial(self).colonisation.find_build(system, {'MarketID': base.get('marketId'), 'Name': name})
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
            RavenColonial(self).colonisation.add_build(system, build)
            Debug.logger.debug(f"Added station {build} to system {data.get('name')}")

        RavenColonial(self).bgstally.ui.window_colonisation.update_display()


    @catch_exceptions
    def import_system(self, system_name:str) -> None:
        """ Retrieve the details of a system """
        if system_name == None or system_name == '':
            Debug.logger.info("No system name")
            return

        if not hasattr(RavenColonial(self), '_initialized'): return

        # Check when we last updated this system
        system:dict|None = RavenColonial(self).colonisation.find_system({'StarSystem': system_name})
        if system == None:
            Debug.logger.info(f"Unknown system {system_name}")
            return

        if system.get('EDSMUpdated', 0) > int(time.time()) - EDSM_COOLDOWN:
            Debug.logger.info(f"Not refreshing {system_name}, too soon")
            return

        url:str = f"{EDSM_SYSTEM}{quote(system_name)}"
        RavenColonial(self).bgstally.request_manager.queue_request(url, RequestMethod.GET, callback=self._system_callback)
        return


    @catch_exceptions
    def _system_callback(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        ''' Process the results of querying ESDM for the system details '''
        data:dict = response.json()
        if data.get('name', None) == None:
            Debug.logger.warning(f"system didn't contain a name, ignoring")
            return
        system:dict = RavenColonial(self).colonisation.find_system({'StarSystem' : data.get('name')})
        if system == None:
            Debug.logger.warning(f"system didn't find system {data.get('name')}")
            return

        changes:dict = {'Population' : get_by_path(data, ['information', 'population'], None),
                        'Economy' : get_by_path(data, ['information', 'economy'], None),
                        'Security' : get_by_path(data, ['information', 'security'], None),
                        'EDSMUpdated' : int(time.time())
                        }
        if get_by_path(data, ['information', 'secondEconomy'], 'None') != 'None':
            changes['Economy'] += "/" + get_by_path(data, ['information', 'secondEconomy'])

        RavenColonial(self).colonisation.modify_system(system, changes)


    @catch_exceptions
    def import_bodies(self, system_name:str) -> None:
        """ Retrieve the bodies in a system """
        if system_name == None or system_name == '':
            Debug.logger.info("No system name")
            return

        if not hasattr(RavenColonial(self), '_initialized'): return

        # Check when we last updated this system
        system:dict|None = RavenColonial(self).colonisation.find_system({'StarSystem': system_name})
        if system == None:
            Debug.logger.info(f"Unknown system {system_name}")
            return

        if system.get('Bodies', None) != None:
            Debug.logger.info(f"Already have body info for {system_name}")
            return

        url:str = f"{EDSM_BODIES}{quote(system_name)}"
        # We're going to do this synchronously since we need the data before we can proceed and it's a one-time call.
        response:Response = requests.get(url, headers=RavenColonial(self).base_headers, timeout=5)
        if response.status_code == 200:
            self._bodies(True, response)
        return


    def _bodies(self, success:bool, response:Response, request:BGSTallyRequest|None = None) -> None:
        ''' Process the results of querying ESDM for the bodies in a system '''

        data:dict = response.json()
        if data.get('name', None) == None:
            Debug.logger.info(f"Bodies didn't contain a name, ignoring")
            return
        system:dict = RavenColonial(self).colonisation.find_system({'StarSystem' : data.get('name')})
        if system == None:
            Debug.logger.info(f"Bodies didn't find system {data.get('name')}")
            return

        # Only record the body details that we need since returns an enormous amount of data.
        bodies:list = []
        for b in data.get('bodies', []):
            v:dict = {}
            for k in self.body_details:
                if b.get(k, None): v[k] = b.get(k)
            if b.get('parents', None) != None:
                v['parents'] = len(b.get('parents', []))
            bodies.append(v)

        RavenColonial(self).colonisation.modify_system(system, {'Bodies' : bodies})



class Spansh:
    """
    Class to retrieve system, body and station data from Spansh.
    """
    _instance = None

    # Singleton pattern
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize if it's the first time
        if not hasattr(self, '_initialized'):
            self.system_cache:dict = {} # Spansh has a single endpoint for all system data so cache it here rather than requerying.
            self._initialized = True
        self.body_details = ['name', 'bodyId', 'type', 'subType', 'terraformingState', 'isLandable', 'rotationalPeriodTidallyLocked', \
                             'atmosphereType', 'volcanismType', 'rings', 'reserveLevel', 'distanceToArrival']

    def import_stations(self, system_name:str) -> None:
        return self._get_details(system_name, 'stations')

    def import_system(self, system_name:str) -> None:
        return self._get_details(system_name, 'system')

    def import_bodies(self, system_name:str) -> None:
        return self._get_details(system_name, 'bodies')

    @catch_exceptions
    def _get_by_name(self, system_name:str) -> dict|None:
        """ Retrieve the system address from Spansh """
        system:dict|None = RavenColonial(self).colonisation.find_system({'StarSystem': system_name})
        if system == None:
            Debug.logger.info(f"Unknown system {system_name}")
            return

        system_address:int|None = system.get('SystemAddress', None)
        if system_address != None:
            Debug.logger.debug(f"System {system_name} has address {system_address} in local data")
            return system_address

        url:str = f"{SPANSH_API}/search?q={quote(system_name)}"
        response:Response = requests.get(url, headers=RavenColonial(self).base_headers, timeout=5)
        if response.status_code != 200:
            Debug.logger.error(f"Query system response for {system_name}: {response.status_code}")
            return None
        data:dict = response.json()

        return get_by_path(data.get('results',[])[0], ['record'], None)


    @catch_exceptions
    def _get_details(self, system_name:str, which:str) -> None:
        """ Retrieve a system's details """
        if system_name == None or system_name == '':
            Debug.logger.info("No system name given")
            return

        # Check when we last updated this system
        if not hasattr(RavenColonial(self), '_initialized'): return

        system:dict|None = RavenColonial(self).colonisation.find_system({'StarSystem': system_name})
        if system == None:
            Debug.logger.info(f"Unknown system {system_name}")
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
            RavenColonial(self).bgstally.request_manager.queue_request(url, RequestMethod.GET, callback=partial(self._callback, system, which))
            return

        url:str = f"{SPANSH_API}/search?q={quote(system_name)}"
        response:Response = requests.get(url, headers=RavenColonial(self).base_headers, timeout=5)
        RavenColonial(self).bgstally.request_manager.queue_request(url, RequestMethod.GET, callback=partial(self._callback, system, which))


    @catch_exceptions
    def _callback(self, system:dict, which: str, success:bool, response:Response, request:BGSTallyRequest) -> None:
        ''' Process the results of querying Spansh for the system details '''
        if success == False:
            Debug.logger.error(f"System query failed {response.content}")
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
            Debug.logger.warning(f"System didn't contain a name, ignoring {data}")
            return

        self.system_cache[data.get('id64', None)] = data
        match which:
            case 'bodies': return self._update_bodies(system, data)
            case 'stations': return self._update_stations(system, data)
            case 'system': return self._update_system(system, data)


    @catch_exceptions
    def _update_system(self, system:dict, data:dict) -> None:
        """ Update the system details"""
        update:dict = {}
        update['Population'] = data.get('population', None)
        update['Economy'] = data.get('primary_economy', None)
        if data.get('primary_economy', None) != None and data.get('secondary_economy', 'None') != None:
            update['Economy'] += "/" + data.get('secondary_economy', '')
        update['Security'] = data.get('security', None)
        update['SystemAddress'] = data.get('id64', None)
        update['SpanshUpdated'] = int(time.time())

        RavenColonial(self).colonisation.modify_system(system, update)


    @catch_exceptions
    def _update_stations(self, system:dict, data:dict) -> None:
        ''' Process the results of querying for the stations in a system '''
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

            if RavenColonial(self).colonisation.find_build(system, {'MarketID': market_id, 'Name': name}) != None:
                Debug.logger.debug(f"Build {name} already exists in system {data.get('name')}, skipping")
                continue

            # Look for a completed base with the same name since depots sometimes hang around.
            if 'Construction Site' in base.get('name', '') and \
                RavenColonial(self).colonisation.find_build(system, {'Name': re.sub(r".* Construction Site: ", "", base.get('name'))}) != None:
                    Debug.logger.debug(f"Skipping construction site {base.get('name')}")
                    continue

            build:dict = {
                'Base Type': base.get('type'),
                'StationEconomy': base.get('economy'),
                'State': state,
                'Name': name,
                'MarketID': market_id
                }
            Debug.logger.debug(f"Adding station base.get('name', '') to system {data.get('name')} {build}")
            RavenColonial(self).colonisation.add_build(system, build)


    @catch_exceptions
    def _update_bodies(self, system:dict, data:dict) -> None:
        ''' Process the results of querying Spansh for the bodies in a system '''
        if data.get('name', None) == None:
            Debug.logger.warning(f"bodies didn't contain a name, ignoring")
            return

        # Only record the body details that we need since returns an enormous amount of data.
        bodies:list = []
        for b in data.get('bodies', []):
            v:dict = {}
            for k in self.body_details:
                if b.get(k, None): v[k] = b.get(k)
            if b.get('parents', None) != None:
                v['parents'] = len(b.get('parents', []))
            bodies.append(v)

        if bodies != []:
            RavenColonial(self).colonisation.modify_system(system, {'Bodies': bodies})
