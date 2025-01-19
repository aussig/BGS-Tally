import json
import re
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Dict

from bgstally.constants import (DATETIME_FORMAT_ACTIVITY, DATETIME_FORMAT_JOURNAL, DATETIME_FORMAT_TITLE, FILE_SUFFIX, ApiSizeLookup,
                                ApiSyntheticCZObjectiveType, ApiSyntheticEvent, ApiSyntheticScenarioType, CheckStates)
from bgstally.debug import Debug
from bgstally.missionlog import MissionLog
from bgstally.state import State
from bgstally.tick import Tick
from bgstally.utils import _, __, add_dicts
from thirdparty.colors import *

STATES_WAR = ['War', 'CivilWar']
STATES_ELECTION = ['Election']

# Missions that we count as +1 INF in Elections even if the Journal reports no +INF
MISSIONS_ELECTION = [
    'Mission_AltruismCredits_name',
    'Mission_Collect_name', 'Mission_Collect_Industrial_name',
    'Mission_Courier_name', 'Mission_Courier_Boom_name', 'Mission_Courier_Democracy_name', 'Mission_Courier_Elections_name', 'Mission_Courier_Expansion_name',
    'Mission_Delivery_name', 'Mission_Delivery_Agriculture_name', 'Mission_Delivery_Boom_name', 'Mission_Delivery_Confederacy_name', 'Mission_Delivery_Democracy_name',
    'Mission_Mining_name', 'Mission_Mining_Boom_name', 'Mission_Mining_Expansion_name',
    'Mission_OnFoot_Collect_MB_name',
    'Mission_OnFoot_Salvage_MB_name', 'Mission_OnFoot_Salvage_BS_MB_name',
    'Mission_PassengerBulk_name', 'Mission_PassengerBulk_AIDWORKER_ARRIVING_name', 'Mission_PassengerBulk_BUSINESS_ARRIVING_name', 'Mission_PassengerBulk_POLITICIAN_ARRIVING_name', 'Mission_PassengerBulk_SECURITY_ARRIVING_name',
    'Mission_PassengerVIP_name', 'Mission_PassengerVIP_CEO_BOOM_name', 'Mission_PassengerVIP_CEO_EXPANSION_name', 'Mission_PassengerVIP_Explorer_EXPANSION_name', 'Mission_PassengerVIP_Tourist_ELECTION_name', 'Mission_PassengerVIP_Tourist_BOOM_name',
    'Mission_Rescue_Elections_name',
    'Mission_Salvage_name', 'Mission_Salvage_Planet_name', 'MISSION_Salvage_Refinery_name',
    'MISSION_Scan_name',
    'Mission_Sightseeing_name', 'Mission_Sightseeing_Celebrity_ELECTION_name', 'Mission_Sightseeing_Tourist_BOOM_name',
    'Chain_HelpFinishTheOrder_name'
]

# Missions that we count as +1 INF in conflicts even if the Journal reports no +INF
MISSIONS_WAR = [
    'Mission_Assassinate_Legal_CivilWar_name', 'Mission_Assassinate_Legal_War_name',
    'Mission_Massacre_Conflict_CivilWar_name', 'Mission_Massacre_Conflict_War_name',
    'Mission_OnFoot_Assassination_Covert_MB_name',
    'Mission_OnFoot_Onslaught_Offline_MB_name'
]

# Missions that count towards the Thargoid War
MISSIONS_TW_COLLECT = [
    'Mission_TW_Collect_Alert_name', 'Mission_TW_CollectWing_Alert_name',
    'Mission_TW_Collect_Repairing_name', 'Mission_TW_CollectWing_Repairing_name',
    'Mission_TW_Collect_Recovery_name', 'Mission_TW_CollectWing_Recovery_name',
    'Mission_TW_Collect_UnderAttack_name', 'Mission_TW_CollectWing_UnderAttack_name'
]
MISSIONS_TW_EVAC_LOW = [
    'Mission_TW_Rescue_Alert_name', # "Evacuate n injured personnel" (cargo)
    'Mission_TW_PassengerEvacuation_Alert_name', # "n Refugees requesting evacuation" (passenger)
    'Mission_TW_RefugeeBulk_name', # "Evacuate xxx's group of refugees" (passenger)
    'Mission_TW_RefugeeVIP_name' # Evacuate xxx's party (passenger)
]
MISSIONS_TW_EVAC_MED = [
    'Mission_TW_Rescue_UnderAttack_name', # "Evacuate n wounded" (cargo)
    'Mission_TW_PassengerEvacuation_UnderAttack_name' # "n Refugees need evacuation" (passenger)
]
MISSIONS_TW_EVAC_HIGH = [
    'Mission_TW_Rescue_Burning_name', # "Evacuate n critically wounded civilians" (cargo)
    'Mission_TW_PassengerEvacuation_Burning_name' # "n Refugees need evacuation" (passenger)
]
MISSIONS_TW_MASSACRE = [
    'Mission_TW_Massacre_Scout_Singular_name', 'Mission_TW_Massacre_Scout_Plural_name',
    'Mission_TW_Massacre_Cyclops_Singular_name', 'Mission_TW_Massacre_Cyclops_Plural_name',
    'Mission_TW_Massacre_Basilisk_Singular_name', 'Mission_TW_Massacre_Basilisk_Plural_name',
    'Mission_TW_Massacre_Medusa_Singular_name', 'Mission_TW_Massacre_Medusa_Plural_name',
    'Mission_TW_Massacre_Hydra_Singular_name', 'Mission_TW_Massacre_Hydra_Plural_name',
    'Mission_TW_Massacre_Orthrus_Singular_name', 'Mission_TW_Massacre_Orthrus_Plural_name'
]
MISSIONS_TW_REACTIVATE = [
    'Mission_TW_OnFoot_Reboot_Occupied_MB_name'
]

SPACECZ_PILOTNAMES_CAPTAIN = [
    '$LUASC_Scenario_Warzone_NPC_WarzoneGeneral_Emp;',
    '$LUASC_Scenario_Warzone_NPC_WarzoneGeneral_Fed;',
    '$LUASC_Scenario_Warzone_NPC_WarzoneGeneral_Ind;'
]

SPACECZ_PILOTNAMES_SPECOPS = [
    '$LUASC_Scenario_Warzone_NPC_SpecOps_A;',
    '$LUASC_Scenario_Warzone_NPC_SpecOps_B;',
    '$LUASC_Scenario_Warzone_NPC_SpecOps_G;',
    '$LUASC_Scenario_Warzone_NPC_SpecOps_D;'
]

SPACECZ_PILOTNAME_CORRESPONDENT = '$LUASC_Scenario_Warzone_NPC_WarzoneCorrespondent;'

CZ_GROUND_LOW_CB_MAX = 5000
CZ_GROUND_MED_CB_MAX = 38000

TW_CBS = {
    25000: 'r',                     # Revenant
    80000: 's',                     # Scout - 80k v18.06
    1000000: 'ba',                  # Banshee
    4500000: 'sg',                  # Scythe and Glaive
    8000000: 'c',                   # Cyclops - 8m v18.06
    24000000: 'b',                  # Basilisk - 24m v18.06
    15000000: 'o',                  # Orthrus - 15m v18.06
    40000000: 'm',                  # Medusa - 40m v18.06
    60000000: 'h'                   # Hydra - 60m v18.06
}


class SystemActivity(dict):
    """
    Utility class for working with system activity. Adds some accessor methods for ease of use.
    """
    def get_trade_profit_total(self):
        try:
            return sum(int(d['profit']) for d in dict.__getitem__(self, 'TradeSell'))
        except KeyError:
            return 0


