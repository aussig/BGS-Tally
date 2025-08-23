import json
from json import JSONDecodeError
from urllib.parse import quote
from os import path
from os.path import join
import traceback
import re
import time
from datetime import datetime, timedelta, timezone
import requests
from requests import Response
from config import config
from bgstally.constants import RequestMethod, BuildState
from bgstally.requestmanager import BGSTallyRequest
from bgstally.debug import Debug
from bgstally.utils import _, get_by_path

RC_API = 'https://ravencolonial100-awcbdvabgze4c5cq.canadacentral-01.azurewebsites.net/api'
RC_COOLDOWN = 60

class RavenColonial:
    """
    Class to handle all the data syncing between the colonisation system and RavenColonial.com

    It syncs systems and sites, projects, contributions and fleet carrier cargo.
    Many requests are queued to the request manager to avoid blocking EDMC but some are done synchronously where appropriate.
    """
    def __init__(self, colonisation) -> None:
        self.colonisation:Colonisation = colonisation
        self.bgstally:BGSTally = colonisation.bgstally

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
        self.site_params:dict = {'id' : 'RCID',
                                 'name' : 'Name',
                                 'bodyNum' : 'BodyNum',
                                 'buildType' : 'Layout',
                                 'status' : 'State',
                                 'buildId' : 'BuildID',
                                 'architectName' : 'Architect'
                                 }
        # Project parameter mapping between colonisation & raven.
        self.project_params:dict = {
            'marketId': 'MarketID',
            'systemAddress': 'SystemAddress',
            'buildName': 'Name',
            'buildId': 'RCID',
            'commodities': 'Commodities',
            'colonisationConstructionDepot': 'event',
            'buildType': 'Layout',
            'bodyNum': 'BodyNum',
            'architectName': 'Architect',
            'timeDue': 'Deadline',
            'isPrimaryPort': 'Primary',
            'bodyType': 'BodyType'
            }

        # build state parameters between colonisation & raven.
        self.status_map:dict = {
            'plan': BuildState.PLANNED.value,
            'build': BuildState.PROGRESS.value,
            'complete': BuildState.COMPLETE.value
        }

        self._cache:dict = {} # Cache of responses and response times used to reduce API calls


    def load_system(self, id64:str = None, rev:str = None) -> None:
        """ Retrieve the rcdata data with the latest system data from RC when we start. """
        Debug.logger.debug(f"Load system {id64}")

        # Implement cooldown and revision tracking
        if self._cache.get(id64, None) == None: self._cache[id64] = {}

        if self._cache[id64].get('ts', 0) > round(time.mktime(datetime.now(timezone.utc).timetuple())) - RC_COOLDOWN:
            Debug.logger.info(f"Not refreshing {id64}, too soon")
            return

        self._cache[id64]['rev'] = rev
        self._cache[id64]['ts'] = round(time.mktime(datetime.now(timezone.utc).timetuple()))

        # This just returns a commanders list of project (or system?) revisions.
        #url:str = f"{RC_API}/v2/system/revs"
        #response:Response = requests.get(url, headers=self.headers,timeout=5)
        #Debug.logger.info(f"Response for /revs {id64}: {response.status_code} {response}")
        #data:dict = response.json()

        url:str = f"{RC_API}/v2/system/{id64}"
        self.bgstally.request_manager.queue_request(url, RequestMethod.GET, callback=self._load_response)
        return


    def add_system(self, system_name:str = None) -> None:
        """ Add a system to RC. """

        if self.colonisation.cmdr == None:
            Debug.logger.info("Not adding system no commander")
            return

        url:str = f"{RC_API}/v2/system/{quote(system_name)}"
        self.headers["rcc-cmdr"] = self.colonisation.cmdr
        response:Response = requests.get(url, headers=self.headers,timeout=5)
        Debug.logger.info(f"Response for {system_name}: {response.status_code}")
        data:dict = response.json()

        # Add a new system to RavenColonial
        if response.status_code == 404:
            url:str = f"{RC_API}/v2/system/{quote(system_name)}/import/"
            response:Response = requests.post(url, headers=self.headers, timeout=5)
            data:dict = response.json()

            if response.status_code != 200:
                Debug.logger.error(f"Failed to import system {system_name}: {response.status_code} system data: {data}")
                return

        # Merge RC data with system data
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



    def upsert_site(self, system:dict, ind:int, data:dict = None) -> None:
        """ Modify a site (build) in RavenColonial """
        try:
            if self.colonisation.cmdr == None:
                Debug.logger.info(f"Cannot upsert site, no cmdr")
                return

            build:dict = system['Builds'][ind]

            if build == None or data == None:
                Debug.logger.warning("RavenColonial upsert_site called with no build or no data")
                return

            # Create an ID if necessary
            if build.get('RCID', None) == None and build['State'] == BuildState.COMPLETE and build.get('MarketID', None) != None:
                build['RCID'] = f"&{build['MarketID']}"

            if build.get('RCID', None) == None and build['State'] == BuildState.PLANNED:
                timestamp:int = round(time.mktime(datetime.now(timezone.utc).timetuple()))
                build['RCID'] = f"x{timestamp}"

            update:dict = {}
            rev_map = {value: key for key, value in self.status_map.items()}
            for p, m in self.site_params.items():
                rcval = build.get(m, '').strip().lower().replace(' ', '_') if isinstance(build.get(m, None), str) and 'name' not in p.lower() else build.get(m, None)
                if p == 'status': rcval = rev_map[build.get(m, '')]
                if rcval != None:
                    update[p] = rcval

            payload:dict = {'update': [update], 'delete':[]}

            url:str = f"{RC_API}/v2/system/{system.get('ID64')}/sites"
            self.headers["rcc-cmdr"] = system.get('Architect')

            Debug.logger.info(f"RavenColonial upserting site {payload}")

            response:Response = requests.put(url, json=payload, headers=self.headers, timeout=5)
            if response.status_code != 200:
                Debug.logger.error(f"{url} {response} {response.content}")

            # Refresh the system info
            self.load_system(system.get('SystemAddress'))

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

            if build.get('RCID', None) == None:
                Debug.logger.warning("RavenColonial modify_site called for non-RC site")
                return

            payload:dict = {'update': [], 'delete':[build.get('RCID')]}
            Debug.logger.info(f"RavenColonial removing site {payload}")
            url:str = f"{RC_API}/v2/system/{system.get('ID64')}/sites"
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
            systems:list = self.colonisation.get_all_systems()
            system:dict = self.colonisation.find_system({'SystemAddress' : data.get('id64', None),
                                                         'StarSystem': data.get('name', None)})
            sysnum:int|None = systems.index(system)
            if sysnum == None:
                Debug.logger.info(f"Can't merge, system {data.get('name', None)} not found")
                return

            mod:dict = {}
            for k, v in self.sys_params.items():
                if k != 'rev' and data.get(k, '') != '' and \
                    data.get(k, None) != self.colonisation.systems[sysnum].get(v, None):
                    mod[v] = data.get(k, None).strip() if isinstance(data.get(k, None), str) else data.get(k, None)

            if mod != {}:
                Debug.logger.debug(f"Changes found, modyfing system {mod}")
                self.colonisation.modify_system(sysnum, mod)

            for site in data.get('sites', []):
                build:dict = self.colonisation.find_build(system, {'MarketID': site.get('id', -1)[1:],
                                                                   'Name': site.get('name', -1),
                                                                   'RCID' : site.get('id', -1)})
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
                        Debug.logger.info(f"Adding build {sysnum} {deets}")
                        self.colonisation.add_build(sysnum, deets, True)
                    else:
                        Debug.logger.info(f"Updating build {sysnum} {system['Builds'].index(build)} {deets}")
                        self.colonisation.modify_build(sysnum, system['Builds'].index(build), deets, True)
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
            for ind, b in enumerate(system['Builds']):
                if b.get('Layout', None) == None or b.get('BodyNum', None) == None:
                    continue

                for site in data.get('sites', []):
                    if site.get('id', None) == b.get('RCID', None):
                        break

                if site.get('id', None) != b.get('RCID', None):
                    self.upsert_site(system, ind, b)

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
            systems:list = self.colonisation.get_all_systems()
            system:dict = self.colonisation.find_system({'StarSystem': data.get('name', None)})
            sysnum:int|None = systems.index(system)

            if sysnum == None:
                Debug.logger.info(f"RavenColonial system {data.get('id64', None)} not found")
                return

            self.colonisation.modify_system(sysnum, {
                'SystemAddress': data.get('id64', None),
                'StarSystem': data.get('name', None),
                'Name': data.get('name', None),
                'Architect': data.get('architect', None)
            })

            # Update the system's builds with the data from RC
            for ind, build in enumerate(system.get('Builds', [])):
                site:dict = {}
                for site in data.get('sites', []):
                    if site.get('name', None) == build.get('name', None):
                        break

                deets:dict = {}
                for p, m in self.site_params.items():
                    if site.get(p, None) != None:
                        deets[m] = self.status_map[site[p]] if p == 'status' else site.get(p)
                if deets != {}:
                    self.colonisation.modify_build(sysnum, ind, deets, True)
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
            elif k == 'commodities':
                rcval = {re.sub(r"\$(.*)_name;", r"\1", comm['Name']).lower() : comm['RequiredAmount'] for comm in progress.get('ResourcesRequired')}

            if rcval != None:
                payload[k] = rcval

        url:str = f"{RC_API}/project/"
        response:Response = requests.put(url, json=payload, headers=self.headers, timeout=5)
        if response.status_code not in [200, 202]:
            Debug.logger.error(f"{url} {response} {response.content}")
            return

        # Set the project ID in the progress
        data:dict = response.json()
        self.colonisation.update_progress(progress.get('MarketID'), {'ProjectID': data.get('buildId')})

        # Link the project to us.
        url:str = f"{RC_API}/project/{data.get('buildId')}/link/{self.colonisation.cmdr}"
        response:Response = requests.put(url, headers=self.headers, timeout=5)
        if response.status_code not in [200, 202]:
            Debug.logger.error(f"{url} {response} {response.content}")
            return

        return


    def upsert_project(self, system:dict, build:dict, progress:dict, event:dict) -> None:
        """ Update build progress """
        # Required: buildId (though maybe not if you use )
        try:

            # Create project if we don't have an id.
            if progress.get('ProjectID', None) == None:
                self.create_project(system, build, progress)
                return

            # Update project
            payload:dict = {'colonisationConstructionDepot': event}
            for k, v in self.project_params.items():
                rcval = None
                if progress.get(v, None) != None:
                    rcval = progress.get(v, '').strip().lower().replace(' ', '_') if isinstance(progress.get(v, None), str) and 'name' not in k.lower() else progress.get(v, None)
                elif build.get(v, None) != None:
                    rcval = build.get(v, '').strip().lower().replace(' ', '_') if isinstance(build.get(v, None), str) and 'name' not in k.lower() else build.get(v, None)
                elif system.get(v, None) != None:
                    rcval = system.get(v, '').strip().lower().replace(' ', '_') if isinstance(system.get(v, None), str) and 'name' not in k.lower() else system.get(v, None)
                elif k == 'commodities':
                    rcval = {re.sub(r"\$(.*)_name;", r"\1", comm['Name']).lower() : comm['RequiredAmount'] - comm['ProvidedAmount'] for comm in progress.get('ResourcesRequired')}

                if rcval != None:
                    payload[k] = rcval

            url = f"{RC_API}/project/{progress.get('ProjectID')}"
            self.headers["rcc-cmdr"] = self.colonisation.cmdr
            Debug.logger.debug(f"Sending project update: {payload}")
            #Debug.logger.debug(f"{url} {payload} {self.headers}")
            #response:Response = requests.patch(url, json=payload, headers=self.headers, timeout=5)
            #Debug.logger.debug(f"{url} {response} {response.content}")
            self.bgstally.request_manager.queue_request(url, RequestMethod.PATCH, payload=payload, headers=self.headers, callback=self._project_callback)
            return

        except Exception as e:
            Debug.logger.info(f"Error upserting project")
            Debug.logger.error(traceback.format_exc())


    def _project_callback(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        """ Process the results of querying RavenColonial """
        data:dict = response.json()
        self._cache[data.get('buildId')] = data.get('timestamp')

        if success == True:
            Debug.logger.debug(f"Project submission succeeded")
            return

        Debug.logger.debug(f"Project submission failed {success} {response} {request}")


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

            if response.content != self._cache.get(projectid, ''):
                self._cache[projectid] = response.content
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
                Debug.logger.error(f"Project load failed {response.content}")
                return

            data:dict = response.json()
            self._cache[data.get('buildId')] = data.get('timestamp')

            # Need to figure out what we're going to update here.
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

            payload:dict = {re.sub(r"\$(.*)_name;", r"\1", comm).lower() : qty for comm, qty in cargo.items()}
            url:str = f"{RC_API}/FC/{marketid}/cargo"
            self.headers["rcc-cmdr"] = self.colonisation.cmdr
            self.bgstally.request_manager.queue_request(url, RequestMethod.PATCH, payload=payload, headers=self.headers, callback=self._carrier_callback)
            return

        except Exception as e:
            Debug.logger.info(f"Error updating carrier")
            Debug.logger.error(traceback.format_exc())


    def _carrier_callback(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        """ Process the results of querying RavenColonial """
        data:dict = response.json()
        if success == False or response.status_code != 200:
            Debug.logger.debug(f"Error updating carrier {response} {response.content}")
            return

        return
