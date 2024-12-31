from datetime import datetime, UTC
from enum import Enum

from bgstally.activity import Activity
from bgstally.constants import DATETIME_FORMAT_API
from bgstally.debug import Debug
from bgstally.utils import get_by_path, human_format


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
    Handles the management of objectives
    """
    def __init__(self, bgstally):
        self.bgstally = bgstally

        self._objectives: list[dict] = []


    def get_objectives(self) -> list:
        """Get the available objectives

        Returns:
            list: current list of objectives
        """
        return self._objectives


    def set_objectives(self, objectives: list):
        """Set the current objectives

        Args:
            objectives (dict): The list of objectives
        """
        self._objectives = objectives


    def get_human_readable_objectives(self) -> str:
        """Get the objectives nicely formatted

        Returns:
            str: The human readable objectives
        """
        result: str = ""

        for mission in self._objectives:
            mission_title: str|None = mission.get('title')
            mission_description: str|None = mission.get('description')
            mission_system: str|None = mission.get('system')
            mission_faction: str|None = mission.get('faction')
            mission_startdate: datetime = datetime.strptime(mission.get('startdate', datetime.now(UTC).strftime(DATETIME_FORMAT_API)), DATETIME_FORMAT_API)
            mission_enddate: datetime|None = datetime.strptime(mission.get('enddate', None), DATETIME_FORMAT_API)
            if mission_enddate < datetime.now(UTC): continue
            mission_activity: Activity = self.bgstally.activity_manager.query_activity(mission_startdate)

            if mission_title:
                result += "º " + mission_title + "\n"
            else:
                match mission.get('type'):
                    case MissionType.RECON: result += "º " + "Recon Mission" + "\n"
                    case MissionType.WIN_WAR: result += "º " + "Win a War" + "\n"
                    case MissionType.DRAW_WAR: result += "º " + "Draw a War" + "\n"
                    case MissionType.WIN_ELECTION: result += "º " + "Win an Election" + "\n"
                    case MissionType.DRAW_ELECTION: result += "º " + "Draw an Election" + "\n"
                    case MissionType.BOOST: result += "º " + "Boost a Faction" + "\n"
                    case MissionType.EXPAND: result += "º " + "Expand from a System" + "\n"
                    case MissionType.REDUCE: result += "º " + "Reduce a Faction" + "\n"
                    case MissionType.RETREAT: result += "º " + "Retreat a Faction from a System" + "\n"
                    case MissionType.EQUALISE: result += "º " + "Equalise two Factions" + "\n"

            if mission_description:
                result += "› " + mission_description + "\n"

            for target in mission.get('targets', []):
                target_system: str|None = target.get('system', mission_system)
                target_faction: str|None = target.get('faction', mission_faction)
                target_station: str|None = target.get('station')
                system_activity: dict|None = mission_activity.get_system_by_name(target_system)
                faction_activity: dict|None = None if system_activity is None else get_by_path(system_activity, ['Factions', target_faction])
                status: str
                value: int

                match target.get('type'):
                    case MissionTargetType.VISIT:
                        if target_station:
                            # Progress on 'visit station' targets is handled server-side
                            server_progress: int|None = int(target.get('progress', 0))
                            status, value = self._get_status(target, user_progress=server_progress, numeric=False)
                            result += f"  {status} Access the market in station '{target_station}' in '{target_system}'" + "\n"
                        else:
                            # Progress on 'visit system' targets is handled server-side
                            server_progress: int|None = int(target.get('progress', 0))
                            status, value = self._get_status(target, user_progress=server_progress, numeric=False)
                            result += f"  {status} Visit system '{target_system}'" + "\n"

                    case MissionTargetType.INF:
                        user_progress: int|None = None if faction_activity is None else \
                            sum((1 if k == 'm' else int(k)) * int(v) for k, v in faction_activity['MissionPoints'].items()) + \
                            sum((1 if k == 'm' else int(k)) * int(v) for k, v in faction_activity['MissionPointsSecondary'].items())
                        status, value = self._get_status(target, user_progress=user_progress, label="INF")
                        if value > 0:
                            result += f"  {status} Boost '{target_faction}' in '{target_system}'" + "\n"
                        elif value < 0:
                            result += f"  {status} Undermine '{target_faction}' in '{target_system}'" + "\n"
                        else:
                            result += f"  {status} Boost '{target_faction}' in '{target_system}' with as much INF as possible" + "\n"

                    case MissionTargetType.BV:
                        user_progress: int|None = None if faction_activity is None else faction_activity.get('Bounties')
                        status, value = self._get_status(target, user_progress=user_progress, label="CR")
                        result += f"  {status} Bounty Vouchers for '{target_faction}' in '{target_system}'" + "\n"

                    case MissionTargetType.CB:
                        user_progress: int|None = None if faction_activity is None else faction_activity.get('CombatBonds')
                        status, value = self._get_status(target, user_progress=user_progress, label="CR")
                        result += f"  {status} Combat Bonds for '{target_faction}' in '{target_system}'" + "\n"

                    case MissionTargetType.EXPL:
                        user_progress: int|None = None if faction_activity is None else faction_activity.get('CartData')
                        status, value = self._get_status(target, user_progress=user_progress, label="CR")
                        result += f"  {status} Exploration Data for '{target_faction}' in '{target_system}'" + "\n"

                    case MissionTargetType.TRADE_PROFIT:
                        user_progress: int|None = None if faction_activity is None else sum(int(d['profit']) for d in faction_activity['TradeSell'])
                        status, value = self._get_status(target, user_progress=user_progress, label="CR")
                        result += f"  {status} Trade Profit for '{target_faction}' in '{target_system}'" + "\n"

                    case MissionTargetType.BM_PROF:
                        user_progress: int|None = None if faction_activity is None else faction_activity.get('BlackMarketProfit')
                        status, value = self._get_status(target, user_progress=user_progress, label="CR")
                        result += f"  {status} Black Market Profit for '{target_faction}' in '{target_system}'" + "\n"

                    case MissionTargetType.GROUND_CZ:
                        user_progress: int|None = None if faction_activity is None else sum(faction_activity.get('GroundCZ', {}).values())
                        status, value = self._get_status(target, user_progress=user_progress, label="wins")
                        result += f"  {status} Fight for '{target_faction}' at on-ground CZs in '{target_system}'" + "\n"

                        for settlement in target.get('settlements', []):
                            settlement_name: str|None = settlement.get('name')
                            settlement_activity: dict|None = None if faction_activity is None else get_by_path(faction_activity, ['GroundCZSettlements', settlement_name], None)
                            user_progress: int|None = None if settlement_activity is None else settlement_activity.get('count')
                            status, value = self._get_status(settlement, user_progress=user_progress, label="wins")
                            result += f"    {status} Fight at '{settlement_name}'" + "\n"

                    case MissionTargetType.SPACE_CZ:
                        user_progress: int|None = None if faction_activity is None else sum(faction_activity.get('SpaceCZ', {}).values())
                        status, value = self._get_status(target, user_progress=user_progress, label="wins")
                        result += f"  {status} Fight for '{target_faction}' at in-space CZs in '{target_system}'" + "\n"

                    case MissionTargetType.MURDER:
                        user_progress: int|None = None if faction_activity is None else faction_activity.get('Murdered')
                        status, value = self._get_status(target, user_progress=user_progress, label="kills")
                        result += f"  {status} Murder '{target_faction}' ships in '{target_system}'" + "\n"

                    case MissionTargetType.MISSION_FAIL:
                        user_progress: int|None = None if faction_activity is None else faction_activity.get('MissionFailed')
                        status, value = self._get_status(target, user_progress=user_progress, label="fails")
                        result += f"  {status} Fail missions against '{target_faction}' in '{target_system}'" + "\n"


        return result


    def _get_status(self, target: dict, numeric: bool = True, user_progress: int|None = None, label: str|None = None) -> tuple[str, int]:
        """Get a string showing the status of a particular mission or sub-mission

        Args:
            target (dict): A dict containing information about the mission or sub-mission, including global progress from server.
            just_flag (bool): If True, only show a status flag, not the numeric progress. Defaults to False.
            numeric (bool): If True, track as progress towards a numeric target. Defaults to True.
            user_progress (int | None, optional: Progress made by user. Defaults to None.
            label (str | None, optional): A label suffix for the values. Defaults to None.

        Returns:
            tuple[str, int]: The description and the numeric target value
        """
        try:
            value: int = int(target.get('value', 0))
        except ValueError:
            value: int = 0

        try:
            # For the moment, just show user progess. May want to show both global and user progress in future.
            progress: int|None = user_progress
        except ValueError:
            progress: int|None = 0

        if value == 0 and numeric:
            flag: str = "∞"
            complete: bool = False
        elif progress is not None and ( \
             (numeric and value > 0 and progress >= value) or \
             (numeric and value < 0 and progress <= value) or \
             (not numeric and progress > 0)):
            flag: str = "√ [done]"
            complete: bool = True
        else:
            flag: str = "•"
            complete: bool = False

        if complete or not numeric:
            # Don't show target value
            return flag, value
        elif value == 0:
            # Infinite target value
            if progress: return f"{flag} [{human_format(progress)} / ∞ {label}]", value
            else: return f"{flag} [∞ {label}]", value
        else:
            # Integer target value
            if progress: return f"{flag} [{human_format(progress)} / {human_format(value)} {label}]", value
            else: return f"{flag} [{human_format(progress)} / {human_format(value)} {label}]", value
