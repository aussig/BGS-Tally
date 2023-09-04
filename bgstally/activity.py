import json
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Dict

from bgstally.constants import CheckStates, DiscordActivity
from bgstally.debug import Debug
from bgstally.missionlog import MissionLog
from bgstally.state import State
from bgstally.tick import Tick
from bgstally.utils import human_format
from thirdparty.colors import *

DATETIME_FORMAT_ACTIVITY = "%Y-%m-%dT%H:%M:%S.%fZ"
DATETIME_FORMAT_TITLE = "%Y-%m-%d %H:%M:%S"
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
    'Mission_TW_RefugeeBulk_name' # "Evacuate xxx's group of refugees" (passenger)
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

CZ_GROUND_LOW_CB_MAX = 5000
CZ_GROUND_MED_CB_MAX = 38000

TW_CBS = {25000: 'r', 65000: 's', 75000: 's', 4500000: 'sg', 6500000: 'c', 20000000: 'b', 25000000: 'o', 34000000: 'm', 40000000: 'o', 50000000: 'h'}


class Activity:
    """
    User activity for a single tick

    Activity is stored in the self.systems Dict, with key = SystemAddress and value = Dict containing the system name and a Dict of
    factions with their activity
    """

    def __init__(self, bgstally, tick: Tick = None, discord_bgs_messageid: str = None):
        """
        Instantiate using a given Tick
        """
        self.bgstally = bgstally
        if tick == None: tick = Tick(self.bgstally)

        # Stored data. Remember to modify __deepcopy__(), _as_dict() and _from_dict() if these are changed or new data added.
        self.tick_id: str = tick.tick_id
        self.tick_time: datetime = tick.tick_time
        self.tick_forced: bool = False
        self.discord_bgs_messageid: str = discord_bgs_messageid
        self.discord_tw_messageid: str = None
        self.discord_notes: str = ""
        self.dirty: bool = False
        self.systems: dict = {}


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


    def get_title(self) -> str:
        """
        Get the title for this activity
        """
        if self.tick_forced:
            return f"{str(self.tick_time.strftime(DATETIME_FORMAT_TITLE))} (forced)"
        else:
            return f"{str(self.tick_time.strftime(DATETIME_FORMAT_TITLE))} (game)"


    def get_ordered_systems(self):
        """
        Get an ordered list of the systems we are tracking, with the current system first, followed by those with activity, and finally those without
        """
        return sorted(self.systems.keys(), key=lambda x: (str(x) != self.bgstally.state.current_system_id, self.systems[x]['zero_system_activity'], self.systems[x]['System']))


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
                    system['Factions'][faction_name] = self._get_new_faction_data(faction_name, faction_data['FactionState'])
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

    def system_entered(self, journal_entry: Dict, state: State):
        """
        The user has entered a system
        """
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
                faction_state = faction['FactionState'] if faction['FactionState'] not in STATES_WAR and faction['FactionState'] not in STATES_ELECTION else "None"

                if faction['Name'] in current_system['Factions']:
                    # We have this faction, ensure it's up to date with latest state
                    faction_data = current_system['Factions'][faction['Name']]
                    self._update_faction_data(faction_data, faction_state)
                else:
                    # We do not have this faction, create a new clean entry
                    current_system['Factions'][faction['Name']] = self._get_new_faction_data(faction['Name'], faction_state)

            # Set war states for pairs of factions in War / Civil War / Elections
            for conflict in journal_entry.get('Conflicts', []):
                if conflict['Status'] != "active": continue

                if conflict['Faction1']['Name'] in current_system['Factions'] and conflict['Faction2']['Name'] in current_system['Factions']:
                    conflict_state = "War" if conflict['WarType'] == "war" else "CivilWar" if conflict['WarType'] == "civilwar" else "Election" if conflict['WarType'] == "election" else "None"
                    current_system['Factions'][conflict['Faction1']['Name']]['FactionState'] = conflict_state
                    current_system['Factions'][conflict['Faction2']['Name']]['FactionState'] = conflict_state

        self.recalculate_zero_activity()
        state.current_system_id = str(current_system['SystemAddress'])
        state.system_tw_status = journal_entry.get('ThargoidWar', None)


    def mission_completed(self, journal_entry: Dict, mission_log: MissionLog):
        """
        Handle mission completed
        """
        self.dirty = True
        mission = mission_log.get_mission(journal_entry['MissionID'])

        # BGS
        for faction_effect in journal_entry['FactionEffects']:
            effect_faction_name = faction_effect['Faction']
            if faction_effect['Influence'] != []:
                inf = len(faction_effect['Influence'][0]['Influence'])
                inftrend = faction_effect['Influence'][0]['Trend']
                for system_address, system in self.systems.items():
                    if str(faction_effect['Influence'][0]['SystemAddress']) != system_address: continue

                    faction = system['Factions'].get(effect_faction_name)
                    if not faction: continue

                    if inftrend == "UpGood" or inftrend == "DownGood":
                        if effect_faction_name == journal_entry['Faction']:
                            faction['MissionPoints'] += inf
                            self.bgstally.ui.show_system_report(system_address) # Only show system report for primary INF
                        else:
                            faction['MissionPointsSecondary'] += inf
                    else:
                        if effect_faction_name == journal_entry['Faction']:
                            faction['MissionPoints'] -= inf
                            self.bgstally.ui.show_system_report(system_address) # Only show system report for primary INF
                        else:
                            faction['MissionPointsSecondary'] -= inf

            elif mission is not None:  # No influence specified for faction effect
                for system_address, system in self.systems.items():
                    if mission['System'] != system['System']: continue

                    faction = system['Factions'].get(effect_faction_name)
                    if not faction: continue

                    if (faction['FactionState'] in STATES_ELECTION and journal_entry['Name'] in MISSIONS_ELECTION) \
                    or (faction['FactionState'] in STATES_WAR and journal_entry['Name'] in MISSIONS_WAR) \
                    and effect_faction_name == journal_entry['Faction']:
                        faction['MissionPoints'] += 1
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

                    if mission.get('PassengerCount', -1) > -1:
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
                    elif journal_entry['Name'] in MISSIONS_TW_REACTIVATE:
                        self.bgstally.ui.show_system_report(system_address)

                        # This tracking is unusual - we track BOTH against the station where the mission was completed AND the system where the settlement was reactivated
                        tw_stations[mission_station]['reactivate'] += 1
                        destination_system = self.get_system_by_name(mission['DestinationSystem'])
                        if destination_system is not None:
                            destination_system['TWReactivate'] += 1

        self.recalculate_zero_activity()
        mission_log.delete_mission_by_id(journal_entry['MissionID'])


    def mission_failed(self, journal_entry: Dict, mission_log: MissionLog):
        """
        Handle mission failed
        """
        mission = mission_log.get_mission(journal_entry['MissionID'])
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
            self._search_and_rescue_handin('t', journal_entry.get('Count', 0))
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


    def ship_targeted(self, journal_entry: Dict, state: State):
        """
        Handle targeting a ship
        """
        if 'Faction' in journal_entry and 'PilotName_Localised' in journal_entry:
            self.dirty = True
            state.last_ship_targeted = {'Faction': journal_entry['Faction'], 'PilotName_Localised': journal_entry['PilotName_Localised']}


    def crime_committed(self, journal_entry: Dict, state: State):
        """
        Handle a crime
        """
        current_system = self.systems.get(state.current_system_id)
        if not current_system: return
        self.dirty = True

        # For in-space murders, the faction logged in the CommitCrime event is the system faction,
        # not the ship faction. We need to log the murder against the ship faction, so we store the
        # it from the previous ShipTargeted event in last_ship_targeted.

        match journal_entry['CrimeType']:
            case 'murder':
                # For ship murders, if we didn't get a previous scan containing ship faction, don't log
                if journal_entry.get('Victim') != state.last_ship_targeted.get('PilotName_Localised'): return
                faction = current_system['Factions'].get(state.last_ship_targeted.get('Faction'))
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


    def settlement_approached(self, journal_entry: Dict, state:State):
        """
        Handle approaching a settlement
        """
        state.last_settlement_approached = {'timestamp': journal_entry['timestamp'], 'name': journal_entry['Name'], 'size': None}


    def destination_dropped(self, journal_entry: dict, state: State):
        """
        Handle drop at a supercruise destination
        """
        current_system = self.systems.get(state.current_system_id)
        if not current_system: return

        match journal_entry.get('Type', "").lower():
            case type if type.startswith("$warzone_pointrace_low"):
                state.last_spacecz_approached = {'timestamp': journal_entry['timestamp'], 'type': 'l', 'counted': False}
            case type if type.startswith("$warzone_pointrace_med"):
                state.last_spacecz_approached = {'timestamp': journal_entry['timestamp'], 'type': 'm', 'counted': False}
            case type if type.startswith("$warzone_pointrace_high"):
                state.last_spacecz_approached = {'timestamp': journal_entry['timestamp'], 'type': 'h', 'counted': False}


    def cb_received(self, journal_entry: Dict, state: State):
        """
        Handle a combat bond received for a kill
        """
        current_system = self.systems.get(state.current_system_id)
        if not current_system: return

        # Check for Thargoid Kill
        if journal_entry.get('VictimFaction', "").lower() == "$faction_thargoid;":
            self._cb_tw(journal_entry, current_system)
            return

        # Otherwise, must be on-ground or in-space CZ for CB kill tracking
        if state.last_settlement_approached != {}:
            timedifference = datetime.strptime(journal_entry['timestamp'], "%Y-%m-%dT%H:%M:%SZ") - datetime.strptime(state.last_settlement_approached['timestamp'], "%Y-%m-%dT%H:%M:%SZ")
            if timedifference > timedelta(minutes=5):
                # Too long since we last approached a settlement, we can't be sure we're fighting at that settlement, clear down
                state.last_settlement_approached = {}
                # Fall through to check space CZs too
            else:
                # We're within the timeout, refresh timestamp and handle the CB
                state.last_settlement_approached['timestamp'] = journal_entry['timestamp']
                self._cb_ground_cz(journal_entry, current_system, state)

        if state.last_spacecz_approached != {}:
            timedifference = datetime.strptime(journal_entry['timestamp'], "%Y-%m-%dT%H:%M:%SZ") - datetime.strptime(state.last_spacecz_approached['timestamp'], "%Y-%m-%dT%H:%M:%SZ")
            if timedifference > timedelta(minutes=5):
                # Too long since we last entered a space cz, we can't be sure we're fighting at that cz, clear down
                state.last_spacecz_approached = {}
            else:
                # We're within the timeout, refresh timestamp and handle the CB
                state.last_spacecz_approached['timestamp'] = journal_entry['timestamp']
                self._cb_space_cz(journal_entry, current_system, state)


    def _cb_tw(self, journal_entry:dict, current_system:dict):
        """
        We are logging a Thargoid kill
        """
        tw_ship:str = TW_CBS.get(journal_entry.get('Reward', 0))
        if tw_ship: current_system['TWKills'][tw_ship] += 1

        self.bgstally.ui.show_system_report(current_system['SystemAddress'])


    def _cb_ground_cz(self, journal_entry:dict, current_system:dict, state:State):
        """
        We are in an active ground CZ
        """
        faction = current_system['Factions'].get(journal_entry['AwardingFaction'])
        if not faction: return

        self.dirty = True

        self.bgstally.ui.show_system_report(current_system['SystemAddress'])

        # Add settlement to this faction's list, if not already present
        if state.last_settlement_approached['name'] not in faction['GroundCZSettlements']:
            faction['GroundCZSettlements'][state.last_settlement_approached['name']] = {'count': 0, 'enabled': CheckStates.STATE_ON, 'type': 'l'}

        # Store the previously counted size of this settlement
        previous_size = state.last_settlement_approached['size']

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
                faction['GroundCZ']['l'] = str(int(faction['GroundCZ'].get('l', '0')) + 1)
                # Set faction settlement type
                faction['GroundCZSettlements'][state.last_settlement_approached['name']]['type'] = 'l'
                # Store last settlement type
                state.last_settlement_approached['size'] = 'l'
        elif journal_entry['Reward'] < CZ_GROUND_MED_CB_MAX:
            # Handle as 'Med' if this is either the first CB or we've counted this settlement as a 'Low' before
            if state.last_settlement_approached['size'] == None or state.last_settlement_approached['size'] == 'l':
                # Increment overall 'Med' count for this faction
                faction['GroundCZ']['m'] = str(int(faction['GroundCZ'].get('m', '0')) + 1)
                # Decrement overall previous size count if we previously counted it
                if previous_size != None: faction['GroundCZ'][previous_size] = str(int(faction['GroundCZ'].get(previous_size, '0')) - 1)
                # Set faction settlement type
                faction['GroundCZSettlements'][state.last_settlement_approached['name']]['type'] = 'm'
                # Store last settlement type
                state.last_settlement_approached['size'] = 'm'
        else:
            # Handle as 'High' if this is either the first CB or we've counted this settlement as a 'Low' or 'Med' before
            if state.last_settlement_approached['size'] == None or state.last_settlement_approached['size'] == 'l' or state.last_settlement_approached['size'] == 'm':
                # Increment overall 'High' count for this faction
                faction['GroundCZ']['h'] = str(int(faction['GroundCZ'].get('h', '0')) + 1)
                # Decrement overall previous size count if we previously counted it
                if previous_size != None: faction['GroundCZ'][previous_size] = str(int(faction['GroundCZ'].get(previous_size, '0')) - 1)
                # Set faction settlement type
                faction['GroundCZSettlements'][state.last_settlement_approached['name']]['type'] = 'h'
                # Store last settlement type
                state.last_settlement_approached['size'] = 'h'

        self.recalculate_zero_activity()


    def _cb_space_cz(self, journal_entry:dict, current_system:dict, state:State):
        """
        We are in an active space CZ
        """
        faction = current_system['Factions'].get(journal_entry['AwardingFaction'])
        if not faction: return

        # If we've already counted this CZ, exit
        if state.last_spacecz_approached.get('counted', False): return

        state.last_spacecz_approached['counted'] = True
        self.dirty = True

        self.bgstally.ui.show_system_report(current_system['SystemAddress'])

        type:str = state.last_spacecz_approached.get('type', 'l')
        faction['SpaceCZ'][type] = str(int(faction['SpaceCZ'].get(type, '0')) + 1)

        self.recalculate_zero_activity()


    def collect_cargo(self, journal_entry: dict, state: State):
        """
        Handle cargo collection for certain cargo types
        """
        current_system = self.systems.get(state.current_system_id)
        if not current_system: return

        key:str = None

        match journal_entry.get('Type', "").lower():
            case 'damagedescapepod': key = 'dp'
            case 'occupiedcryopod': key = 'op'
            case 'usscargoblackbox': key = 'bb'
            case _ as cargo_type if "thargoidtissuesample" in cargo_type or "thargoidscouttissuesample" in cargo_type: key = 't'

        if key is None: return

        current_system['TWSandR'][key]['scooped'] += 1
        self.dirty = True


    def search_and_rescue(self, journal_entry: dict, state: State):
        """
        Handle search and rescue hand-in
        """
        key:str = None
        count:int = int(journal_entry.get('Count', 0))

        # There is no tissue sample tracking here as those are treated a commodities
        match journal_entry.get('Name', "").lower():
            case 'damagedescapepod': key = 'dp'
            case 'occupiedcryopod': key = 'op'
            case 'usscargoblackbox': key = 'bb'

        if key is None or count == 0: return

        self._search_and_rescue_handin(key, count)


    def _search_and_rescue_handin(self, key:str, count:int):
        """
        Tally a search and rescue handin. These can originate from SearchAndRescue or TradeSell events
        """

        # S&R can be handed in in any system, but the effect counts for the system the items were collected in. However,
        # we have no way of knowing exactly which items were handed in, so just iterate through all our known systems
        # looking for previously scooped cargo of the correct type.

        for system in self.systems.values():
            if count <= 0: break  # Finish when we've accounted for all items

            allocatable:int = min(count, system['TWSandR'][key]['scooped'])
            if allocatable > 0:
                system['TWSandR'][key]['scooped'] -= allocatable
                system['TWSandR'][key]['delivered'] += allocatable
                count -= allocatable
                self.dirty = True

                self.bgstally.ui.show_system_report(system['SystemAddress'])

        # count can end up > 0 here - i.e. more S&R handed in than we originally logged as scooped. Ignore, as we don't know
        # where it originally came from


    def player_resurrected(self):
        """
        Clear down any logged cargo on resurrect
        """
        for system in self.systems.values():
            system['TWSandR'] = self._get_new_tw_sandr_data()

        self.dirty = True


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


    def generate_text(self, activity_mode: DiscordActivity, discord: bool = False, system_name: str = None):
        """
        Generate plain text report
        """
        text:str = ""
        # Force plain text if we are not posting to Discord
        fp:bool = not discord

        for system in self.systems.values():
            if system_name is not None and system['System'] != system_name: continue
            system_text:str = ""

            if activity_mode == DiscordActivity.THARGOIDWAR or activity_mode == DiscordActivity.BOTH:
                system_text += self._generate_tw_system_text(system, discord)

            if activity_mode == DiscordActivity.BGS or activity_mode == DiscordActivity.BOTH:
                for faction in system['Factions'].values():
                    if faction['Enabled'] != CheckStates.STATE_ON: continue
                    system_text += self._generate_faction_text(faction, discord)

            if system_text != "":
                if discord: text += f"```ansi\n{color_wrap(system['System'], 'white', None, 'bold', fp=fp)}\n{system_text}```"
                else: text += f"{color_wrap(system['System'], 'white', None, 'bold', fp=fp)}\n{system_text}"

        if discord and self.discord_notes is not None and self.discord_notes != "": text += "\n" + self.discord_notes

        return text.replace("'", "")


    def generate_discord_embed_fields(self, activity_mode: DiscordActivity):
        """
        Generate fields for a Discord post with embed
        """
        discord_fields = []

        for system in self.systems.values():
            system_text = ""

            if activity_mode == DiscordActivity.THARGOIDWAR or activity_mode == DiscordActivity.BOTH:
                system_text += self._generate_tw_system_text(system, True)

            if activity_mode == DiscordActivity.BGS or activity_mode == DiscordActivity.BOTH:
                for faction in system['Factions'].values():
                    if faction['Enabled'] != CheckStates.STATE_ON: continue
                    system_text += self._generate_faction_text(faction, True)

            if system_text != "":
                system_text = system_text.replace("'", "")
                discord_field = {'name': system['System'], 'value': f"```ansi\n{system_text}```"}
                discord_fields.append(discord_field)

        return discord_fields


    #
    # Private functions
    #

    def _get_new_system_data(self, system_name: str, system_address: str, faction_data: Dict):
        """
        Get a new data structure for storing system data
        """
        return {'System': system_name,
                'SystemAddress': system_address,
                'zero_system_activity': True,
                'Factions': faction_data,
                'TWKills': self._get_new_tw_kills_data(),
                'TWSandR': self._get_new_tw_sandr_data()}


    def _get_new_faction_data(self, faction_name, faction_state):
        """
        Get a new data structure for storing faction data
        """
        return {'Faction': faction_name, 'FactionState': faction_state, 'Enabled': self.bgstally.state.EnableSystemActivityByDefault.get(),
                'MissionPoints': 0, 'MissionPointsSecondary': 0,
                'TradeProfit': 0, 'TradePurchase': 0, 'BlackMarketProfit': 0, 'Bounties': 0, 'CartData': 0, 'ExoData': 0,
                'TradeBuy': [{'items': 0, 'value': 0}, {'items': 0, 'value': 0}, {'items': 0, 'value': 0}, {'items': 0, 'value': 0}],
                'TradeSell': [{'items': 0, 'value': 0, 'profit': 0}, {'items': 0, 'value': 0, 'profit': 0}, {'items': 0, 'value': 0, 'profit': 0}, {'items': 0, 'value': 0, 'profit': 0}],
                'CombatBonds': 0, 'MissionFailed': 0, 'Murdered': 0, 'GroundMurdered': 0,
                'SpaceCZ': {}, 'GroundCZ': {}, 'GroundCZSettlements': {}, 'Scenarios': 0,
                'TWStations': {}}


    def _get_new_tw_station_data(self, station_name):
        """
        Get a new data structure for storing Thargoid War station data
        """
        return {'name': station_name, 'enabled': CheckStates.STATE_ON,
                'passengers': {'l': {'count': 0, 'sum': 0}, 'm': {'count': 0, 'sum': 0}, 'h': {'count': 0, 'sum': 0}},
                'escapepods': {'l': {'count': 0, 'sum': 0}, 'm': {'count': 0, 'sum': 0}, 'h': {'count': 0, 'sum': 0}},
                'cargo': {'count': 0, 'sum': 0},
                'massacre': {'s': {'count': 0, 'sum': 0}, 'c': {'count': 0, 'sum': 0}, 'b': {'count': 0, 'sum': 0}, 'm': {'count': 0, 'sum': 0}, 'h': {'count': 0, 'sum': 0}, 'o': {'count': 0, 'sum': 0}},
                'reactivate': 0}


    def _get_new_aggregate_tw_station_data(self):
        """
        Get a new data structure for aggregating Thargoid War station data when displaying in text reports
        """
        return {'mission_count_total': 0,
                'passengers': {'count': 0, 'sum': 0},
                'escapepods': {'l': {'count': 0, 'sum': 0}, 'm': {'count': 0, 'sum': 0}, 'h': {'count': 0, 'sum': 0}},
                'cargo': {'count': 0, 'sum': 0},
                'massacre': {'s': {'count': 0, 'sum': 0}, 'c': {'count': 0, 'sum': 0}, 'b': {'count': 0, 'sum': 0}, 'm': {'count': 0, 'sum': 0}, 'h': {'count': 0, 'sum': 0}, 'o': {'count': 0, 'sum': 0}},
                'reactivate': 0}


    def _get_new_tw_kills_data(self):
        """
        Get a new data structure for storing Thargoid War Kills
        """
        return {'r': 0, 's': 0, 'sg': 0, 'c': 0, 'b': 0, 'm': 0, 'h': 0, 'o': 0}


    def _get_new_tw_sandr_data(self):
        """
        Get a new data structure for storing Thargoid War Search and Rescue
        """
        return {'dp': {'scooped': 0, 'delivered': 0}, 'op': {'scooped': 0, 'delivered': 0}, 'bb': {'scooped': 0, 'delivered': 0}, 't': {'scooped': 0, 'delivered': 0}}


    def _update_system_data(self, system_data:dict):
        """
        Update system data structure for elements not present in previous versions of plugin
        """
        # From < v3.1.0 to 3.1.0
        if not 'TWKills' in system_data: system_data['TWKills'] = self._get_new_tw_kills_data()
        if not 'TWSandR' in system_data: system_data['TWSandR'] = self._get_new_tw_sandr_data()
        # From < 3.2.0 to 3.2.0
        if not 'TWReactivate' in system_data: system_data['TWReactivate'] = 0


    def _update_faction_data(self, faction_data: Dict, faction_state: str = None):
        """
        Update faction data structure for elements not present in previous versions of plugin
        """
        # Update faction state as it can change at any time post-tick
        if faction_state: faction_data['FactionState'] = faction_state

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
        # 2.2.0-a1 - 2.2.0-a3 stored a single integer for passengers,  escapepods and cargo in TW station data. 2.2.0-a4 onwards has a dict for each.
        # Put the previous values for passengers and escapepods into the 'm' 'sum' entries in the dict, for want of a better place.
        # Put the previous value for cargo into the 'sum' entry in the dict.
        # The previous mission count value was aggregate across all passengers, escape pods and cargo so just plonk in escapepods for want of a better place.
        # We can remove all this code on release of final 2.2.0
        for station in faction_data['TWStations'].values():
            if not type(station.get('passengers')) == dict:
                station['passengers'] = {'l': {'count': 0, 'sum': 0}, 'm': {'count': 0, 'sum': station['passengers']}, 'h': {'count': 0, 'sum': 0}}
            if not type(station.get('escapepods')) == dict:
                station['escapepods'] = {'l': {'count': 0, 'sum': 0}, 'm': {'count': station['missions'], 'sum': station['escapepods']}, 'h': {'count': 0, 'sum': 0}}
            if not type(station.get('cargo')) == dict:
                station['cargo'] = {'count': 0, 'sum': station['cargo']}
            if not type(station.get('massacre')) == dict:
                station['massacre'] = {'s': {'count': 0, 'sum': 0}, 'c': {'count': 0, 'sum': 0}, 'b': {'count': 0, 'sum': 0}, 'm': {'count': 0, 'sum': 0}, 'h': {'count': 0, 'sum': 0}, 'o': {'count': 0, 'sum': 0}}
        # From < 3.0.0 to 3.0.0
        if not 'GroundMurdered' in faction_data: faction_data['GroundMurdered'] = 0
        if not 'TradeBuy' in faction_data:
            faction_data['TradeBuy'] = [{'items': 0, 'value': 0}, {'items': 0, 'value': 0}, {'items': 0, 'value': 0}, {'items': 0, 'value': 0}]
        if not 'TradeSell' in faction_data:
            faction_data['TradeSell'] = [{'items': 0, 'value': 0, 'profit': 0}, {'items': 0, 'value': 0, 'profit': 0}, {'items': 0, 'value': 0, 'profit': 0}, {'items': 0, 'value': 0, 'profit': 0}]
        # From < 3.2.0 to 3.2.0
        for station in faction_data['TWStations'].values():
            if not 'reactivate' in station: station['reactivate'] = 0


    def _is_faction_data_zero(self, faction_data: Dict):
        """
        Check whether all information is empty or zero for a faction
        """
        return int(faction_data['MissionPoints']) == 0 and int(faction_data['MissionPointsSecondary']) == 0 and \
                int(faction_data['TradeProfit']) == 0 and int(faction_data['TradePurchase']) == 0 and int(faction_data['BlackMarketProfit']) == 0 and \
                sum(int(d['value']) for d in faction_data['TradeBuy']) == 0 and \
                sum(int(d['value']) for d in faction_data['TradeSell']) == 0 and \
                int(faction_data['BlackMarketProfit']) == 0 and \
                int(faction_data['Bounties']) == 0 and int(faction_data['CartData']) == 0 and int(faction_data['ExoData']) == 0 and \
                int(faction_data['CombatBonds']) == 0 and int(faction_data['MissionFailed']) == 0 and int(faction_data['Murdered']) == 0 and int(faction_data['GroundMurdered']) == 0 and \
                (faction_data['SpaceCZ'] == {} or (int(faction_data['SpaceCZ'].get('l', 0)) == 0 and int(faction_data['SpaceCZ'].get('m', 0)) == 0 and int(faction_data['SpaceCZ'].get('h', 0)) == 0)) and \
                (faction_data['GroundCZ'] == {} or (int(faction_data['GroundCZ'].get('l', 0)) == 0 and int(faction_data['GroundCZ'].get('m', 0)) == 0 and int(faction_data['GroundCZ'].get('h', 0)) == 0)) and \
                faction_data['GroundCZSettlements'] == {} and \
                int(faction_data['Scenarios']) == 0 and \
                faction_data['TWStations'] == {}


    def _generate_faction_text(self, faction: dict, discord: bool):
        """
        Generate formatted text for a faction
        """
        activity_text:str = ""
        # Force plain text if we are not posting to Discord
        fp:bool = not discord

        inf = faction['MissionPoints']
        if self.bgstally.state.IncludeSecondaryInf.get() == CheckStates.STATE_ON: inf += faction['MissionPointsSecondary']

        if faction['FactionState'] in STATES_ELECTION:
            activity_text += f"{blue('ElectionINF', fp=fp)} {green(f'+{inf}', fp=fp)} " if inf > 0 else f"{blue('ElectionINF', fp=fp)} {green(inf, fp=fp)} " if inf < 0 else ""
        elif faction['FactionState'] in STATES_WAR:
            activity_text += f"{blue('WarINF', fp=fp)} {green(f'+{inf}', fp=fp)} " if inf > 0 else f"{blue('WarINF', fp=fp)} {green(inf, fp=fp)} " if inf < 0 else ""
        else:
            activity_text += f"{blue('INF', fp=fp)} {green(f'+{inf}', fp=fp)} " if inf > 0 else f"{blue('INF', fp=fp)} {green(inf, fp=fp)} " if inf < 0 else ""

        activity_text += f"{red('BVs', fp=fp)} {green(human_format(faction['Bounties']), fp=fp)} " if faction['Bounties'] != 0 else ""
        activity_text += f"{red('CBs', fp=fp)} {green(human_format(faction['CombatBonds']), fp=fp)} " if faction['CombatBonds'] != 0 else ""
        if faction['TradePurchase'] > 0:
            # Legacy - Used a single value for purchase value / profit
            activity_text += f"{cyan('TrdPurchase', fp=fp)} {green(human_format(faction['TradePurchase']), fp=fp)} " if faction['TradePurchase'] != 0 else ""
            activity_text += f"{cyan('TrdProfit', fp=fp)} {green(human_format(faction['TradeProfit']), fp=fp)} " if faction['TradeProfit'] != 0 else ""
        else:
            # Modern - Split into values per supply / demand bracket
            if sum(int(d['value']) for d in faction['TradeBuy']) > 0:
                # Buy brackets currently range from 0 - 3
                activity_text += f"{cyan('TrdBuy', fp=fp)} " \
                    + f"{'🅻' if discord else '[L]'}:{green(human_format(faction['TradeBuy'][2]['value']), fp=fp)} " \
                    + f"{'🅷' if discord else '[H]'}:{green(human_format(faction['TradeBuy'][3]['value']), fp=fp)} "
            if sum(int(d['value']) for d in faction['TradeSell']) > 0:
                # Sell brackets currently range from 0 - 3
                activity_text += f"{cyan('TrdProfit', fp=fp)} " \
                    + f"{'🆉' if discord else '[Z]'}:{green(human_format(faction['TradeSell'][0]['profit']), fp=fp)} " \
                    + f"{'🅻' if discord else '[L]'}:{green(human_format(faction['TradeSell'][2]['profit']), fp=fp)} " \
                    + f"{'🅷' if discord else '[H]'}:{green(human_format(faction['TradeSell'][3]['profit']), fp=fp)} "
        activity_text += f"{cyan('TrdBMProfit', fp=fp)} {green(human_format(faction['BlackMarketProfit']), fp=fp)} " if faction['BlackMarketProfit'] != 0 else ""
        activity_text += f"{white('Expl', fp=fp)} {green(human_format(faction['CartData']), fp=fp)} " if faction['CartData'] != 0 else ""
        activity_text += f"{grey('Exo', fp=fp)} {green(human_format(faction['ExoData']), fp=fp)} " if faction['ExoData'] != 0 else ""
        activity_text += f"{red('Murders', fp=fp)} {green(faction['Murdered'], fp=fp)} " if faction['Murdered'] != 0 else ""
        activity_text += f"{red('GroundMurders', fp=fp)} {green(faction['GroundMurdered'], fp=fp)} " if faction['GroundMurdered'] != 0 else ""
        activity_text += f"{yellow('Scenarios', fp=fp)} {green(faction['Scenarios'], fp=fp)} " if faction['Scenarios'] != 0 else ""
        activity_text += f"{magenta('Fails', fp=fp)} {green(faction['MissionFailed'], fp=fp)} " if faction['MissionFailed'] != 0 else ""
        space_cz = self._build_cz_text(faction.get('SpaceCZ', {}), "SpaceCZs", discord)
        activity_text += f"{space_cz} " if space_cz != "" else ""
        ground_cz = self._build_cz_text(faction.get('GroundCZ', {}), "GroundCZs", discord)
        activity_text += f"{ground_cz} " if ground_cz != "" else ""

        faction_name = self._process_faction_name(faction['Faction'])
        faction_text = f"{color_wrap(faction_name, 'yellow', None, 'bold', fp=fp)} {activity_text}\n" if activity_text != "" else ""

        for settlement_name in faction.get('GroundCZSettlements', {}):
            if faction['GroundCZSettlements'][settlement_name]['enabled'] == CheckStates.STATE_ON:
                faction_text += f"  {'⚔️' if discord else '[X]'} {settlement_name} x {green(faction['GroundCZSettlements'][settlement_name]['count'], fp=fp)}\n"

        return faction_text


    def _generate_tw_system_text(self, system: dict, discord: bool):
        """
        Create formatted text for Thargoid War in a system
        """
        system_text = ""
        system_stations = {}
        # Force plain text if we are not posting to Discord
        fp:bool = not discord

        # Faction-specific tally
        for faction in system['Factions'].values():
            if faction['Enabled'] != CheckStates.STATE_ON: continue

            for station_name in faction.get('TWStations', {}):
                faction_station = faction['TWStations'][station_name]
                if faction_station['enabled'] != CheckStates.STATE_ON: continue

                if not station_name in system_stations: system_stations[station_name] = self._get_new_aggregate_tw_station_data()
                system_station = system_stations[station_name]

                # Current understanding is we don't need to report the different passenger priorities separately, so aggregate all into a single count and sum
                system_station['passengers']['count'] += faction_station['passengers']['l']['count'] + faction_station['passengers']['m']['count'] + faction_station['passengers']['h']['count']
                system_station['passengers']['sum'] += faction_station['passengers']['l']['sum'] + faction_station['passengers']['m']['sum'] + faction_station['passengers']['h']['sum']
                system_station['mission_count_total'] += (sum(x['count'] for x in faction_station['passengers'].values()))
                # Current understanding is it is important to report each type of escape pod evac mission separately
                system_station['escapepods']['l']['count'] += faction_station['escapepods']['l']['count']; system_station['escapepods']['l']['sum'] += faction_station['escapepods']['l']['sum']
                system_station['escapepods']['m']['count'] += faction_station['escapepods']['m']['count']; system_station['escapepods']['m']['sum'] += faction_station['escapepods']['m']['sum']
                system_station['escapepods']['h']['count'] += faction_station['escapepods']['h']['count']; system_station['escapepods']['h']['sum'] += faction_station['escapepods']['h']['sum']
                system_station['mission_count_total'] += (sum(x['count'] for x in faction_station['escapepods'].values()))
                # We don't track different priorities of cargo missions
                system_station['cargo']['count'] += faction_station['cargo']['count']
                system_station['cargo']['sum'] += faction_station['cargo']['sum']
                system_station['mission_count_total'] += faction_station['cargo']['count']
                # We track each type of Thargoid ship massacre mission separately
                system_station['massacre']['s']['count'] += faction_station['massacre']['s']['count']; system_station['massacre']['s']['sum'] += faction_station['massacre']['s']['sum']
                system_station['massacre']['c']['count'] += faction_station['massacre']['c']['count']; system_station['massacre']['c']['sum'] += faction_station['massacre']['c']['sum']
                system_station['massacre']['b']['count'] += faction_station['massacre']['b']['count']; system_station['massacre']['b']['sum'] += faction_station['massacre']['b']['sum']
                system_station['massacre']['m']['count'] += faction_station['massacre']['m']['count']; system_station['massacre']['m']['sum'] += faction_station['massacre']['m']['sum']
                system_station['massacre']['h']['count'] += faction_station['massacre']['h']['count']; system_station['massacre']['h']['sum'] += faction_station['massacre']['h']['sum']
                system_station['massacre']['o']['count'] += faction_station['massacre']['o']['count']; system_station['massacre']['o']['sum'] += faction_station['massacre']['o']['sum']
                system_station['mission_count_total'] += (sum(x['count'] for x in faction_station['massacre'].values()))
                # We track TW settlement reactivation missions as a simple total
                system_station['reactivate'] += faction_station['reactivate']
                system_station['mission_count_total'] += faction_station['reactivate']

        # System-specific tally
        kills:int = sum(system['TWKills'].values())
        sandr:int = sum(int(d['delivered']) for d in system['TWSandR'].values())
        reactivate:int = system['TWReactivate']
        if kills > 0 or sandr > 0 or reactivate > 0:
            system_text += f"🍀 System activity\n"
            if kills > 0:
                system_text += f"  💀 (kills): " \
                                    + f"{red('R', fp=fp)} x {green(system['TWKills'].get('r', 0), fp=fp)}, " \
                                    + f"{red('S', fp=fp)} x {green(system['TWKills'].get('s', 0), fp=fp)}, " \
                                    + f"{red('S/G', fp=fp)} x {green(system['TWKills'].get('sg', 0), fp=fp)}, " \
                                    + f"{red('C', fp=fp)} x {green(system['TWKills'].get('c', 0), fp=fp)}, " \
                                    + f"{red('B', fp=fp)} x {green(system['TWKills'].get('b', 0), fp=fp)}, " \
                                    + f"{red('M', fp=fp)} x {green(system['TWKills'].get('m', 0), fp=fp)}, " \
                                    + f"{red('H', fp=fp)} x {green(system['TWKills'].get('h', 0), fp=fp)}, " \
                                    + f"{red('O', fp=fp)} x {green(system['TWKills'].get('o', 0), fp=fp)} \n"
            if sandr > 0:
                system_text += "  "
                pods:int = system['TWSandR']['dp']['delivered'] + system['TWSandR']['op']['delivered']
                if pods > 0: system_text += f"⚰️ x {green(pods, fp=fp)} "
                bbs:int = system['TWSandR']['bb']['delivered']
                if bbs > 0: system_text += f"⬛ x {green(bbs, fp=fp)} "
                tissue:int = system['TWSandR']['t']['delivered']
                if tissue > 0: system_text += f"🌱 x {green(tissue, fp=fp)} "
                system_text += "\n"
            if reactivate > 0:
                system_text += f"  🛠️ x {green(reactivate, fp=fp)} settlements\n"

        # Station-specific tally
        for system_station_name, system_station in system_stations.items():
            system_text += f"🍀 {system_station_name}: {green(system_station['mission_count_total'], fp=fp)} missions\n"
            if (system_station['escapepods']['m']['sum'] > 0):
                system_text += f"  ❕ x {green(system_station['escapepods']['m']['sum'], fp=fp)} - {green(system_station['escapepods']['m']['count'], fp=fp)} missions\n"
            if (system_station['escapepods']['h']['sum'] > 0):
                system_text += f"  ❗ x {green(system_station['escapepods']['h']['sum'], fp=fp)} - {green(system_station['escapepods']['h']['count'], fp=fp)} missions\n"
            if (system_station['cargo']['sum'] > 0):
                system_text += f"  📦 x {green(system_station['cargo']['sum'], fp=fp)} - {green(system_station['cargo']['count'], fp=fp)} missions\n"
            if (system_station['escapepods']['l']['sum'] > 0):
                system_text += f"  ⚕️ x {green(system_station['escapepods']['l']['sum'], fp=fp)} - {green(system_station['escapepods']['l']['count'], fp=fp)} missions\n"
            if (system_station['passengers']['sum'] > 0):
                system_text += f"  🧍 x {green(system_station['passengers']['sum'], fp=fp)} - {green(system_station['passengers']['count'], fp=fp)} missions\n"
            if (sum(x['sum'] for x in system_station['massacre'].values())) > 0:
                system_text += f"  💀 (missions): {red('S', fp=fp)} x {green(system_station['massacre']['s']['sum'], fp=fp)}, {red('C', fp=fp)} x {green(system_station['massacre']['c']['sum'], fp=fp)}, " \
                                    + f"{red('B', fp=fp)} x {green(system_station['massacre']['b']['sum'], fp=fp)}, {red('M', fp=fp)} x {green(system_station['massacre']['m']['sum'], fp=fp)}, " \
                                    + f"{red('H', fp=fp)} x {green(system_station['massacre']['h']['sum'], fp=fp)}, {red('O', fp=fp)} x {green(system_station['massacre']['o']['sum'], fp=fp)} " \
                                    + f"- {green((sum(x['count'] for x in system_station['massacre'].values())), fp=fp)} missions\n"
            if (system_station['reactivate'] > 0):
                system_text += f"  🛠️ x {green(system_station['reactivate'], fp=fp)} missions\n"

        return system_text


    def _build_cz_text(self, cz_data: dict, prefix: str, discord: bool):
        """
        Create a summary of Conflict Zone activity
        """
        if cz_data == {}: return ""
        text:str = ""
        # Force plain text if we are not posting to Discord
        fp:bool = not discord

        if 'l' in cz_data and cz_data['l'] != '0' and cz_data['l'] != '': text += f"{cz_data['l']}xL "
        if 'm' in cz_data and cz_data['m'] != '0' and cz_data['m'] != '': text += f"{cz_data['m']}xM "
        if 'h' in cz_data and cz_data['h'] != '0' and cz_data['h'] != '': text += f"{cz_data['h']}xH "

        if text != '': text = f"{red(prefix, fp=fp)} {green(text, fp=fp)}"
        return text


    def _process_faction_name(self, faction_name):
        """
        Shorten the faction name if the user has chosen to
        """
        if self.bgstally.state.AbbreviateFactionNames.get() == CheckStates.STATE_ON:
            return ''.join((i if i.isnumeric() else i[0]) for i in faction_name.split())
        else:
            return faction_name


    def _as_dict(self):
        """
        Return a Dictionary representation of our data, suitable for serializing
        """
        return {
            'tickid': self.tick_id,
            'ticktime': self.tick_time.strftime(DATETIME_FORMAT_ACTIVITY),
            'tickforced': self.tick_forced,
            'discordmessageid': self.discord_bgs_messageid,
            'discordtwmessageid': self.discord_tw_messageid,
            'discordnotes': self.discord_notes,
            'systems': self.systems}


    def _from_dict(self, dict: Dict):
        """
        Populate our data from a Dictionary that has been deserialized
        """
        self.tick_id = dict.get('tickid')
        self.tick_time = datetime.strptime(dict.get('ticktime'), DATETIME_FORMAT_ACTIVITY)
        self.tick_forced = dict.get('tickforced', False)
        self.discord_bgs_messageid = dict.get('discordmessageid')
        self.discord_tw_messageid = dict.get('discordtwmessageid')
        self.discord_notes = dict.get('discordnotes')
        self.systems = dict.get('systems')



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
        setattr(result, 'discord_bgs_messageid', self.discord_bgs_messageid)
        setattr(result, 'discord_tw_messageid', self.discord_tw_messageid)
        setattr(result, 'discord_notes', self.discord_notes)

        # Deep copied items
        setattr(result, 'systems', deepcopy(self.systems, memo))

        return result
