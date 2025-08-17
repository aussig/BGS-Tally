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

class RavenColonial:
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

        self.sys_params:dict = {
            'id64': 'ID64',
            'name': 'SystemAddress',
            'architect': 'Architect'
        }
        self.site_params:dict = {'id' : 'RCID',
                                 'name' : 'Name',
                                 'bodyNum' : 'BodyNum',
                                 'buildType' : 'Layout',
                                 'status' : 'State',
                                 'buildId' : 'BuildID'
                                 }
        self.status_map:dict = {
            'plan': BuildState.PLANNED.value,
            'progress': BuildState.PROGRESS.value,
            'complete': BuildState.COMPLETE.value
        }

        self.systems:dict = {} # The last responses we got from RC for each system

    def load_system(self, id64:str = None) -> None:
        """ Retrieve the rcdata data with the latest system data from RC when we start. """

        # Implement a 60 second cooldown
        if self.systems.get(id64, None) is not None and self.systems[id64].get('ts', None) is not None and \
            self.systems[id64]['ts'] > round(time.mktime(datetime.now(timezone.utc).timetuple())) - 60:
            return

        if self.systems.get('id64', None) is None: self.systems[id64] = {}
        self.systems[id64]['ts'] = round(time.mktime(datetime.now(timezone.utc).timetuple()))

        url:str = f"{RC_API}/v2/system/{id64}"
        self.bgstally.request_manager.queue_request(url, RequestMethod.GET, callback=self._load_response)
        return


    def add_system(self, system_name:str = None) -> None:
        """ Retrieve the rcdata data with the latest system data from RC when we start. """

        Debug.logger.debug(f"CMDR: {self.colonisation.cmdr}")
        url:str = f"{RC_API}/v2/system/{quote(system_name)}"
        self.headers["rcc-cmdr"] = self.colonisation.cmdr

        response:Response = requests.get(url, headers=self.headers,timeout=5)
        data:dict = response.json()
        Debug.logger.info(f"Response for {system_name}: {response.status_code}")

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
        Debug.logger.info(f"RavenColonial modifying site {json.dumps(payload, indent=4)}")

        url:str = f"{RC_API}/v2/system/{quote(system_name)}/sites"

        Debug.logger.debug(f"headers: {self.headers}")
        response:Response = requests.put(url, json=payload, headers=self.headers, timeout=5)
        Debug.logger.debug(f"{url} {response} {response.content}")

        return


    def upsert_site(self, system:dict, ind:int, data:dict = None) -> None:
        """ Modify a site in RavenColonial """
        try:
            build:dict = system['Builds'][ind]

            if build is None or data is None:
                Debug.logger.warning("RavenColonial modify_site called with no build or no data")
                return

            # Create the ID and store it
            if build.get('RCID', None) is None:
                timestamp:int = round(time.mktime(datetime.now(timezone.utc).timetuple()))
                build['RCID'] = f"x{timestamp}"

            update:dict = {}
            rev_map = {value: key for key, value in self.status_map.items()}
            for p, m in self.site_params.items():
                rcval = build.get(m, '').strip().lower() if isinstance(build.get(m, None), str) and p not in ['name'] else build.get(m, None)
                if p == 'status': rcval = rev_map[build.get(m, '')]
                if rcval is not None:
                    update[p] = rcval

            payload:dict = {'update': [update], 'delete':[]}
            Debug.logger.info(f"RavenColonial modifying site {json.dumps(payload, indent=4)}")

            url:str = f"{RC_API}/v2/system/{system.get('ID64')}/sites"
            self.headers["rcc-cmdr"] = self.colonisation.cmdr

            Debug.logger.debug(f"headers: {self.headers}")
            response:Response = requests.put(url, json=payload, headers=self.headers, timeout=5)
            Debug.logger.debug(f"{url} {response} {response.content}")

            # Refresh the system info
            self.load_system(system.get('SystemAddress'))

            return

        except Exception as e:
            Debug.logger.info(f"Error upserting site")
            Debug.logger.error(traceback.format_exc())


    def remove_site(self, system:dict, ind:int) -> None:
        """ Remove a site from RavenColonial """
        try:
            Debug.logger.debug(f"RavenColonial remove_site called for build {ind}")
            build:dict = system['Builds'][ind]

            if build.get('RCID', None) is None:
                Debug.logger.warning("RavenColonial modify_site called for non-RC site")
                return

            payload:dict = {'update': [], 'delete':[build.get('RCID')]}
            Debug.logger.info(f"RavenColonial modifying site {payload}")
            url:str = f"{RC_API}/v2/system/{system.get('ID64')}/sites"
            self.headers["rcc-cmdr"] = self.colonisation.cmdr
            response:Response = requests.put(url, json=payload, headers=self.headers, timeout=5)
            Debug.logger.debug(f"{url} {response} {response.content}")
            #self.session_put(url, payload)
            return

        except Exception as e:
            Debug.logger.info(f"Error recording remove_site response")
            Debug.logger.error(traceback.format_exc())


    def _merge_system_data(self, data:dict) -> None:
        """ Merge the data from RavenColonial into the system data """
        try:
            Debug.logger.debug(f"Merging data")
            sysnum = self.colonisation.get_sysnum('StarSystem', data.get('name', None))
            if sysnum is None:
                Debug.logger.info(f"Can't merge, system {data.get('name', None)} not found")
                return

            mod:dict = {}
            for k, v in self.sys_params.items():
                if data.get(k, None) is not None and data.get(k, None) != self.colonisation.systems[sysnum].get(v, None):
                    mod[v] = data.get(k, None).strip() if isinstance(data.get(k, None), str) else data.get(k, None)

            if mod != {}:
                Debug.logger.debug(f"Changes found, modyfing system {mod}")
                self.colonisation.modify_system(sysnum, mod)

            for site in data.get('sites', []):
                #Debug.logger.debug(f"Processing site {site}")
                build:dict = {}
                i:int = None
                found:bool = False
                for i, build in enumerate(self.colonisation.systems[sysnum].get('Builds', [])):
                    if site.get('id', -1) == build.get('RCID', None): # Full match
                        found = True
                        break
                    elif build.get('RCID', None) is None and \
                         (site.get('name', -1) == build.get('Name', None) or \
                            (site.get('buildType', "Unknown") == build.get('Layout', None) and \
                                site.get('bodyId', -1) == build.get('BodyNum', None))): # Fuzzy match
                        found = True
                        break

                deets:dict = {}
                for p, m in self.site_params.items():
                    rcval = site.get(p, '').strip().title() if isinstance(site.get(p, None), str) and p not in ['id', 'buildId'] else site.get(p, None)
                    if p == 'status': rcval = self.status_map[site[p]]
                    if rcval is not None and rcval is not -1 and rcval != build.get(m, None):
                        Debug.logger.debug(f"Current: {build.get(m, None)} New: {rcval}")
                        deets[m] = rcval

                if deets != {}:
                    if found is False:
                        self.colonisation.add_build(sysnum, deets)
                    else:
                        self.colonisation.modify_build(sysnum, i, deets)
            return

        except Exception as e:
            Debug.logger.info(f"Error recording _rc_system response")
            Debug.logger.error(traceback.format_exc())

    def _load_response(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        """ Process the results of querying RavenColonial for the system details """
        try:
            if success == False:
                Debug.logger.debug(f"System load failed")
                return

            data:dict = response.json()
            if self.colonisation.get_sysnum('ID64', data.get('id64', None)) == None:
                Debug.logger.info(f"RavenColonial system {data.get('id64', None)} not found")
                return

            if self.systems[data['id64']].get('data', {}) == data:
                Debug.logger.debug(f"System hasn't changed no update required")
                return

            self.systems[data['id64']]['data'] = data
            self._merge_system_data(data)
            return

        except Exception as e:
            Debug.logger.info(f"Error recording _rc_system response")
            Debug.logger.error(traceback.format_exc())


    def _add_response(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        """ Add a system to RavenColonial """
        try:
            if success == False:
                return
            data:dict = response.json()

            Debug.logger.info(f"RavenColonial system data: {data}")

            sysnum:int|None = self.colonisation.sysnum(data.get('id64', None), data.get('name', None))

            if sysnum == None:
                Debug.logger.info(f"RavenColonial system {data.get('id64', None)} not found")
                return

            self.colonisation.modify_system(sysnum, {
                'ID64': data.get('id64', None),
                'Name': data.get('name', None),
                'Architect': data.get('architect', None)
            })

            # Update the system's builds with the data from RC
            for build in system.get('Builds', []):
                site:dict = {}
                for site in data.get('sites', []):
                    if site.get('name', None) == build.get('name', None):
                        break

                for p, m in self.site_params.items():
                    if site.get(p, None) is not None:
                        build[m] = self.status_map[site[p]] if p == 'status' else site.get(p, None)

            self.colonisation.dirty = True
            self.colonisation.save('RC system data updated')
            return

        except Exception as e:
            Debug.logger.info(f"Error recording _rc_system response")
            Debug.logger.error(traceback.format_exc())


    def _request_complete(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        """ Generic request completion handler """
        if not success:
            Debug.logger.warning(f"RavenColonial Call failed. Reason: '{response.reason}' URL: '{request.endpoint}")
            Debug.logger.debug(f"Content: '{response.content}' URL: '{request.endpoint}'")
        else:
            Debug.logger.debug(f"RavenColonial update succeeded")
        return

    def session_put(url:str, payload:json) -> None:
        ''' Do a session-based put '''
        try:
            # Version using sessions. It doesn't help with the auth issues.
            with requests.Session() as session:
                #url:str = f"{RC_API}/cmdr/NavlGazr/primary/{quote(system['StarSystem'])}"
                url:str = f"{RC_API}/cmdr/{self.colonisation.cmdr}/primary"
                response:Response = session.get(url, headers=self.headers, timeout=5)

                response:Response = session.put(url, json=payload, headers=self.headers, timeout=5)
                Debug.logger.debug(f"{url} {response} {response.content}")
            return

        except Exception as e:
            Debug.logger.info(f"Error in session_put")
            Debug.logger.error(traceback.format_exc())
