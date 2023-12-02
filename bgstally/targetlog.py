import json
import os.path
import re
from datetime import datetime, timedelta

from copy import copy

from requests import Response

from bgstally.constants import DATETIME_FORMAT_JOURNAL, FOLDER_DATA, RequestMethod
from bgstally.debug import Debug
from bgstally.requestmanager import BGSTallyRequest

FILENAME = "targetlog.json"
TIME_TARGET_LOG_EXPIRY_D = 90
URL_INARA_API = "https://inara.cz/inapi/v1/"
DATETIME_FORMAT_INARA = "%Y-%m-%dT%H:%M:%SZ"


class TargetLog:
    """
    Handle a log of all targeted players
    """
    cmdr_name_pattern:re.Pattern = re.compile(r"\$cmdr_decorate\:#name=([^]]*);")

    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.targetlog = []
        self.cmdr_cache = {}
        self.load()
        self._expire_old_targets()


    def load(self):
        """
        Load state from file
        """
        file = os.path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)
        if os.path.exists(file):
            try:
                with open(file) as json_file:
                    self.targetlog = json.load(json_file)
            except Exception as e:
                Debug.logger.info(f"Unable to load {file}")


    def save(self):
        """
        Save state to file
        """
        file = os.path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self.targetlog, outfile)


    def get_targetlog(self):
        """
        Get the current target log
        """
        return self.targetlog


    def get_target_info(self, cmdr_name:str):
        """
        Look up and return latest information on a CMDR
        """
        return next((item for item in reversed(self.targetlog) if item['TargetName'] == cmdr_name), None)


    def ship_targeted(self, journal_entry: dict, system: str):
        """
        A ship targeted event has been received, if it's a player, add it to the target log
        """
        # Normal Player: { "timestamp":"2022-10-09T06:49:06Z", "event":"ShipTargeted", "TargetLocked":true, "Ship":"cutter", "Ship_Localised":"Imperial Cutter", "ScanStage":3, "PilotName":"$cmdr_decorate:#name=[Name];", "PilotName_Localised":"[CMDR Name]", "PilotRank":"Elite", "SquadronID":"TSPA", "ShieldHealth":100.000000, "HullHealth":100.000000, "LegalStatus":"Clean" }
        # Taxi Player:   { "timestamp":"2023-10-07T16:47:16Z", "event":"ShipTargeted", "TargetLocked":true, "Ship":"vulture_taxi", "Ship_Localised":"$VULTURE_NAME;", "ScanStage":3, "PilotName":"$npc_name_decorate:#name=[CMDR Name];", "PilotName_Localised":"[CMDR Name]", "PilotRank":"Harmless", "ShieldHealth":100.000000, "HullHealth":100.000000, "Faction":"FrontlineSolutions", "LegalStatus":"Clean" }
        # Normal NPC:    { "timestamp":"2023-10-03T21:08:08Z", "event":"ShipTargeted", "TargetLocked":true, "Ship":"federation_corvette", "Ship_Localised":"Federal Corvette", "ScanStage":3, "PilotName":"$npc_name_decorate:#name=John Ehrnstrom;", "PilotName_Localised":"John Ehrnstrom", "PilotRank":"Dangerous", "ShieldHealth":100.000000, "HullHealth":100.000000, "Faction":"Mafia of LTT 9552", "LegalStatus":"Wanted", "Bounty":609303 }

        if not 'ScanStage' in journal_entry or journal_entry['ScanStage'] < 3: return
        if not 'PilotName' in journal_entry: return

        cmdr_name:str = None
        cmdr_match = self.cmdr_name_pattern.match(journal_entry['PilotName'])

        if cmdr_match:
            # CMDR in their own ship
            cmdr_name = cmdr_match.group(1)
        elif "_taxi" in journal_entry.get('Ship', ""):
            # CMDR in a taxi
            cmdr_name = journal_entry.get('PilotName_Localised')

        if cmdr_name is None: return

        ship_type:str = "Vulture Taxi" if journal_entry.get('Ship', "") == "vulture_taxi" else journal_entry.get('Ship_Localised', journal_entry.get('Ship', '----'))

        cmdr_data:dict = {'TargetName': cmdr_name,
                    'System': system,
                    'SquadronID': journal_entry.get('SquadronID', "----"),
                    'Ship': ship_type,
                    'LegalStatus': journal_entry.get('LegalStatus', '----'),
                    'Notes': "Scanned",
                    'Timestamp': journal_entry['timestamp']}

        cmdr_data, different, pending = self._fetch_cmdr_info(cmdr_name, cmdr_data)
        if different and not pending: self.targetlog.append(cmdr_data)


    def friend_request(self, journal_entry: dict, system: str):
        """
        A friend request has been received
        """
        cmdr_name:str = journal_entry.get('Name', "")
        if cmdr_name == "": return

        cmdr_data:dict = {'TargetName': cmdr_name,
                    'System': system,
                    'SquadronID': "----",
                    'Ship': "----",
                    'LegalStatus': "----",
                    'Notes': "Received friend request",
                    'Timestamp': journal_entry['timestamp']}

        cmdr_data, different, pending = self._fetch_cmdr_info(cmdr_name, cmdr_data)
        if different and not pending: self.targetlog.append(cmdr_data)


    def interdicted(self, journal_entry: dict, system: str):
        """
        Interdicted by another ship
        """
        if journal_entry.get('IsPlayer', False) != True: return

        cmdr_name:str = journal_entry.get('Interdictor', "")
        if cmdr_name == "": return

        cmdr_data:dict = {'TargetName': cmdr_name,
                    'System': system,
                    'SquadronID': "----",
                    'Ship': "----",
                    'LegalStatus': "----",
                    'Notes': "Interdicted by",
                    'Timestamp': journal_entry['timestamp']}

        cmdr_data, different, pending = self._fetch_cmdr_info(cmdr_name, cmdr_data)
        if different and not pending: self.targetlog.append(cmdr_data)


    def died(self, journal_entry: dict, system: str):
        """
        Killed by another ship or team.
        """
        # Look for team kill first
        killers:list[dict] = journal_entry.get('Killers', [])
        if len(killers) == 0:
            # Not a team kill, check for solo kill
            if not 'KillerName' in journal_entry: return
            killers = [{'Name': journal_entry.get('KillerName'), 'Ship': journal_entry.get('KillerShip')}]

        for killer in killers:
            killer_name:str = killer.get('Name')
            if killer_name is None or not killer_name.startswith("Cmdr "): continue

            cmdr_data:dict = {'TargetName': killer_name[5:],
                    'System': system,
                    'SquadronID': "----",
                    'Ship': killer.get('Ship', "----"),
                    'LegalStatus': "----",
                    'Notes': "Killed by",
                    'Timestamp': journal_entry['timestamp']}

            cmdr_data, different, pending = self._fetch_cmdr_info(killer_name[5:], cmdr_data)
            if different and not pending: self.targetlog.append(cmdr_data)


    def received_text(self, journal_entry: dict, system: str):
        """
        Received a text message
        """
        # Only interested if it's in the 'local' channel, as that's the current system. Ignore all other messages.
        if journal_entry.get('Channel') != "local": return

        cmdr_name:str = journal_entry.get('From', "")
        if cmdr_name == "": return

        cmdr_data:dict = {'TargetName': cmdr_name,
                    'System': system,
                    'SquadronID': "----",
                    'Ship': "----",
                    'LegalStatus': "----",
                    'Notes': "Received message from",
                    'Timestamp': journal_entry['timestamp']}

        cmdr_data, different, pending = self._fetch_cmdr_info(cmdr_name, cmdr_data)
        if different and not pending: self.targetlog.append(cmdr_data)


    def team_invite(self, journal_entry: dict, system: str):
        """
        Received a team invite
        """
        cmdr_name:str = journal_entry.get('Name', "")
        if cmdr_name == "": return

        cmdr_data:dict = {'TargetName': cmdr_name,
                    'System': system,
                    'SquadronID': "----",
                    'Ship': "----",
                    'LegalStatus': "----",
                    'Notes': "Received team invite from",
                    'Timestamp': journal_entry['timestamp']}

        cmdr_data, different, pending = self._fetch_cmdr_info(cmdr_name, cmdr_data)
        if different and not pending: self.targetlog.append(cmdr_data)


    def _fetch_cmdr_info(self, cmdr_name:str, cmdr_data:dict):
        """
        Fetch additional CMDR data from Inara and enhance the cmdr_data Dict with it
        """
        if cmdr_name in self.cmdr_cache:
            # We have cached data. Check whether it's different enough to make a new log entry for this CMDR.
            # Different enough: Any of System, SquadronID, Ship and LegalStatus don't match (if blank in the new data, ignore).
            cmdr_cache_data:dict = self.cmdr_cache[cmdr_name]
            if cmdr_data['System'] == cmdr_cache_data['System'] \
                and (cmdr_data['SquadronID'] == cmdr_cache_data['SquadronID'] or cmdr_data['SquadronID'] == "----") \
                and (cmdr_data['Ship'] == cmdr_cache_data['Ship'] or cmdr_data['Ship'] == "----") \
                and (cmdr_data['LegalStatus'] == cmdr_cache_data['LegalStatus'] or cmdr_data['LegalStatus'] == "----"):
                return cmdr_cache_data, False, False

            # It's different, make a copy and update the fields that may have changed in the latest data. This ensures we avoid
            # expensive multiple calls to the Inara API, but keep a record of every sighting of the same CMDR. We assume Inara info
            # (squadron name, ranks, URLs) stay the same during a play session.
            cmdr_data_copy:dict = copy(self.cmdr_cache[cmdr_name])
            cmdr_data_copy['System'] = cmdr_data['System']
            if cmdr_data['Ship'] != "----": cmdr_data_copy['Ship'] = cmdr_data['Ship']
            if cmdr_data['LegalStatus'] != "----": cmdr_data_copy['LegalStatus'] = cmdr_data['LegalStatus']
            cmdr_data_copy['Notes'] = cmdr_data['Notes']
            cmdr_data_copy['Timestamp'] = cmdr_data['Timestamp']
            # Re-cache the data with the latest updates
            self.cmdr_cache[cmdr_name] = cmdr_data_copy
            return cmdr_data_copy, True, False

        # CMDR data not in cache, create a background request to fetch Inara data
        payload = {
            'header': {
                'appName': self.bgstally.plugin_name,
                'appVersion': str(self.bgstally.version),
                'isBeingDeveloped': "false",
                'APIkey': self.bgstally.config.apikey_inara()
            },
            'events': [
                {
                    'eventName': "getCommanderProfile",
                    'eventTimestamp': datetime.utcnow().strftime(DATETIME_FORMAT_INARA),
                    'eventData': {
                        'searchName': cmdr_name
                    }
                }
            ]
        }

        self.bgstally.request_manager.queue_request(URL_INARA_API, RequestMethod.POST, callback=self.inara_data_received, payload=payload, data=cmdr_data)

        return cmdr_data, True, True


    def inara_data_received(self, success:bool, response:Response, request:BGSTallyRequest):
        """
        A queued inara request has returned data, process it
        """
        if success:
            cmdr_data:dict = request.data
            response_data = response.json()
            if 'events' in response_data and len(response_data['events']) > 0 and 'eventData' in response_data['events'][0]:
                event_data = response_data['events'][0]['eventData']

                if 'commanderRanksPilot' in event_data:
                    cmdr_data['ranks'] = event_data['commanderRanksPilot']
                if 'commanderSquadron' in event_data:
                    cmdr_data['squadron'] = event_data['commanderSquadron']
                if 'inaraURL' in event_data:
                    cmdr_data['inaraURL'] = event_data['inaraURL']

        # In all cases (even Inara failure) add the CMDR to the cache and log because we will at least have in-game data for them
        self.cmdr_cache[cmdr_data['TargetName']] = cmdr_data
        self.targetlog.append(cmdr_data)


    def _expire_old_targets(self):
        """
        Clear out all old targets from the target log
        """
        for target in reversed(self.targetlog):
            timedifference = datetime.utcnow() - datetime.strptime(target['Timestamp'], DATETIME_FORMAT_JOURNAL)
            if timedifference > timedelta(days = TIME_TARGET_LOG_EXPIRY_D):
                self.targetlog.remove(target)
