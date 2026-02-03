from datetime import UTC, datetime
from enum import Enum

from bgstally.activity import Activity
from bgstally.api import API
from bgstally.constants import DATETIME_FORMAT_API
from bgstally.debug import Debug
from bgstally.utils import _, get_by_path, human_format


class MissionType(str, Enum):
    RECON = 'recon'
    WIN_WAR = 'win_war'
    DRAW_WAR = 'draw_war'
    WIN_ELECTION = 'win_election'
    DRAW_ELECTION = 'draw_election'
    BOOST = 'boost'
    EXPAND = 'expand'
    REDUCE = 'reduce'
    RETREAT = 'retreat'
    EQUALISE = 'equalise'
class MissionTargetType(str, Enum):
    VISIT = 'visit'
    INF = 'inf'
    BV = 'bv'
    CB = 'cb'
    EXPL = 'expl'
    TRADE_PROFIT = 'trade_prof'
    BM_PROF = 'bm_prof'
    GROUND_CZ = 'ground_cz'
    SPACE_CZ = 'space_cz'
    MURDER = 'murder'
    MISSION_FAIL = 'mission_fail'

class ObjectivesManager:
    """
    Handles the management of objectives.

    Note that the objectives are stored inside the API object and there is only a single API tracked here.  So, if multiple APIs
    are implemented in future, it will flip-flop between them and we either need to handle that or limit objectives to a single API.
    """
    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.api: API|None = None


    def objectives_available(self) -> bool:
        """Check whether any objectives are available

        Returns:
            bool: True if there are objectives
        """
        if self.api is None: return False
        else: return len(self.api.objectives) > 0


    def get_title(self) -> str:
        if self.api is None: return _("Objectives") # LANG: Objectives title where there is no server name
        else: return _("{server_name} Objectives").format(server_name=self.api.name) # LANG: Objectives title


    def get_objectives(self) -> list:
        """Get the available objectives

        Returns:
            list: current list of objectives
        """
        if self.api is None: return []
        else: return self.api.objectives


    def _get_priority_stars(self, priority: str|None) -> str:
        """Convert priority number to star representation

        Args:
            priority (str|None): Priority as string (1-5)

        Returns:
            str: Star representation (e.g., "★★★☆☆" or "[***  ]")
        """
        try:
            priority_num = int(priority) if priority else 0
        except (ValueError, TypeError):
            priority_num = 0

        # Clamp between 0 and 5
        priority_num = max(0, min(5, priority_num))

        # Use unicode stars for visual representation
        filled_stars = "★" * priority_num
        empty_stars = "☆" * (5 - priority_num)

        return f"[{filled_stars}{empty_stars}]"


    def objectives_received(self, api: API):
        """Objectives have been received from the API

        Args:
            api (API): The API object
        """
        previous_available: bool = self.objectives_available()
        self.api = api

        if previous_available != self.objectives_available():
            # We've flipped from having objectives to not having objectives or vice versa. Refresh the plugin frame.
            self.bgstally.ui.frame.after(1000, self.bgstally.ui.update_plugin_frame())


    def get_human_readable_objectives(self, discord: bool) -> str:
        """Get the objectives nicely formatted

        Returns:
            str: The human readable objectives
        """
        result: str = ""
        if self.api is None: return result

        for mission in self.api.objectives:
            mission_title: str|None = mission.get('title')
            mission_priority: str|None = mission.get('priority', '0')
            mission_description: str|None = mission.get('description')
            mission_system: str|dict|None = mission.get('system')
            if mission_system == "" or mission_system is None:
                mission_system = {'name': _("Unknown"), 'x': 0, 'y': 0, 'z': 0} # LANG: Unknown system name
            elif isinstance(mission_system, str): # API <= v1.7.0 TODO Remove after API v1.7.0 is obsolete
                mission_system = {'name': mission_system, 'x': 0, 'y': 0, 'z': 0}
            mission_faction: str|None = mission.get('faction')
            if mission_faction is None: mission_faction = _("Unknown") # LANG: Unknown faction name
            mission_startdate: datetime = datetime.strptime(mission.get('startdate', datetime.now(UTC).strftime(DATETIME_FORMAT_API)), DATETIME_FORMAT_API)
            mission_startdate = mission_startdate.replace(tzinfo=UTC)
            mission_enddate: datetime = datetime.strptime(mission.get('enddate', datetime(3999, 12, 31, 23, 59, 59, 0, UTC).strftime(DATETIME_FORMAT_API)), DATETIME_FORMAT_API)
            mission_enddate = mission_enddate.replace(tzinfo=UTC)
            if mission_enddate < datetime.now(UTC): continue
            mission_activity: Activity = self.bgstally.activity_manager.query_activity(mission_startdate)

            # Add priority stars
            priority_stars: str = self._get_priority_stars(mission_priority)

            if mission_title:
                result += f"{priority_stars} " + mission_title + "\n"
            else:
                match mission.get('type'):
                    case MissionType.RECON: result += "º " + _("Recon Mission") + "\n" # LANG: Recon mission objective
                    case MissionType.WIN_WAR: result += "º " + _("Win a War") + "\n" # LANG: Win war mission objective
                    case MissionType.DRAW_WAR: result += "º " + _("Draw a War") + "\n" # LANG: Draw war mission objective
                    case MissionType.WIN_ELECTION: result += "º " + _("Win an Election") + "\n" # LANG: Win election mission objective
                    case MissionType.DRAW_ELECTION: result += "º " + _("Draw an Election") + "\n" # LANG: Draw election mission objective
                    case MissionType.BOOST: result += "º " + _("Boost a Faction") + "\n" # LANG: Boost faction mission objective
                    case MissionType.EXPAND: result += "º " + _("Expand from a System") + "\n" # LANG: Expand faction mission objective
                    case MissionType.REDUCE: result += "º " + _("Reduce a Faction") + "\n" # LANG: Reduce faction mission objective
                    case MissionType.RETREAT: result += "º " + _("Retreat a Faction from a System") + "\n" # LANG: Retreat faction mission objective
                    case MissionType.EQUALISE: result += "º " + _("Equalise two Factions") + "\n" # LANG: Equalise factions mission objective

            if mission_description:
                result += "› " + mission_description + "\n"

            for target in mission.get('targets', []):
                target_system: str|dict|None = target.get('system')
                if target_system == "" or target_system is None:
                    target_system = mission_system
                elif isinstance(target_system, str): # API <= v1.7.0 TODO Remove after API v1.7.0 is obsolete
                    target_system = {'name': target_system, 'x': 0, 'y': 0, 'z': 0}
                target_system_name: str = target_system.get('name', _('Unknown')) # LANG: Unknown system name
                target_faction: str|None = target.get('faction')
                if target_faction == "" or target_faction is None: target_faction = mission_faction
                target_station: str|None = target.get('station')
                system_activity: dict|None = mission_activity.get_system_by_name(target_system_name)
                faction_activity: dict|None = None if system_activity is None else get_by_path(system_activity, ['Factions', target_faction])
                status: str
                target_overall: int

                match target.get('type'):
                    case MissionTargetType.VISIT:
                        if target_station:
                            # Progress on 'visit station' targets is handled server-side
                            status, target_overall = self._get_status(target, discord, numeric=False)
                            result += "  " + _("{status} Access the market in station '{target_station}' in '{target_system}'").format(status=status, target_station=target_station, target_system=target_system_name) + "\n" # LANG: Mission to access a market in a station
                        else:
                            # Progress on 'visit system' targets is handled server-side
                            status, target_overall = self._get_status(target, discord, numeric=False)
                            result += "  " + _("{status} Visit system '{target_system}'").format(status=status, target_system=target_system_name) + "\n" # LANG: Mission to visit a system

                    case MissionTargetType.INF:
                        progress_individual: int|None = None if faction_activity is None else \
                            sum((1 if k == 'm' else int(k)) * int(v) for k, v in faction_activity['MissionPoints'].items()) + \
                            sum((1 if k == 'm' else int(k)) * int(v) for k, v in faction_activity['MissionPointsSecondary'].items())
                        status, target_overall = self._get_status(target, discord, progress_individual=progress_individual, label="INF")
                        if target_overall > 0:
                            result += "  " + _("{status} Boost '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system_name) + "\n" # LANG: Mission to boost a faction in a system
                        elif target_overall < 0:
                            result += "  " + _("{status} Undermine '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system_name) + "\n" # LANG: Mission to undermine a faction in a system
                        else:
                            result += "  " + _("{status} Boost '{target_faction}' in '{target_system}' with as much INF as possible").format(status=status, target_faction=target_faction, target_system=target_system_name) + "\n" # LANG: Mission to boost a faction in a system with no specific target
                    case MissionTargetType.BV:
                        progress_individual: int|None = None if faction_activity is None else faction_activity.get('Bounties')
                        status, target_overall = self._get_status(target, discord, progress_individual=progress_individual, label="CR")
                        result += "  " + _("{status} Bounty Vouchers for '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system_name) + "\n" # LANG: Mission to collect bounty vouchers for a faction in a system

                    case MissionTargetType.CB:
                        progress_individual: int|None = None if faction_activity is None else faction_activity.get('CombatBonds')
                        status, target_overall = self._get_status(target, discord, progress_individual=progress_individual, label="CR")
                        result += "  " + _("{status} Combat Bonds for '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system_name) + "\n" # LANG: Mission to collect combat bonds for a faction in a system

                    case MissionTargetType.EXPL:
                        progress_individual: int|None = None if faction_activity is None else faction_activity.get('CartData')
                        status, target_overall = self._get_status(target, discord, progress_individual=progress_individual, label="CR")
                        result += "  " + _("{status} Exploration Data for '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system_name) + "\n" # LANG: Mission to collect exploration data for a faction in a system

                    case MissionTargetType.TRADE_PROFIT:
                        progress_individual: int|None = None if faction_activity is None else sum(int(d['profit']) for d in faction_activity['TradeSell'])
                        status, target_overall = self._get_status(target, discord, progress_individual=progress_individual, label="CR")
                        result += "  " + _("{status} Trade Profit for '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system_name) + "\n" # LANG: Mission to collect trade profit for a faction in a system

                    case MissionTargetType.BM_PROF:
                        progress_individual: int|None = None if faction_activity is None else faction_activity.get('BlackMarketProfit')
                        status, target_overall = self._get_status(target, discord, progress_individual=progress_individual, label="CR")
                        result += "  " + _("{status} Black Market Profit for '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system_name) + "\n" # LANG: Mission to collect black market profit for a faction in a system

                    case MissionTargetType.GROUND_CZ:
                        progress_individual: int|None = None if faction_activity is None else sum(faction_activity.get('GroundCZ', {}).values())
                        status, target_overall = self._get_status(target, discord, progress_individual=progress_individual, label="wins")
                        result += "  " + _("{status} Fight for '{target_faction}' at on-ground CZs in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system_name) + "\n" # LANG: Mission to fight for a faction at on-ground CZs in a system

                        for settlement in target.get('settlements', []):
                            settlement_name: str|None = settlement.get('name')
                            if settlement_name is None: settlement_name = _("Unknown") # LANG: Unknown settlement name
                            settlement_activity: dict|None = None if faction_activity is None else get_by_path(faction_activity, ['GroundCZSettlements', settlement_name], None)
                            progress_individual: int|None = None if settlement_activity is None else settlement_activity.get('count')
                            status, target_overall = self._get_status(settlement, discord, progress_individual=progress_individual, label="wins")
                            result += "    " + _("{status} Fight at '{settlement_name}'").format(status=status, settlement_name=settlement_name) + "\n" # LANG: Mission to fight at a settlement

                    case MissionTargetType.SPACE_CZ:
                        progress_individual: int|None = None if faction_activity is None else sum(faction_activity.get('SpaceCZ', {}).values())
                        status, target_overall = self._get_status(target, discord, progress_individual=progress_individual, label="wins")
                        result += "  " + _("{status} Fight for '{target_faction}' at in-space CZs in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system_name) + "\n" # LANG: Mission to fight for a faction at in-space CZs in a system

                    case MissionTargetType.MURDER:
                        progress_individual: int|None = None if faction_activity is None else faction_activity.get('Murdered')
                        status, target_overall = self._get_status(target, discord, progress_individual=progress_individual, label="kills")
                        result += "  " + _("{status} Murder '{target_faction}' ships in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system_name) + "\n" # LANG: Mission to murder ships for a faction in a system

                    case MissionTargetType.MISSION_FAIL:
                        progress_individual: int|None = None if faction_activity is None else faction_activity.get('MissionFailed')
                        status, target_overall = self._get_status(target, discord, progress_individual=progress_individual, label="fails")
                        result += "  " + _("{status} Fail missions against '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system_name) + "\n" # LANG: Mission to fail missions against a faction in a system

        return result


    def _get_status(self, target: dict, discord: bool, numeric: bool = True, progress_individual: int|None = None, label: str|None = None) -> tuple[str, int]:
        """Build a string showing the status of a particular mission or sub-mission, showing both overall and individual progress

        Args:
            target (dict): A dict containing information about the mission or sub-mission, including global progress from server.
            discord (bool): If True, format for Discord.
            numeric (bool): If True, track as progress towards a numeric target. Defaults to True.
            progress_individual (int | None, optional: Progress made by user. Defaults to None.
            label (str | None, optional): A label suffix for the values. Defaults to None.

        Returns:
            tuple[str, int]: The description and the numeric target value
        """
        try:
            target_overall: int = int(target.get('targetoverall', 0))
        except ValueError:
            target_overall: int = 0

        try:
            target_individual: int = int(target.get('targetindividual', 0))
        except ValueError:
            target_individual: int = 0

        try:
            progress_overall: int|None = int(target.get('progress', 0))
        except ValueError:
            progress_overall: int|None = 0

        if target_overall > 0 and target_individual == 0:
            # If no individual target is set, use the overall target
            target_individual = target_overall

        # Calculate overall completeness
        complete_overall: bool = False
        if progress_overall is not None and ( \
             (numeric and target_overall > 0 and progress_overall >= target_overall) or \
             (numeric and target_overall < 0 and progress_overall <= target_overall) or \
             (not numeric and progress_overall > 0)):
            # For numeric targets, positive or negative - if we've met or exceeded the target then mark as done
            # For non-numeric targets - if we've made any progress, mark as done
            complete_overall = True

        # Calculate individual completeness
        complete_individual: bool = False
        if progress_individual is not None and ( \
             (numeric and target_individual > 0 and progress_individual >= target_individual) or \
             (numeric and target_individual < 0 and progress_individual <= target_individual) or \
             (not numeric and progress_individual > 0)):
            # For numeric targets, positive or negative - if we've met or exceeded the target then mark as done
            # For non-numeric targets - if we've made any progress, mark as done
            complete_individual = True
        elif progress_individual is None:
            # If no individual progress is passed in, progress is not tracked client side for this target, so use
            # the overall progress instead
            complete_individual = complete_overall
            progress_individual = 0

        if complete_overall or complete_individual:
            # If the target is complete, just show an indicator
            # [√]
            return (f"[✓]" if discord else "[√]"), target_overall
        elif not numeric:
            # If the target is not complete and not numeric, just show an indicator
            # [•]
            return f"[•]", target_overall
        else:
            # Otherwise build a progress report including individual and overall progress:
            # [123 / 456 | 789 / 1000 CR] or
            # [123 / 456 | 789 / ∞ CR] or
            # [123 / ∞ | 789 / ∞ CR]
            result: str = "["

            if target_individual == 0:
                result += f"{human_format(progress_individual)} / ∞ | "
            else:
                result += f"{human_format(progress_individual)} / {human_format(target_individual)} | "

            if target_overall == 0:
                result += f"{human_format(progress_overall)} / ∞"
            else:
                result += f"{human_format(progress_overall)} / {human_format(target_overall)}"

            result += f" {label}]"

            return result, target_overall


    def get_overlay_objectives(self) -> str:
        """Get objectives formatted for overlay display (enhanced text-based, everything expanded)

        Returns:
            str: Formatted objectives for overlay
        """
        result: str = ""
        if self.api is None: return result

        # We have to sort by priority first, assuming that no priority is 0
        self.api.objectives.sort(key=lambda m: int(m.get('priority', '0')), reverse=True)

        for idx, mission in enumerate(self.api.objectives):
            mission_title: str|None = mission.get('title')
            mission_priority: str|None = mission.get('priority', '0')
            mission_description: str|None = mission.get('description')
            mission_system: str|None = mission.get('system')
            if mission_system is None: mission_system = _("Unknown") # LANG: Unknown system name
            mission_faction: str|None = mission.get('faction')
            if mission_faction is None: mission_faction = _("Unknown") # LANG: Unknown faction name
            mission_startdate: datetime = datetime.strptime(mission.get('startdate', datetime.now(UTC).strftime(DATETIME_FORMAT_API)), DATETIME_FORMAT_API)
            mission_startdate = mission_startdate.replace(tzinfo=UTC)
            mission_enddate: datetime = datetime.strptime(mission.get('enddate', datetime(3999, 12, 31, 23, 59, 59, 0, UTC).strftime(DATETIME_FORMAT_API)), DATETIME_FORMAT_API)
            mission_enddate = mission_enddate.replace(tzinfo=UTC)
            if mission_enddate < datetime.now(UTC): continue
            mission_activity: Activity = self.bgstally.activity_manager.query_activity(mission_startdate)

            # Add separator between objectives
            if idx > 0:
                result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            # Priority stars
            priority_stars: str = self._get_priority_stars(mission_priority)

            # Title section
            if mission_title:
                result += f"{priority_stars} {mission_title}\n"
            else:
                match mission.get('type'):
                    case MissionType.RECON: result += f"{priority_stars} " + _("Recon Mission") + "\n" # LANG: Recon mission objective
                    case MissionType.WIN_WAR: result += f"{priority_stars} " + _("Win a War") + "\n" # LANG: Win war mission objective
                    case MissionType.DRAW_WAR: result += f"{priority_stars} " + _("Draw a War") + "\n" # LANG: Draw war mission objective
                    case MissionType.WIN_ELECTION: result += f"{priority_stars} " + _("Win an Election") + "\n" # LANG: Win election mission objective
                    case MissionType.DRAW_ELECTION: result += f"{priority_stars} " + _("Draw an Election") + "\n" # LANG: Draw election mission objective
                    case MissionType.BOOST: result += f"{priority_stars} " + _("Boost a Faction") + "\n" # LANG: Boost faction mission objective
                    case MissionType.EXPAND: result += f"{priority_stars} " + _("Expand from a System") + "\n" # LANG: Expand faction mission objective
                    case MissionType.REDUCE: result += f"{priority_stars} " + _("Reduce a Faction") + "\n" # LANG: Reduce faction mission objective
                    case MissionType.RETREAT: result += f"{priority_stars} " + _("Retreat a Faction from a System") + "\n" # LANG: Retreat faction mission objective
                    case MissionType.EQUALISE: result += f"{priority_stars} " + _("Equalise two Factions") + "\n" # LANG: Equalise factions mission objective

            # Metadata: Type, System, Faction
            mission_type_str = mission.get('type', _("Unknown")) # LANG: Unknown mission type
            result += f"Type: {mission_type_str} | System: {mission_system} | Faction: {mission_faction}\n"

            # Dates
            start_str = mission_startdate.strftime("%Y-%m-%d") if mission_startdate else "-"
            end_str = mission_enddate.strftime("%Y-%m-%d") if mission_enddate and mission_enddate.year < 3999 else "-"
            if start_str != "-" or end_str != "-":
                result += f"Start: {start_str} | End: {end_str}\n"

            # Description
            #if mission_description:
            #    result += "─────────────────────────────────────────────────\n"
            #    result += f"{mission_description}\n"

            # Targets section
            if mission.get('targets'):
                result += "─────────────────────────────────────────────────\n"
                result += _("Targets:") + "\n" # LANG: Targets section header

                for target in mission.get('targets', []):
                    target_system: str|None = target.get('system')
                    if target_system == "" or target_system is None: target_system = mission_system
                    target_faction: str|None = target.get('faction')
                    if target_faction == "" or target_faction is None: target_faction = mission_faction
                    target_station: str|None = target.get('station')
                    system_activity: dict|None = mission_activity.get_system_by_name(target_system)
                    faction_activity: dict|None = None if system_activity is None else get_by_path(system_activity, ['Factions', target_faction])
                    status: str
                    target_overall: int

                    match target.get('type'):
                        case MissionTargetType.VISIT:
                            if target_station:
                                status, target_overall = self._get_status(target, False, numeric=False)
                                result += "  " + _("{status} Access the market in station '{target_station}' in '{target_system}'").format(status=status, target_station=target_station, target_system=target_system) + "\n"
                            else:
                                status, target_overall = self._get_status(target, False, numeric=False)
                                result += "  " + _("{status} Visit system '{target_system}'").format(status=status, target_system=target_system) + "\n"

                        case MissionTargetType.INF:
                            progress_individual: int|None = None if faction_activity is None else \
                                sum((1 if k == 'm' else int(k)) * int(v) for k, v in faction_activity['MissionPoints'].items()) + \
                                sum((1 if k == 'm' else int(k)) * int(v) for k, v in faction_activity['MissionPointsSecondary'].items())
                            status, target_overall = self._get_status(target, False, progress_individual=progress_individual, label="INF")
                            if target_overall > 0:
                                result += "  " + _("{status} Boost '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system) + "\n"
                            elif target_overall < 0:
                                result += "  " + _("{status} Undermine '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system) + "\n"
                            else:
                                result += "  " + _("{status} Boost '{target_faction}' in '{target_system}' with as much INF as possible").format(status=status, target_faction=target_faction, target_system=target_system) + "\n"

                        case MissionTargetType.BV:
                            progress_individual: int|None = None if faction_activity is None else faction_activity.get('Bounties')
                            status, target_overall = self._get_status(target, False, progress_individual=progress_individual, label="CR")
                            result += "  " + _("{status} Bounty Vouchers for '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system) + "\n"

                        case MissionTargetType.CB:
                            progress_individual: int|None = None if faction_activity is None else faction_activity.get('CombatBonds')
                            status, target_overall = self._get_status(target, False, progress_individual=progress_individual, label="CR")
                            result += "  " + _("{status} Combat Bonds for '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system) + "\n"

                        case MissionTargetType.EXPL:
                            progress_individual: int|None = None if faction_activity is None else faction_activity.get('CartData')
                            status, target_overall = self._get_status(target, False, progress_individual=progress_individual, label="CR")
                            result += "  " + _("{status} Exploration Data for '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system) + "\n"

                        case MissionTargetType.TRADE_PROFIT:
                            progress_individual: int|None = None if faction_activity is None else sum(int(d['profit']) for d in faction_activity['TradeSell'])
                            status, target_overall = self._get_status(target, False, progress_individual=progress_individual, label="CR")
                            result += "  " + _("{status} Trade Profit for '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system) + "\n"

                        case MissionTargetType.BM_PROF:
                            progress_individual: int|None = None if faction_activity is None else faction_activity.get('BlackMarketProfit')
                            status, target_overall = self._get_status(target, False, progress_individual=progress_individual, label="CR")
                            result += "  " + _("{status} Black Market Profit for '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system) + "\n"

                        case MissionTargetType.GROUND_CZ:
                            progress_individual: int|None = None if faction_activity is None else sum(faction_activity.get('GroundCZ', {}).values())
                            status, target_overall = self._get_status(target, False, progress_individual=progress_individual, label="wins")
                            result += "  " + _("{status} Fight for '{target_faction}' at on-ground CZs in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system) + "\n"

                            for settlement in target.get('settlements', []):
                                settlement_name: str|None = settlement.get('name')
                                if settlement_name is None: settlement_name = _("Unknown") # LANG: Unknown settlement name
                                settlement_activity: dict|None = None if faction_activity is None else get_by_path(faction_activity, ['GroundCZSettlements', settlement_name], None)
                                progress_individual: int|None = None if settlement_activity is None else settlement_activity.get('count')
                                status, target_overall = self._get_status(settlement, False, progress_individual=progress_individual, label="wins")
                                result += "    " + _("{status} Fight at '{settlement_name}'").format(status=status, settlement_name=settlement_name) + "\n"

                        case MissionTargetType.SPACE_CZ:
                            progress_individual: int|None = None if faction_activity is None else sum(faction_activity.get('SpaceCZ', {}).values())
                            status, target_overall = self._get_status(target, False, progress_individual=progress_individual, label="wins")
                            result += "  " + _("{status} Fight for '{target_faction}' at in-space CZs in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system) + "\n"

                        case MissionTargetType.MURDER:
                            progress_individual: int|None = None if faction_activity is None else faction_activity.get('Murdered')
                            status, target_overall = self._get_status(target, False, progress_individual=progress_individual, label="kills")
                            result += "  " + _("{status} Murder '{target_faction}' ships in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system) + "\n"

                        case MissionTargetType.MISSION_FAIL:
                            progress_individual: int|None = None if faction_activity is None else faction_activity.get('MissionFailed')
                            status, target_overall = self._get_status(target, False, progress_individual=progress_individual, label="fails")
                            result += "  " + _("{status} Fail missions against '{target_faction}' in '{target_system}'").format(status=status, target_faction=target_faction, target_system=target_system) + "\n"

            result += "\n"

        return result