class Activity:
    """
    User activity for a single tick

    Activity is stored in the self.systems Dict, with key = SystemAddress and value = Dict containing the system name and a Dict of
    factions with their activity
    """

    def __init__(self, bgstally, tick: Tick = None, sample: bool = False, cmdr = None):
        """Constructor

        Args:
            bgstally (BGSTally): The BGSTally object
            tick (Tick, optional): The Tick object to instantiate from. If None, the last known tick is used. Defaults to None.
            sample (bool, optional): Populate with sample data. Defaults to False.
            cmdr (str, optional): The CMDR name. This is not done properly (yet) - the cmdr name is simply updated often to be the latest cmdr seen.
        """
        self.bgstally = bgstally
        if tick == None: tick = Tick(self.bgstally)

        # Stored data. Remember to modify __deepcopy__(), _as_dict() and _from_dict() if these are changed or new data added.
        self.tick_id: str = tick.tick_id
        self.tick_time: datetime = tick.tick_time
        self.tick_forced: bool = False
        self.discord_webhook_data:dict = {} # key = webhook uuid, value = dict containing webhook data
        self.discord_notes: str = ""
        self.dirty: bool = False

        self.cmdr: str = cmdr  # Not saved / loaded (yet) because it's not implemented properly

        if sample:
            self.systems: dict = {"Sample System ID": self.get_sample_system_data()}
        else:
            self.systems: dict = {}

        # Non-stored instance data. Remember to modify __deepcopy__() if these are changed or new data added.
        self.megaship_pat:re.Pattern = re.compile("^[a-z]{3}-[0-9]{3} ")  # e.g. kar-314 aquarius-class tanker


    def load_legacy_data(self, filepath: str):
        """
        Load and populate from a legacy (v1) data structure - i.e. the old Today Data.txt and Yesterday Data.txt files
        """
        # Convert:
        # {"1": [{"System": "Sowiio", "SystemAddress": 1458376217306, "Factions": [{}, {}], "zero_system_activity": false}]}
        # To:
        # {"tick_id": tick_id, "tick_time": tick_time, "discord_messageid": discordmessageid, "systems": {1458376217306: {"System": "Sowiio", "SystemAddress": 1458376217306, "zero_system_activity": false, "Factions": {"Faction Name 1": {}, "Faction Name 2": {}}}}}
        self.dirty = True
        with open(filepath) as legacyactivityfile:
            legacydata = json.load(legacyactivityfile)
            for legacysystemlist in legacydata.values():        # Iterate the values of the dict. We don't care about the keys - they were just "1", "2" etc.
                legacysystem = legacysystemlist[0]              # For some reason each system was a list, but always had just 1 entry
                if 'SystemAddress' in legacysystem:
                    factions = {}
                    for faction in legacysystem['Factions']:
                        factions[faction['Faction']] = faction  # Just convert List to Dict, with faction name as key

                    self.systems[str(legacysystem['SystemAddress'])] = self._get_new_system_data(legacysystem['System'], str(legacysystem['SystemAddress']), factions)
            self.recalculate_zero_activity()


    def load(self, filepath: str):
        """
        Load an activity file
        """
        try:
            with open(filepath) as activityfile:
                self._from_dict(json.load(activityfile))
                self.recalculate_zero_activity()
        except Exception as e:
            Debug.logger.info(f"Unable to load {filepath}")


    def save(self, filepath: str):
        """
        Save to an activity file
        """
        if not self.dirty: return

        with open(filepath, 'w') as activityfile:
            json.dump(self._as_dict(), activityfile)
            self.dirty = False


    def get_filename(self) -> str:
        """
        Return the filename for this Activity
        """
        return self.tick_id + FILE_SUFFIX


    def get_title(self, discord:bool = False) -> str:
        """
        Get the title for this activity
        """
        if self.tick_forced:
            return f"{str(self.tick_time.strftime(DATETIME_FORMAT_TITLE))} (" + (__("forced", lang=self.bgstally.state.discord_lang) if discord else _("forced")) + ")" # LANG: Appended to tick time if a forced tick
        else:
            return f"{str(self.tick_time.strftime(DATETIME_FORMAT_TITLE))} (" + (__("game", lang=self.bgstally.state.discord_lang) if discord else _("game")) + ")" # LANG: Appended to tick time if a normal tick


    def get_ordered_systems(self) -> list:
        """
        Get an ordered list of the systems we are tracking, with the current system first, followed by those with activity, and finally those without
        """
        return sorted(self.systems.keys(), key=lambda x: (str(x) != self.bgstally.state.current_system_id, self.systems[x]['zero_system_activity'], self.systems[x]['System']))


    def get_ordered_factions(self, factions: dict) -> list:
        """Return the provided factions (values from the dict) as a list, ordered by influence highest first

        Args:
            factions (dict): A dict containing the factions to order

        Returns:
            list: An ordered list of factions
        """
        return sorted(factions.values(), key = lambda x: x['Influence'], reverse = True)


    def get_current_system(self) -> dict | None:
        """
        Get the data for the current system
        """
        return self.systems.get(self.bgstally.state.current_system_id)


    def get_system_by_name(self, system_name:str) -> dict | None:
        """
        Retrieve the data for a system by its name, or None if system not found
        """
        for system in self.systems.values():
            if system['System'] == system_name: return system

        return None


    def get_system_by_address(self, system_address:str) -> dict | None:
        """
        Retrieve the data for a system by its address, or None if system not found
        """
        return self.systems.get(system_address, None)


    def get_pinned_systems(self) -> list:
        """
        Retrieve a list of all system names that are currently pinned to the overlay

        Returns:
            list | None: List of system names
        """
        result:list = []

        for system in self.systems.values():
            if system.get('PinToOverlay') == CheckStates.STATE_ON and not system.get('zero_system_activity'):
                result.append(system.get('System'))

        result.sort()
        return result


    def clear_activity(self, mission_log: MissionLog):
        """
        Clear down all activity. If there is a currently active mission in a system or it's the current system the player is in,
        or the system has had search and rescue items collected there, only zero the activity, otherwise delete the system completely.
        """
        self.dirty = True
        mission_systems = mission_log.get_active_systems()

        # Need to convert keys to list so we can delete as we iterate
        for system_address in list(self.systems.keys()):
            system = self.systems[system_address]
            # Note that the missions log historically stores system name so we check for that, not system address.
            # Potential for very rare bug here for systems with duplicate names.
            if system['System'] in mission_systems or \
                    self.bgstally.state.current_system_id == system_address or \
                    sum(int(d['scooped']) for d in system['TWSandR'].values()) > 0:
                # The system has a current mission, or it's the current system, or it has TWSandR scoops - zero, don't delete
                for faction_name, faction_data in system['Factions'].items():
                    system['Factions'][faction_name] = self._get_new_faction_data(faction_name, faction_data['FactionState'], faction_data['Influence'])
                system['TWKills'] = self._get_new_tw_kills_data()
                # Note: system['TWSandR'] scooped data is carried forward, delivered data is cleared
                for d in system['TWSandR'].values():
                    d['delivered'] = 0
            else:
                # Delete the whole system
                del self.systems[system_address]


    #
    # Player Journal Log Handling
    #

    def system_entered(self, journal_entry: dict, state: State):
        """
        The user has entered a system
        """
        # Protect against rare case of null data, not able to trace how this can happen
        if journal_entry.get('SystemAddress') == None or journal_entry.get('StarSystem') == None: return

        self.dirty = True
        current_system = None

        for system_address in self.systems:
            if system_address == str(journal_entry['SystemAddress']):
                # We already have an entry for this system
                current_system = self.systems[system_address]
                break

        if current_system is None:
            # We don't have this system yet
            current_system = self._get_new_system_data(journal_entry['StarSystem'], journal_entry['SystemAddress'], {})
            self.systems[str(journal_entry['SystemAddress'])] = current_system

        self._update_system_data(current_system)

        if 'Factions' in journal_entry:
            for faction in journal_entry['Factions']:
                if faction['Name'] == "Pilots' Federation Local Branch": continue

                # Ignore conflict states in FactionState as we can't trust they always come in pairs. We deal with conflicts separately below.
                faction_state: str = faction['FactionState'] if faction['FactionState'] not in STATES_WAR and faction['FactionState'] not in STATES_ELECTION else "None"
                faction_inf: float = faction['Influence']

                if faction['Name'] in current_system['Factions']:
                    # We have this faction, ensure it's up to date with latest state
                    faction_data = current_system['Factions'][faction['Name']]
                    self._update_faction_data(faction_data, faction_state, faction_inf)
                else:
                    # We do not have this faction, create a new clean entry
                    current_system['Factions'][faction['Name']] = self._get_new_faction_data(faction['Name'], faction_state, faction_inf)

            # Set war states for pairs of factions in War / Civil War / Elections
            for conflict in journal_entry.get('Conflicts', []):
                if conflict['Status'] != "active": continue
                faction_1:str = conflict['Faction1']['Name']
                faction_2:str = conflict['Faction2']['Name']

                if faction_1 in current_system['Factions'] and faction_2 in current_system['Factions']:
                    conflict_state = "War" if conflict['WarType'] == "war" else "CivilWar" if conflict['WarType'] == "civilwar" else "Election" if conflict['WarType'] == "election" else "None"
                    current_system['Factions'][faction_1]['FactionState'] = conflict_state
                    current_system['Factions'][faction_1]['Opponent'] = faction_2
                    current_system['Factions'][faction_2]['FactionState'] = conflict_state
                    current_system['Factions'][faction_2]['Opponent'] = faction_1

        # System tick handling
        system_tick: str = current_system.get('TickTime')
        system_tick_datetime: datetime|None = datetime.strptime(system_tick, DATETIME_FORMAT_ACTIVITY) if system_tick is not None and system_tick != "" else None
        if system_tick_datetime is not None:
            system_tick_datetime = system_tick_datetime.replace(tzinfo=UTC)
            if system_tick_datetime < self.bgstally.tick.tick_time:
                # System tick is older than the current tick, fetch it
                self.bgstally.tick.fetch_system_tick(str(current_system['SystemAddress']))

        self.recalculate_zero_activity()
        state.current_system_id = str(current_system['SystemAddress'])
        current_system['tw_status'] = journal_entry.get('ThargoidWar', None)


    def mission_completed(self, journal_entry: dict, mission_log: MissionLog):
        """
        Handle mission completed
        """
        self.dirty = True
        mission:dict = mission_log.get_mission(journal_entry['MissionID'])

        # BGS
        for faction_effect in journal_entry['FactionEffects']:
            effect_faction_name:str = faction_effect['Faction']
            if effect_faction_name is None or effect_faction_name == "":
                # A game bug means Faction can sometimes be an empty string in FactionEffects.
                # Use the TargetFaction stored from the original MissionAccepted event in this case
                effect_faction_name = mission.get('TargetFaction', "")

            if faction_effect['Influence'] != []:
                inf_index: str = str(len(faction_effect['Influence'][0]['Influence'])) # Index into dict containing detailed INF breakdown
                inftrend = faction_effect['Influence'][0]['Trend']
                for system_address, system in self.systems.items():
                    if str(faction_effect['Influence'][0]['SystemAddress']) != system_address: continue

                    faction = system['Factions'].get(effect_faction_name)
                    if not faction: continue

                    if inftrend == "UpGood" or inftrend == "DownGood":
                        if effect_faction_name == journal_entry['Faction']:
                            faction['MissionPoints'][inf_index] += 1
                            self.bgstally.ui.show_system_report(system_address) # Only show system report for primary INF
                        else:
                            faction['MissionPointsSecondary'][inf_index] += 1
                    else:
                        if effect_faction_name == journal_entry['Faction']:
                            faction['MissionPoints'][inf_index] -= 1
                            self.bgstally.ui.show_system_report(system_address) # Only show system report for primary INF
                        else:
                            faction['MissionPointsSecondary'][inf_index] -= 1

            elif mission is not None:  # No influence specified for faction effect
                for system_address, system in self.systems.items():
                    if mission['System'] != system['System']: continue

                    faction = system['Factions'].get(effect_faction_name)
                    if not faction: continue

                    if effect_faction_name == journal_entry['Faction']:
                        inf_index: str|None = None

                        if faction['FactionState'] in STATES_ELECTION and journal_entry['Name'] in MISSIONS_ELECTION:
                            inf_index = 1 # Default to +1 INF for election missions
                        elif faction['FactionState'] in STATES_WAR and journal_entry['Name'] in MISSIONS_WAR:
                            inf_index = 2 # Default to +2 INF for war missions

                        if inf_index is not None:
                            faction['MissionPoints'][inf_index] += 1
                            self.bgstally.ui.show_system_report(system_address) # Only show system report for primary INF

        # Thargoid War
        if journal_entry['Name'] in MISSIONS_TW_COLLECT + MISSIONS_TW_EVAC_LOW + MISSIONS_TW_EVAC_MED + MISSIONS_TW_EVAC_HIGH + MISSIONS_TW_MASSACRE + MISSIONS_TW_REACTIVATE and mission is not None:
            mission_station = mission.get('Station', "")
            if mission_station != "":
                for system_address, system in self.systems.items():
                    if mission['System'] != system['System']: continue
                    faction = system['Factions'].get(journal_entry['Faction'])
                    if not faction: continue

                    tw_stations = faction['TWStations']
                    if mission_station not in tw_stations:
                        tw_stations[mission_station] = self._get_new_tw_station_data(mission_station)

                    if journal_entry['Name'] in MISSIONS_TW_REACTIVATE:
                        self.bgstally.ui.show_system_report(system_address)

                        # This tracking is unusual - we track BOTH against the station where the mission was completed AND the system where the settlement was reactivated
                        tw_stations[mission_station]['reactivate'] += 1
                        destination_system = self.get_system_by_name(mission['DestinationSystem'])
                        if destination_system is not None:
                            destination_system['TWReactivate'] += 1
                    elif mission.get('PassengerCount', -1) > -1:
                        self.bgstally.ui.show_system_report(system_address)

                        if journal_entry['Name'] in MISSIONS_TW_EVAC_LOW:
                            tw_stations[mission_station]['passengers']['l']['count'] += 1
                            tw_stations[mission_station]['passengers']['l']['sum'] += mission.get('PassengerCount', -1)
                        elif journal_entry['Name'] in MISSIONS_TW_EVAC_MED:
                            tw_stations[mission_station]['passengers']['m']['count'] += 1
                            tw_stations[mission_station]['passengers']['m']['sum'] += mission.get('PassengerCount', -1)
                        elif journal_entry['Name'] in MISSIONS_TW_EVAC_HIGH:
                            tw_stations[mission_station]['passengers']['h']['count'] += 1
                            tw_stations[mission_station]['passengers']['h']['sum'] += mission.get('PassengerCount', -1)
                    elif mission.get('CommodityCount', -1) > -1:
                        self.bgstally.ui.show_system_report(system_address)

                        match journal_entry.get('Commodity'):
                            case "$OccupiedCryoPod_Name;":
                                if journal_entry['Name'] in MISSIONS_TW_EVAC_LOW:
                                    tw_stations[mission_station]['escapepods']['l']['count'] += 1
                                    tw_stations[mission_station]['escapepods']['l']['sum'] += mission.get('CommodityCount', -1)
                                elif journal_entry['Name'] in MISSIONS_TW_EVAC_MED:
                                    tw_stations[mission_station]['escapepods']['m']['count'] += 1
                                    tw_stations[mission_station]['escapepods']['m']['sum'] += mission.get('CommodityCount', -1)
                                elif journal_entry['Name'] in MISSIONS_TW_EVAC_HIGH:
                                    tw_stations[mission_station]['escapepods']['h']['count'] += 1
                                    tw_stations[mission_station]['escapepods']['h']['sum'] += mission.get('CommodityCount', -1)
                            case _:
                                tw_stations[mission_station]['cargo']['count'] += 1
                                tw_stations[mission_station]['cargo']['sum'] += mission.get('CommodityCount', -1)
                    elif mission.get('KillCount', -1) > -1:
                        self.bgstally.ui.show_system_report(system_address)

                        match journal_entry.get('TargetType'):
                            case "$MissionUtil_FactionTag_Scout;":
                                tw_stations[mission_station]['massacre']['s']['count'] += 1
                                tw_stations[mission_station]['massacre']['s']['sum'] += mission.get('KillCount', -1)
                            case "$MissionUtil_FactionTag_Cyclops;":
                                tw_stations[mission_station]['massacre']['c']['count'] += 1
                                tw_stations[mission_station]['massacre']['c']['sum'] += mission.get('KillCount', -1)
                            case "$MissionUtil_FactionTag_Basilisk;":
                                tw_stations[mission_station]['massacre']['b']['count'] += 1
                                tw_stations[mission_station]['massacre']['b']['sum'] += mission.get('KillCount', -1)
                            case "$MissionUtil_FactionTag_Medusa;":
                                tw_stations[mission_station]['massacre']['m']['count'] += 1
                                tw_stations[mission_station]['massacre']['m']['sum'] += mission.get('KillCount', -1)
                            case "$MissionUtil_FactionTag_Hydra;":
                                tw_stations[mission_station]['massacre']['h']['count'] += 1
                                tw_stations[mission_station]['massacre']['h']['sum'] += mission.get('KillCount', -1)
                            case "$MissionUtil_FactionTag_Orthrus;":
                                tw_stations[mission_station]['massacre']['o']['count'] += 1
                                tw_stations[mission_station]['massacre']['o']['sum'] += mission.get('KillCount', -1)

        self.recalculate_zero_activity()
        mission_log.delete_mission_by_id(journal_entry['MissionID'])


    def mission_failed(self, journal_entry: dict, mission_log: MissionLog):
        """
        Handle mission failed
        """
        mission:dict = mission_log.get_mission(journal_entry['MissionID'])
        if mission is None: return
        self.dirty = True

        for system in self.systems.values():
            if mission['System'] != system['System']: continue

            self.bgstally.ui.show_system_report(system['SystemAddress'])

            faction = system['Factions'].get(mission['Faction'])
            if faction: faction['MissionFailed'] += 1

            mission_log.delete_mission_by_id(mission['MissionID'])
            self.recalculate_zero_activity()
            break


    def exploration_data_sold(self, journal_entry: Dict, state: State):
        """
        Handle sale of exploration data
        """
        current_system = self.systems.get(state.current_system_id)
        if not current_system: return
        self.dirty = True

        faction = current_system['Factions'].get(state.station_faction)
        if faction:
            self.bgstally.ui.show_system_report(current_system['SystemAddress'])

            base_value:int = journal_entry.get('BaseValue', 0)
            bonus:int = journal_entry.get('Bonus', 0)
            total_earnings:int = journal_entry.get('TotalEarnings', 0)
            if total_earnings < base_value + bonus: total_earnings = base_value + bonus

            faction['CartData'] += total_earnings
            self.recalculate_zero_activity()


    def organic_data_sold(self, journal_entry: Dict, state: State):
        """
        Handle sale of organic data
        """
        current_system = self.systems.get(state.current_system_id)
        if not current_system: return
        self.dirty = True

        faction = current_system['Factions'].get(state.station_faction)
        if faction:
            self.bgstally.ui.show_system_report(current_system['SystemAddress'])

            for e in journal_entry['BioData']:
                faction['ExoData'] += e['Value'] + e['Bonus']
            self.recalculate_zero_activity()


    def bv_received(self, journal_entry: Dict, state: State, cmdr: str):
        """Handle a bounty voucher for a kill

        Args:
            journal_entry (Dict): The journal data
            state (State): The bgstally State object
            cmdr (str): The CMDR name
        """
        current_system: dict = self.systems.get(state.current_system_id)
        if not current_system: return

        # Check whether in megaship scenario for scenario tracking
        if state.last_megaship_approached != {}:
            timedifference: datetime = datetime.strptime(journal_entry['timestamp'], DATETIME_FORMAT_JOURNAL) - datetime.strptime(state.last_megaship_approached['timestamp'], DATETIME_FORMAT_JOURNAL)
            if timedifference > timedelta(minutes=5):
                # Too long since we last entered a megaship scenario, we can't be sure we're fighting at that scenario, clear down
                state.last_megaship_approached = {}
            else:
                # We're within the timeout, refresh timestamp and handle the CB
                state.last_megaship_approached['timestamp'] = journal_entry['timestamp']
                self._bv_megaship_scenario(journal_entry, current_system, state, cmdr)


    def bv_redeemed(self, journal_entry: Dict, state: State):
        """
        Handle redemption of bounty vouchers
        """
        current_system = self.systems.get(state.current_system_id)
        if not current_system: return
        self.dirty = True

        for bv_info in journal_entry['Factions']:
            faction = current_system['Factions'].get(bv_info['Faction'])
            if faction:
                self.bgstally.ui.show_system_report(current_system['SystemAddress'])

                if state.station_type == 'FleetCarrier':
                    faction['Bounties'] += (bv_info['Amount'] / 2)
                else:
                    faction['Bounties'] += bv_info['Amount']
                self.recalculate_zero_activity()


    def cb_received(self, journal_entry: dict, state: State, cmdr: str):
        """Handle a combat bond received for a kill

        Args:
            journal_entry (dict): The journal data
            state (State): The bgstally State object
            cmdr (str): The CMDR name
        """
        current_system = self.systems.get(state.current_system_id)
        if not current_system: return

        # Check for Thargoid Kill
        if journal_entry.get('VictimFaction', "").lower() == "$faction_thargoid;":
            self._cb_tw(journal_entry, current_system)
            return

        # Otherwise, must be on-ground or in-space CZ for CB kill tracking
        if state.last_settlement_approached != {}:
            timedifference = datetime.strptime(journal_entry['timestamp'], DATETIME_FORMAT_JOURNAL) - datetime.strptime(state.last_settlement_approached['timestamp'], DATETIME_FORMAT_JOURNAL)
            if timedifference > timedelta(minutes=5):
                # Too long since we last approached a settlement, we can't be sure we're fighting at that settlement, clear down
                state.last_settlement_approached = {}
                # Fall through to check space CZs too
            else:
                # We're within the timeout, refresh timestamp and handle the CB
                state.last_settlement_approached['timestamp'] = journal_entry['timestamp']
                self._cb_ground_cz(journal_entry, current_system, state, cmdr)

        elif state.last_spacecz_approached != {}:
            timedifference = datetime.strptime(journal_entry['timestamp'], DATETIME_FORMAT_JOURNAL) - datetime.strptime(state.last_spacecz_approached['timestamp'], DATETIME_FORMAT_JOURNAL)
            if timedifference > timedelta(minutes=5):
                # Too long since we last entered a space cz, we can't be sure we're fighting at that cz, clear down
                state.last_spacecz_approached = {}
            else:
                # We're within the timeout, refresh timestamp and handle the CB
                state.last_spacecz_approached['timestamp'] = journal_entry['timestamp']
                self._cb_space_cz(journal_entry, current_system, state, cmdr)


    def cb_redeemed(self, journal_entry: Dict, state: State):
        """
        Handle redemption of combat bonds
        """
        current_system = self.systems.get(state.current_system_id)
        if not current_system: return
        self.dirty = True

        faction = current_system['Factions'].get(journal_entry['Faction'])
        if faction:
            self.bgstally.ui.show_system_report(current_system['SystemAddress'])

            faction['CombatBonds'] += journal_entry['Amount']
            self.recalculate_zero_activity()


    def cap_ship_bond_received(self, journal_entry: dict, cmdr: str):
        """Handle a capital ship bond

        Args:
            journal_entry (dict): The journal entry data
        """
        current_system = self.systems.get(self.bgstally.state.current_system_id)
        if not current_system: return

        if self.bgstally.state.last_spacecz_approached != {}:
            faction = current_system['Factions'].get(journal_entry.get('AwardingFaction', ""))
            if not faction: return

            self.dirty = True

            faction['SpaceCZ']['cs'] = int(faction['SpaceCZ'].get('cs', '0')) + 1

            event: dict = {
                'event': ApiSyntheticEvent.CZOBJECTIVE,
                'count': 1,
                'type': ApiSyntheticCZObjectiveType.CAPSHIP,
                'Faction': faction
            }
            self.bgstally.api_manager.send_event(event, self, cmdr)

            self.bgstally.ui.show_system_report(current_system['SystemAddress'])
            self.recalculate_zero_activity()


    def trade_purchased(self, journal_entry:dict, state:State):
        """
        Handle purchase of trade commodities
        """
        current_system = self.systems.get(state.current_system_id)
        if not current_system: return

        faction = current_system['Factions'].get(state.station_faction)
        if faction:
            self.dirty = True
            bracket:int = 0

            self.bgstally.ui.show_system_report(current_system['SystemAddress'])

            if self.bgstally.market.available(journal_entry['MarketID']):
                market_data:dict = self.bgstally.market.get_commodity(journal_entry['Type'])
                bracket = market_data.get('StockBracket', 0)

            faction['TradeBuy'][bracket]['value'] += journal_entry['TotalCost']
            faction['TradeBuy'][bracket]['items'] += journal_entry['Count']

            self.recalculate_zero_activity()


    def trade_sold(self, journal_entry:dict, state:State):
        """
        Handle sale of trade commodities
        """
        current_system = self.systems.get(state.current_system_id)
        if not current_system: return

        # Handle SandR tissue samples first
        cargo_type:str = journal_entry.get('Type', "").lower()
        if 'thargoidtissuesample' in cargo_type or 'thargoidscouttissuesample' in cargo_type:
            self._tw_sandr_handin('t', journal_entry.get('Count', 0), True)
            # Fall through to BGS tracking for standard trade sale

        faction = current_system['Factions'].get(state.station_faction)
        if faction:
            self.dirty = True
            cost:int = journal_entry['Count'] * journal_entry['AvgPricePaid']
            profit:int = journal_entry['TotalSale'] - cost
            bracket:int = 0

            self.bgstally.ui.show_system_report(current_system['SystemAddress'])

            if journal_entry.get('BlackMarket', False):
                faction['BlackMarketProfit'] += profit
            else:
                if self.bgstally.market.available(journal_entry['MarketID']):
                    market_data:dict = self.bgstally.market.get_commodity(journal_entry['Type'])
                    bracket = market_data.get('DemandBracket', 0)

                faction['TradeSell'][bracket]['profit'] += profit
                faction['TradeSell'][bracket]['value'] += journal_entry['TotalSale']
                faction['TradeSell'][bracket]['items'] += journal_entry['Count']

            self.recalculate_zero_activity()


    def ship_targeted(self, journal_entry: dict, state: State):
        """
        Handle targeting a ship
        """
        # Always clear last targeted on new target lock
        if journal_entry.get('TargetLocked', False) == True:
            state.last_ship_targeted = {}

        if 'Faction' in journal_entry and 'PilotName_Localised' in journal_entry and 'PilotName' in journal_entry:
            # Store info on targeted ship
            self.dirty = True
            state.last_ship_targeted = {'Faction': journal_entry['Faction'],
                                        'PilotName': journal_entry['PilotName'],
                                        'PilotName_Localised': journal_entry['PilotName_Localised']}

            if journal_entry['PilotName'].startswith("$ShipName_Police"):
                state.last_ships_targeted[journal_entry['PilotName']] = state.last_ship_targeted
            else:
                state.last_ships_targeted[journal_entry['PilotName_Localised']] = state.last_ship_targeted

        if 'Faction' in journal_entry and state.last_spacecz_approached != {} and state.last_spacecz_approached.get('ally_faction') is not None:
            # In space CZ, check we're targeting the right faction
            if journal_entry.get('Faction', "") == state.last_spacecz_approached.get('ally_faction', ""):
                self.bgstally.ui.show_warning(_("Targeted Ally!")) # LANG: Overlay message


    def crime_committed(self, journal_entry: dict, state: State):
        """
        Handle a crime
        """
        current_system: dict|None = self.systems.get(state.current_system_id)
        if not current_system: return
        self.dirty = True

        # For in-space murders, the faction logged in the CommitCrime event is the system faction,
        # not the ship faction. We need to log the murder against the ship faction, so we store
        # it from the previous ShipTargeted event in last_ships_targeted. Need to keep a dict of all
        # previously targeted ships because of a game bug where the logged murdered ship may not be the
        # last target logged.

        match journal_entry['CrimeType']:
            case 'murder':
                # For ship murders, if we didn't get a previous scan containing ship faction, don't log
                ship_target_info: dict = state.last_ships_targeted.pop(journal_entry.get('Victim'), None)
                if ship_target_info is None: return
                faction = current_system['Factions'].get(ship_target_info.get('Faction'))

                if faction:
                    faction['Murdered'] += 1
                    self.recalculate_zero_activity()

                    self.bgstally.ui.show_system_report(current_system['SystemAddress'])

            case 'onFoot_murder':
                # For on-foot murders, get the faction from the journal entry
                faction = current_system['Factions'].get(journal_entry['Faction'])
                if faction:
                    faction['GroundMurdered'] += 1
                    self.recalculate_zero_activity()

                    self.bgstally.ui.show_system_report(current_system['SystemAddress'])


    def cargo(self, journal_entry: dict):
        """
        Handle Cargo status
        """
        if journal_entry.get('Vessel') == "Ship" and journal_entry.get('Count', 0) == 0:
            self._tw_sandr_clear_all_scooped()


    def cargo_collected(self, journal_entry: dict, state: State):
        """
        Handle cargo collection for certain cargo types
        """
        current_system = self.systems.get(state.current_system_id)
        if not current_system: return
        if current_system.get('tw_status') is None: return # Do not track TW cargo collection in non TW systems

        key:str = None

        match journal_entry.get('Type', "").lower():
            case 'damagedescapepod': key = 'dp'
            case 'occupiedcryopod': key = 'op'
            case 'thargoidpod': key = 'tp'
            case 'usscargoblackbox': key = 'bb'
            case _ as cargo_type if "thargoidtissuesample" in cargo_type or "thargoidscouttissuesample" in cargo_type: key = 't'

        if key is None: return

        current_system['TWSandR'][key]['scooped'] += 1
        self.dirty = True


    def cargo_ejected(self, journal_entry: dict):
        """
        Handle cargo ejection for certain cargo types
        """
        key:str = None

        match journal_entry.get('Type', "").lower():
            case 'damagedescapepod': key = 'dp'
            case 'occupiedcryopod': key = 'op'
            case 'thargoidpod': key = 'tp'
            case 'usscargoblackbox': key = 'bb'
            case _ as cargo_type if "thargoidtissuesample" in cargo_type or "thargoidscouttissuesample" in cargo_type: key = 't'

        if key is None: return

        self._tw_sandr_handin(key, journal_entry.get('Count', 0), False)


    def search_and_rescue(self, journal_entry: dict, state: State):
        """
        Handle search and rescue hand-in.
        """
        current_system: dict = self.systems.get(state.current_system_id)
        if not current_system: return
        count: int = int(journal_entry.get('Count', 0))
        if count == 0: return

        key: str = None
        tw: bool = False

        match journal_entry.get('Name', "").lower():
            # There is no TW tissue sample tracking here as those are treated a commodities
            case 'damagedescapepod': key = 'dp'; tw = True
            case 'occupiedcryopod': key = 'op'; tw = True
            case 'thargoidpod': key = 'tp'; tw = True
            case 'usscargoblackbox': key = 'bb'; tw = True
            case 'wreckagecomponents': key = 'wc'
            case 'personaleffects': key = 'pe'
            case 'politicalprisoner': key = 'pp'
            case 'hostage': key = 'h'

        if key is None: return

        # Handle BGS S&R
        # This is counted for the controlling faction at the station handed in. Note that if the S&R items originated in a TW
        # system, they will be counted for both BGS and TW

        faction = current_system['Factions'].get(state.station_faction)
        if faction:
            self.dirty = True
            self.bgstally.ui.show_system_report(current_system['SystemAddress'])

            faction['SandR'][key] += count
            self.recalculate_zero_activity()

        # Handle TW S&R
        if not tw: return
        self._tw_sandr_handin(key, count, True)


    def player_resurrected(self):
        """
        Clear down any logged S&R cargo on resurrect
        """
        self._tw_sandr_clear_all_scooped()


    def supercruise(self, journal_entry: dict, state:State):
        """Enter supercruise

        Args:
            journal_entry (dict): The journal entry
        """
        state.last_settlement_approached = {}
        state.last_spacecz_approached = {}
        state.last_megaship_approached = {}


    def settlement_approached(self, journal_entry: dict, state:State):
        """
        Handle approaching a settlement
        """
        state.last_settlement_approached = {'timestamp': journal_entry['timestamp'], 'name': journal_entry['Name'], 'size': None}
        state.last_spacecz_approached = {}
        state.last_megaship_approached = {}


    def destination_dropped(self, journal_entry: dict, state: State):
        """
        Handle drop at a supercruise destination
        """
        current_system = self.systems.get(state.current_system_id)
        if not current_system: return

        match journal_entry.get('Type', "").lower():
            case type if type.startswith("$warzone_pointrace_low"):
                state.last_spacecz_approached = {'timestamp': journal_entry['timestamp'], 'type': 'l', 'counted': False}
                state.last_settlement_approached = {}
                state.last_megaship_approached = {}
            case type if type.startswith("$warzone_pointrace_med"):
                state.last_spacecz_approached = {'timestamp': journal_entry['timestamp'], 'type': 'm', 'counted': False}
                state.last_settlement_approached = {}
                state.last_megaship_approached = {}
            case type if type.startswith("$warzone_pointrace_high"):
                state.last_spacecz_approached = {'timestamp': journal_entry['timestamp'], 'type': 'h', 'counted': False}
                state.last_settlement_approached = {}
                state.last_megaship_approached = {}
            case type if self.megaship_pat.match(type):
                state.last_megaship_approached = {'timestamp': journal_entry['timestamp'], 'counted': False}
                state.last_spacecz_approached = {}
                state.last_settlement_approached = {}


    def recalculate_zero_activity(self):
        """
        For efficiency at display time, we store whether each system has had any activity in the data structure
        """
        for system in self.systems.values():
            self._update_system_data(system)
            system['zero_system_activity'] = True

            for faction_data in system['Factions'].values():
                self._update_faction_data(faction_data)
                if not self._is_faction_data_zero(faction_data):
                    system['zero_system_activity'] = False

            if system['zero_system_activity'] == False: continue

            if sum(system['TWKills'].values()) > 0: system['zero_system_activity'] = False

            if system['zero_system_activity'] == False: continue

            if sum(int(d['delivered']) for d in system['TWSandR'].values()) > 0: system['zero_system_activity'] = False

            if system['zero_system_activity'] == False: continue


    #
    # Private functions
    #

    def _cb_tw(self, journal_entry:dict, current_system:dict):
        """
        We are logging a Thargoid kill
        """
        tw_ship:str = TW_CBS.get(journal_entry.get('Reward', 0))
        if tw_ship: current_system['TWKills'][tw_ship] = current_system['TWKills'].get(tw_ship, 0) + 1

        self.bgstally.ui.show_system_report(current_system['SystemAddress'])


    def _cb_ground_cz(self, journal_entry: dict, current_system: dict, state: State, cmdr: str):
        """Combat bond received while we are in an active ground CZ

        Args:
            journal_entry (dict): The journal entry data
            current_system (dict): The current system data
            state (State): The bgstally State object
            cmdr (str): The CMDR name
        """
        faction_name: str = journal_entry.get('AwardingFaction', "")
        faction: dict = current_system['Factions'].get(faction_name)
        if not faction: return

        self.dirty = True

        self.bgstally.ui.show_system_report(current_system['SystemAddress'])

        # Add settlement to this faction's list, if not already present
        if state.last_settlement_approached['name'] not in faction['GroundCZSettlements']:
            faction['GroundCZSettlements'][state.last_settlement_approached['name']] = self._get_new_groundcz_settlement_data()

        # Store the previously counted size of this settlement
        previous_size: str = state.last_settlement_approached['size']

        # Increment this settlement's overall count if this is the first bond counted
        if state.last_settlement_approached['size'] == None:
            faction['GroundCZSettlements'][state.last_settlement_approached['name']]['count'] += 1

        # Calculate and count CZ H/M/L - Note this isn't ideal as it counts on any kill, assuming we'll win the CZ! Also note that we re-calculate on every
        # kill because when a kill is made my multiple players in a team, the CBs are split. We just hope that at some point we'll make a solo kill which will
        # put this settlement into the correct CZ size category
        if journal_entry['Reward'] < CZ_GROUND_LOW_CB_MAX:
            # Handle as 'Low' if this is the first CB
            if state.last_settlement_approached['size'] == None:
                # Increment overall 'Low' count for this faction
                faction['GroundCZ']['l'] = int(faction['GroundCZ'].get('l', '0')) + 1
                # Set faction settlement type
                faction['GroundCZSettlements'][state.last_settlement_approached['name']]['type'] = 'l'
                # Store last settlement type
                state.last_settlement_approached['size'] = 'l'

                # Send to API
                event: dict = {
                    'event': ApiSyntheticEvent.GROUNDCZ,
                    'low': 1,
                    'settlement': state.last_settlement_approached['name'],
                    'Faction': faction_name
                }
                self.bgstally.api_manager.send_event(event, self, cmdr)

        elif journal_entry['Reward'] < CZ_GROUND_MED_CB_MAX:
            # Handle as 'Med' if this is either the first CB or we've counted this settlement as a 'Low' before
            if state.last_settlement_approached['size'] == None or state.last_settlement_approached['size'] == 'l':
                # Increment overall 'Med' count for this faction
                faction['GroundCZ']['m'] = int(faction['GroundCZ'].get('m', '0')) + 1
                # Decrement overall previous size count if we previously counted it
                if previous_size != None: faction['GroundCZ'][previous_size] = int(faction['GroundCZ'].get(previous_size, '0')) - 1
                # Set faction settlement type
                faction['GroundCZSettlements'][state.last_settlement_approached['name']]['type'] = 'm'
                # Store last settlement type
                state.last_settlement_approached['size'] = 'm'

                # Send to API
                event: dict = {
                    'event': ApiSyntheticEvent.GROUNDCZ,
                    'medium': 1,
                    'settlement': state.last_settlement_approached['name'],
                    'Faction': faction_name
                }
                if previous_size != None: event[ApiSizeLookup[previous_size]] = -1
                self.bgstally.api_manager.send_event(event, self, cmdr)
        else:
            # Handle as 'High' if this is either the first CB or we've counted this settlement as a 'Low' or 'Med' before
            if state.last_settlement_approached['size'] == None or state.last_settlement_approached['size'] == 'l' or state.last_settlement_approached['size'] == 'm':
                # Increment overall 'High' count for this faction
                faction['GroundCZ']['h'] = int(faction['GroundCZ'].get('h', '0')) + 1
                # Decrement overall previous size count if we previously counted it
                if previous_size != None: faction['GroundCZ'][previous_size] = int(faction['GroundCZ'].get(previous_size, '0')) - 1
                # Set faction settlement type
                faction['GroundCZSettlements'][state.last_settlement_approached['name']]['type'] = 'h'
                # Store last settlement type
                state.last_settlement_approached['size'] = 'h'

                # Send to API
                event: dict = {
                    'event': ApiSyntheticEvent.GROUNDCZ,
                    'high': 1,
                    'settlement': state.last_settlement_approached['name'],
                    'Faction': faction_name
                }
                if previous_size != None: event[ApiSizeLookup[previous_size]] = -1
                self.bgstally.api_manager.send_event(event, self, cmdr)

        self.recalculate_zero_activity()


    def _cb_space_cz(self, journal_entry: dict, current_system: dict, state: State, cmdr: str):
        """Combat bond received while we are in an active space CZ

        Args:
            journal_entry (dict): The journal entry data
            current_system (dict): The current system data
            state (State): The bgstally state object
            cmdr (str): The CMDR name
        """

        faction_name: str = journal_entry.get('AwardingFaction', "")
        faction: dict = current_system['Factions'].get(faction_name)
        if not faction: return

        # Check for side objectives detected by CBs
        if state.last_ship_targeted != {} and journal_entry.get('VictimFaction') != state.last_spacecz_approached.get('ally_faction'):
            if state.last_ship_targeted.get('PilotName', "") in SPACECZ_PILOTNAMES_CAPTAIN and not state.last_spacecz_approached.get('capt'):
                # Tally a captain kill. Unreliable because of journal order unpredictability.
                state.last_spacecz_approached['capt'] = True
                faction['SpaceCZ']['cp'] = int(faction['SpaceCZ'].get('cp', '0')) + 1

                # Send to API
                event: dict = {
                    'event': ApiSyntheticEvent.CZOBJECTIVE,
                    'count': 1,
                    'type': ApiSyntheticCZObjectiveType.GENERAL,
                    'Faction': faction_name
                }
                self.bgstally.api_manager.send_event(event, self, cmdr)

                self.bgstally.ui.show_system_report(current_system['SystemAddress'])
            elif state.last_ship_targeted.get('PilotName', "") in SPACECZ_PILOTNAMES_SPECOPS and not state.last_spacecz_approached.get('specops'):
                # Tally a specops kill. We would like to only tally this after 4 kills in a CZ, but sadly due to journal order
                # unpredictability we tally as soon as we spot a kill after targeting a spec ops
                state.last_spacecz_approached['specops'] = True
                faction['SpaceCZ']['so'] = int(faction['SpaceCZ'].get('so', '0')) + 1

                # Send to API
                event: dict = {
                    'event': ApiSyntheticEvent.CZOBJECTIVE,
                    'count': 1,
                    'type': ApiSyntheticCZObjectiveType.SPECOPS,
                    'Faction': faction_name
                }
                self.bgstally.api_manager.send_event(event, self, cmdr)

                self.bgstally.ui.show_system_report(current_system['SystemAddress'])
            elif state.last_ship_targeted.get('PilotName', "") == SPACECZ_PILOTNAME_CORRESPONDENT and not state.last_spacecz_approached.get('propagand'):
                # Tally a propagandist kill. We would like to only tally this after 3 kills in a CZ, but sadly due to journal order
                # unpredictability we tally as soon as we spot a kill after targeting a propagandist
                state.last_spacecz_approached['propagand'] = True
                faction['SpaceCZ']['pr'] = int(faction['SpaceCZ'].get('pr', '0')) + 1

                # Send to API
                event: dict = {
                    'event': ApiSyntheticEvent.CZOBJECTIVE,
                    'count': 1,
                    'type': ApiSyntheticCZObjectiveType.CORRESPONDENT,
                    'Faction': faction_name
                }
                self.bgstally.api_manager.send_event(event, self, cmdr)

                self.bgstally.ui.show_system_report(current_system['SystemAddress'])

        # If we've already counted this CZ, exit
        if state.last_spacecz_approached.get('counted', False): return

        state.last_spacecz_approached['counted'] = True
        state.last_spacecz_approached['ally_faction'] = faction.get('Faction', "")
        self.dirty = True

        type: str = state.last_spacecz_approached.get('type', 'l')
        faction['SpaceCZ'][type] = int(faction['SpaceCZ'].get(type, '0')) + 1

        # Send to API
        event: dict = {
            'event': ApiSyntheticEvent.CZ,
            ApiSizeLookup[type]: 1,
            'Faction': faction_name
        }
        self.bgstally.api_manager.send_event(event, self, cmdr)

        self.bgstally.ui.show_system_report(current_system['SystemAddress'])
        self.recalculate_zero_activity()


    def _bv_megaship_scenario(self, journal_entry: dict, current_system: dict, state: State, cmdr: str):
        """We are in an active megaship scenario

        Args:
            journal_entry (dict): The journal entry data
            current_system (dict): The current system data
            state (State): The bgstally State object
            cmdr (str): The CMDR name
        """
        faction_name: str = journal_entry.get('VictimFaction', "")
        faction: dict = current_system['Factions'].get(faction_name)
        if not faction: return
        opponent_faction_name: str = faction.get('Opponent', "")
        opponent_faction: dict = current_system['Factions'].get(opponent_faction_name)
        if not opponent_faction: return

        # If we've already counted this scenario, exit
        if state.last_megaship_approached.get('counted', False): return

        state.last_megaship_approached['counted'] = True
        self.dirty = True

        # The scenario should be counted against the opponent faction of the ship just killed
        opponent_faction['Scenarios'] += 1

        # Send to API
        event: dict = {
            'event': ApiSyntheticEvent.SCENARIO,
            'type': ApiSyntheticScenarioType.MEGASHIP,
            'count': 1,
            'Faction': opponent_faction_name
        }
        self.bgstally.api_manager.send_event(event, self, cmdr)

        self.bgstally.ui.show_system_report(current_system['SystemAddress'])
        self.recalculate_zero_activity()


    def _tw_sandr_handin(self, key:str, count:int, tally:bool):
        """
        Tally a TW search and rescue handin. These can originate from SearchAndRescue or TradeSell events
        """

        # This can be handed in in any system, but the effect counts for the system the items were collected in. However,
        # we have no way of knowing exactly which items were handed in, so just iterate through all our known systems
        # looking for previously scooped cargo of the correct type.

        for system in self.systems.values():
            if count <= 0: break  # Finish when we've accounted for all items

            allocatable:int = min(count, system['TWSandR'][key]['scooped'])
            if allocatable > 0:
                system['TWSandR'][key]['scooped'] -= allocatable
                if tally: system['TWSandR'][key]['delivered'] += allocatable
                count -= allocatable
                self.dirty = True

                if tally: self.bgstally.ui.show_system_report(system['SystemAddress'])

        # count can end up > 0 here - i.e. more S&R handed in than we originally logged as scooped. Ignore, as we don't know
        # where it originally came from


    def _tw_sandr_clear_all_scooped(self):
        """
        Clear down all TW search and rescue scooped cargo
        """
        for system in self.systems.values():
            system['TWSandR']['dp']['scooped'] = 0
            system['TWSandR']['op']['scooped'] = 0
            system['TWSandR']['tp']['scooped'] = 0
            system['TWSandR']['bb']['scooped'] = 0
            system['TWSandR']['t']['scooped'] = 0

        self.dirty = True


    def get_sample_system_data(self) -> dict:
        """Get sample system data containing every type of activity for preview / demo purposes

        Returns:
            dict: The sample system data
        """
        return {'System': "Sample System Name",
                'SystemAddress': 1,
                'zero_system_activity': False,
                'Factions': {"Sample Faction Name 1": self._get_new_faction_data("Sample Faction Name 1", "None", 40, True),
                             "Sample Faction Name 2": self._get_new_faction_data("Sample Faction Name 2", "None", 30, True),
                             "Sample Faction Name 3": self._get_new_faction_data("Sample Faction Name 3", "None", 30, True)},
                'TWKills': self._get_new_tw_kills_data(True),
                'TWSandR': self._get_new_tw_sandr_data(True),
                'TWReactivate': 5,
                'TickTime': datetime.now(UTC).strftime(DATETIME_FORMAT_ACTIVITY)
                }


    def _get_new_system_data(self, system_name: str, system_address: str, faction_data: dict) -> dict:
        """Get a new data structure for storing system data

        Args:
            system_name (str): The system name
            system_address (str): The system identifying address
            faction_data (dict): The faction data

        Returns:
            dict: The system data
        """
        return {'System': system_name,
                'SystemAddress': system_address,
                'zero_system_activity': True,
                'Factions': faction_data,
                'TWKills': self._get_new_tw_kills_data(),
                'TWSandR': self._get_new_tw_sandr_data(),
                'TWReactivate': 0,
                'TickTime': ""
                }


    def _get_new_faction_data(self, faction_name: str, faction_state: str, faction_inf: float, sample: bool = False) -> dict:
        """Get a new data structure for storing faction data

        Args:
            faction_name (str): The faction name
            faction_state (str): The BGS state of the faction
            sample (bool, optional): Populate with sample data if True. Defaults to False.

        Returns:
            dict: The faction data
        """
        s: bool = sample # Shorter
        return {'Faction': faction_name, 'FactionState': faction_state, 'Influence': faction_inf, 'Enabled': self.bgstally.state.EnableSystemActivityByDefault.get(),
                'MissionPoints': {'1': 3 if s else 0, '2': 4 if s else 0, '3': 5 if s else 0, '4': 6 if s else 0, '5': 7 if s else 0, 'm': 8 if s else 0},
                'MissionPointsSecondary': {'1': 3 if s else 0, '2': 4 if s else 0, '3': 5 if s else 0, '4': 6 if s else 0, '5': 7 if s else 0, 'm': 8 if s else 0},
                'BlackMarketProfit': 50000 if s else 0, 'Bounties': 1000000 if s else 0, 'CartData': 2000000 if s else 0, 'ExoData': 3000000 if s else 0,
                'TradeBuy': [{'items': 100 if s else 0, 'value': 100000 if s else 0}, {'items': 200 if s else 0, 'value': 200000 if s else 0}, {'items': 300 if s else 0, 'value': 300000 if s else 0}, {'items': 400 if s else 0, 'value': 400000 if s else 0}],
                'TradeSell': [{'items': 100 if s else 0, 'value': 100000 if s else 0, 'profit': 1000 if s else 0}, {'items': 200 if s else 0, 'value': 200000 if s else 0, 'profit': 2000 if s else 0}, {'items': 300 if s else 0, 'value': 300000 if s else 0, 'profit': 3000 if s else 0}, {'items': 400 if s else 0, 'value': 400000 if s else 0, 'profit': 4000 if s else 0}],
                'CombatBonds': 1000000 if s else 0, 'MissionFailed': 10 if s else 0, 'Murdered': 30 if s else 0, 'GroundMurdered': 20 if s else 0,
                'SpaceCZ': {'l': 3 if s else 0, 'm': 4 if s else 0, 'h': 5 if s else 0, 'cs': 1 if s else 0, 'cp': 2 if s else 0, 'so': 3 if s else 0, 'pr': 4 if s else 0},
                'GroundCZ': {'l': 3 if s else 0, 'm': 4 if s else 0, 'h': 5 if s else 0},
                'GroundCZSettlements': {"Sample Ground Settlement Name": self._get_new_groundcz_settlement_data('l', s)} if s else {},
                'Scenarios': 5 if s else 0,
                'SandR': {'dp': 3 if s else 0, 'op': 4 if s else 0, 'tp': 5 if s else 0, 'bb': 6 if s else 0, 'wc': 7 if s else 0, 'pe': 8 if s else 0, 'pp': 9 if s else 0, 'h': 10 if s else 0},
                'TWStations': {"Sample Station Name": self._get_new_tw_station_data("Station Name", s)} if s else {}
                }


    def _get_new_tw_station_data(self, station_name: str, sample: bool = False) -> dict:
        """Get a new data structure for storing Thargoid War station data

        Args:
            station_name (str): The station name
            sample (bool, optional): Populate with sample data if True. Defaults to False.

        Returns:
            dict: The thargoid war station data
        """
        s: bool = sample # Shorter
        return {'name': station_name, 'enabled': CheckStates.STATE_ON,
                'passengers': {'l': {'count': 3 if s else 0, 'sum': 30 if s else 0}, 'm': {'count': 4 if s else 0, 'sum': 40 if s else 0}, 'h': {'count': 5 if s else 0, 'sum': 50 if s else 0}},
                'escapepods': {'l': {'count': 3 if s else 0, 'sum': 30 if s else 0}, 'm': {'count': 4 if s else 0, 'sum': 40 if s else 0}, 'h': {'count': 5 if s else 0, 'sum': 50 if s else 0}},
                'cargo': {'count': 3 if s else 0, 'sum': 300 if s else 0},
                'massacre': {'s': {'count': 1 if s else 0, 'sum': 10 if s else 0}, 'c': {'count': 2 if s else 0, 'sum': 20 if s else 0}, 'b': {'count': 3 if s else 0, 'sum': 30 if s else 0}, 'm': {'count': 4 if s else 0, 'sum': 40 if s else 0}, 'h': {'count': 5 if s else 0, 'sum': 50 if s else 0}, 'o': {'count': 6 if s else 0, 'sum': 60 if s else 0}},
                'reactivate': 10 if s else 0}


    def _get_new_tw_kills_data(self, sample: bool = False) -> dict:
        """Get a new data structure for storing Thargoid War Kills

        Args:
            sample (bool, optional): Populate with sample data if True. Defaults to False.

        Returns:
            dict: The thargoid war kills data
        """
        s: bool = sample # Shorter
        return {'r': 1 if s else 0, 's': 2 if s else 0, 'ba': 3 if s else 0, 'sg': 4 if s else 0, 'c': 5 if s else 0, 'b': 6 if s else 0, 'm': 7 if s else 0, 'h': 8 if s else 0, 'o': 9 if s else 0}


    def _get_new_tw_sandr_data(self, sample: bool = False) -> dict:
        """Get a new data structure for storing Thargoid War Search and Rescue

        Args:
            sample (bool, optional): Populate with sample data if True. Defaults to False.

        Returns:
            dict: The thargoid war SandR data
        """
        s: bool = sample # Shorter
        return {
            'dp': {'scooped': 0, 'delivered': 30 if s else 0},
            'op': {'scooped': 0, 'delivered': 40 if s else 0},
            'tp': {'scooped': 0, 'delivered': 50 if s else 0},
            'bb': {'scooped': 0, 'delivered': 60 if s else 0},
            't': {'scooped': 0, 'delivered': 70 if s else 0}}


    def _get_new_groundcz_settlement_data(self, type: str = 'l', sample: bool = False) -> dict:
        """Get a new data structure for a single GroundCZ settlement

        Args:
            type (str, optional): The CZ type. Defaults to 'l'.
            sample (bool, optional): Populate with sample data if True. Defaults to False.

        Returns:
            dict: Settlement data
        """
        s: bool = sample # Shorter
        return {'count': 5 if s else 0, 'enabled': CheckStates.STATE_ON, 'type': type}


    def _update_system_data(self, system_data:dict):
        """
        Update system data structure for elements not present in previous versions of plugin
        """
        # From < v3.1.0 to 3.1.0
        if not 'TWKills' in system_data: system_data['TWKills'] = self._get_new_tw_kills_data()
        if not 'TWSandR' in system_data: system_data['TWSandR'] = self._get_new_tw_sandr_data()
        # From < 3.2.0 to 3.2.0
        if not 'TWReactivate' in system_data: system_data['TWReactivate'] = 0
        # From < 3.6.0 to 3.6.0
        if not 'PinToOverlay' in system_data: system_data['PinToOverlay'] = CheckStates.STATE_OFF
        if not 'tp' in system_data['TWSandR']: system_data['TWSandR']['tp'] = {'scooped': 0, 'delivered': 0}
        # From < 4.3.0 to 4.3.0
        if not 'TickTime' in system_data: system_data['TickTime'] = ""


    def _update_faction_data(self, faction_data: dict, faction_state: str|None = None, faction_inf: float|None = None):
        """
        Update faction data structure for elements not present in previous versions of plugin
        """
        # Update faction state and influence as it can change at any time post-tick
        if faction_state: faction_data['FactionState'] = faction_state
        if faction_inf: faction_data['Influence'] = faction_inf

        # From < v1.2.0 to 1.2.0
        if not 'SpaceCZ' in faction_data: faction_data['SpaceCZ'] = {}
        if not 'GroundCZ' in faction_data: faction_data['GroundCZ'] = {}
        # From < v1.3.0 to 1.3.0
        if not 'Enabled' in faction_data: faction_data['Enabled'] = CheckStates.STATE_ON
        # From < v1.6.0 to 1.6.0
        if not 'MissionPointsSecondary' in faction_data: faction_data['MissionPointsSecondary'] = 0
        # From < v1.7.0 to 1.7.0
        if not 'ExoData' in faction_data: faction_data['ExoData'] = 0
        if not 'GroundCZSettlements' in faction_data: faction_data['GroundCZSettlements'] = {}
        # From < v1.8.0 to 1.8.0
        if not 'BlackMarketProfit' in faction_data: faction_data['BlackMarketProfit'] = 0
        if not 'TradePurchase' in faction_data: faction_data['TradePurchase'] = 0
        # From < v1.9.0 to 1.9.0
        if not 'Scenarios' in faction_data: faction_data['Scenarios'] = 0
        # From < v2.2.0 to 2.2.0
        if not 'TWStations' in faction_data: faction_data['TWStations'] = {}
        # From < 3.0.0 to 3.0.0
        if not 'GroundMurdered' in faction_data: faction_data['GroundMurdered'] = 0
        if not 'TradeBuy' in faction_data:
            faction_data['TradeBuy'] = [{'items': 0, 'value': 0}, {'items': 0, 'value': 0}, {'items': 0, 'value': 0}, {'items': 0, 'value': 0}]
        if not 'TradeSell' in faction_data:
            faction_data['TradeSell'] = [{'items': 0, 'value': 0, 'profit': 0}, {'items': 0, 'value': 0, 'profit': 0}, {'items': 0, 'value': 0, 'profit': 0}, {'items': 0, 'value': 0, 'profit': 0}]
        # From < 3.2.0 to 3.2.0
        for station in faction_data['TWStations'].values():
            if not 'reactivate' in station: station['reactivate'] = 0
        # From < 3.5.0 to 3.5.0
        if not type(faction_data.get('MissionPoints', 0)) == dict:
            faction_data['MissionPoints'] = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0, 'm': int(faction_data.get('MissionPoints', 0))}
        if not type(faction_data.get('MissionPointsSecondary', 0)) == dict:
            faction_data['MissionPointsSecondary'] = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0, 'm': int(faction_data.get('MissionPointsSecondary', 0))}
        # From < 4.0.0 to 4.0.0
        if not 'SandR' in faction_data: faction_data['SandR'] = {'dp': 0, 'op': 0, 'tp': 0, 'bb': 0, 'wc': 0, 'pe': 0, 'pp': 0, 'h': 0}
        # From < 4.2.0 to 4.2.0
        if not 'Influence' in faction_data: faction_data['Influence'] = 0


    def _is_faction_data_zero(self, faction_data: Dict):
        """
        Check whether all information is empty or zero for a faction. _update_faction_data() is always called before this
        so we can always assume here that the data is in the very latest structure.
        """
        return sum((1 if k == 'm' else int(k)) * int(v) for k, v in faction_data['MissionPoints'].items()) == 0 and \
                sum((1 if k == 'm' else int(k)) * int(v) for k, v in faction_data['MissionPointsSecondary'].items()) == 0 and \
                int(faction_data['BlackMarketProfit']) == 0 and \
                sum(int(d['value']) for d in faction_data['TradeBuy']) == 0 and \
                sum(int(d['value']) for d in faction_data['TradeSell']) == 0 and \
                int(faction_data['BlackMarketProfit']) == 0 and \
                int(faction_data['Bounties']) == 0 and int(faction_data['CartData']) == 0 and int(faction_data['ExoData']) == 0 and \
                int(faction_data['CombatBonds']) == 0 and int(faction_data['MissionFailed']) == 0 and int(faction_data['Murdered']) == 0 and int(faction_data['GroundMurdered']) == 0 and \
                sum(faction_data.get('SpaceCZ', {}).values()) == 0 and \
                (faction_data['GroundCZ'] == {} or (int(faction_data['GroundCZ'].get('l', 0)) == 0 and int(faction_data['GroundCZ'].get('m', 0)) == 0 and int(faction_data['GroundCZ'].get('h', 0)) == 0)) and \
                faction_data['GroundCZSettlements'] == {} and \
                int(faction_data['Scenarios']) == 0 and \
                sum(faction_data.get('SandR', {}).values()) == 0 and \
                faction_data['TWStations'] == {}


    def _as_dict(self):
        """
        Return a Dictionary representation of our data, suitable for serializing
        """
        return {
            'tickid': self.tick_id,
            'ticktime': self.tick_time.strftime(DATETIME_FORMAT_ACTIVITY),
            'tickforced': self.tick_forced,
            'discordwebhookdata': self.discord_webhook_data,
            'discordnotes': self.discord_notes,
            'systems': self.systems}


    def _from_dict(self, dict: Dict):
        """
        Populate our data from a Dictionary that has been deserialized
        """
        self.tick_id = dict.get('tickid')
        self.tick_time = datetime.strptime(dict.get('ticktime'), DATETIME_FORMAT_ACTIVITY)
        self.tick_time = self.tick_time.replace(tzinfo=UTC)
        self.tick_forced = dict.get('tickforced', False)
        self.discord_webhook_data = dict.get('discordwebhookdata', {})
        self.discord_notes = dict.get('discordnotes', "")
        self.systems = dict.get('systems', {})



    # Comparator functions - we use the tick_time for sorting

    def __eq__(self, other):
        if isinstance(other, Activity): return (self.tick_time == other.tick_time)
        return False

    def __lt__(self, other):
        if isinstance(other, Activity): return (self.tick_time < other.tick_time)
        return False

    def __le__(self, other):
        if isinstance(other, Activity): return (self.tick_time <= other.tick_time)
        return False

    def __gt__(self, other):
        if isinstance(other, Activity): return (self.tick_time > other.tick_time)
        return False

    def __ge__(self, other):
        if isinstance(other, Activity): return (self.tick_time >= other.tick_time)
        return False

    def __repr__(self):
        return f"{self.tick_id} ({self.tick_time}): {self._as_dict()}"


    def __add__(self, other):
        self.systems = add_dicts(self.systems, other.systems)
        return self

    # Deep copy override function - we don't deep copy any class references, just data

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        # Copied items
        setattr(result, 'bgstally', self.bgstally)
        setattr(result, 'tick_id', self.tick_id)
        setattr(result, 'tick_time', self.tick_time)
        setattr(result, 'tick_forced', self.tick_forced)
        setattr(result, 'discord_notes', self.discord_notes)
        setattr(result, 'megaship_pat', self.megaship_pat)

        # Deep copied items
        setattr(result, 'systems', deepcopy(self.systems, memo))
        setattr(result, 'discord_webhook_data', deepcopy(self.discord_webhook_data, memo))

        return result
