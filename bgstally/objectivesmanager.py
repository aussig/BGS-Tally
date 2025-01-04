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
            mission_startdate = mission_startdate.replace(tzinfo=UTC)
            mission_enddate: datetime = datetime.strptime(mission.get('enddate', datetime(3999, 12, 31, 23, 59, 59, 0, UTC).strftime(DATETIME_FORMAT_API)), DATETIME_FORMAT_API)
            mission_enddate = mission_enddate.replace(tzinfo=UTC)
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
                target_overall: int

                match target.get('type'):
                    case MissionTargetType.VISIT:
                        if target_station:
                            # Progress on 'visit station' targets is handled server-side
                            status, target_overall = self._get_status(target, numeric=False)
                            result += f"  {status} Access the market in station '{target_station}' in '{target_system}'" + "\n"
                        else:
                            # Progress on 'visit system' targets is handled server-side
                            status, target_overall = self._get_status(target, numeric=False)
                            result += f"  {status} Visit system '{target_system}'" + "\n"

                    case MissionTargetType.INF:
                        progress_individual: int|None = None if faction_activity is None else \
                            sum((1 if k == 'm' else int(k)) * int(v) for k, v in faction_activity['MissionPoints'].items()) + \
                            sum((1 if k == 'm' else int(k)) * int(v) for k, v in faction_activity['MissionPointsSecondary'].items())
                        status, target_overall = self._get_status(target, progress_individual=progress_individual, label="INF")
                        if target_overall > 0:
                            result += f"  {status} Boost '{target_faction}' in '{target_system}'" + "\n"
                        elif target_overall < 0:
                            result += f"  {status} Undermine '{target_faction}' in '{target_system}'" + "\n"
                        else:
                            result += f"  {status} Boost '{target_faction}' in '{target_system}' with as much INF as possible" + "\n"

                    case MissionTargetType.BV:
                        progress_individual: int|None = None if faction_activity is None else faction_activity.get('Bounties')
                        status, target_overall = self._get_status(target, progress_individual=progress_individual, label="CR")
                        result += f"  {status} Bounty Vouchers for '{target_faction}' in '{target_system}'" + "\n"

                    case MissionTargetType.CB:
                        progress_individual: int|None = None if faction_activity is None else faction_activity.get('CombatBonds')
                        status, target_overall = self._get_status(target, progress_individual=progress_individual, label="CR")
                        result += f"  {status} Combat Bonds for '{target_faction}' in '{target_system}'" + "\n"

                    case MissionTargetType.EXPL:
                        progress_individual: int|None = None if faction_activity is None else faction_activity.get('CartData')
                        status, target_overall = self._get_status(target, progress_individual=progress_individual, label="CR")
                        result += f"  {status} Exploration Data for '{target_faction}' in '{target_system}'" + "\n"

                    case MissionTargetType.TRADE_PROFIT:
                        progress_individual: int|None = None if faction_activity is None else sum(int(d['profit']) for d in faction_activity['TradeSell'])
                        status, target_overall = self._get_status(target, progress_individual=progress_individual, label="CR")
                        result += f"  {status} Trade Profit for '{target_faction}' in '{target_system}'" + "\n"

                    case MissionTargetType.BM_PROF:
                        progress_individual: int|None = None if faction_activity is None else faction_activity.get('BlackMarketProfit')
                        status, target_overall = self._get_status(target, progress_individual=progress_individual, label="CR")
                        result += f"  {status} Black Market Profit for '{target_faction}' in '{target_system}'" + "\n"

                    case MissionTargetType.GROUND_CZ:
                        progress_individual: int|None = None if faction_activity is None else sum(faction_activity.get('GroundCZ', {}).values())
                        status, target_overall = self._get_status(target, progress_individual=progress_individual, label="wins")
                        result += f"  {status} Fight for '{target_faction}' at on-ground CZs in '{target_system}'" + "\n"

                        for settlement in target.get('settlements', []):
                            settlement_name: str|None = settlement.get('name')
                            settlement_activity: dict|None = None if faction_activity is None else get_by_path(faction_activity, ['GroundCZSettlements', settlement_name], None)
                            progress_individual: int|None = None if settlement_activity is None else settlement_activity.get('count')
                            status, target_overall = self._get_status(settlement, progress_individual=progress_individual, label="wins")
                            result += f"    {status} Fight at '{settlement_name}'" + "\n"

                    case MissionTargetType.SPACE_CZ:
                        progress_individual: int|None = None if faction_activity is None else sum(faction_activity.get('SpaceCZ', {}).values())
                        status, target_overall = self._get_status(target, progress_individual=progress_individual, label="wins")
                        result += f"  {status} Fight for '{target_faction}' at in-space CZs in '{target_system}'" + "\n"

                    case MissionTargetType.MURDER:
                        progress_individual: int|None = None if faction_activity is None else faction_activity.get('Murdered')
                        status, target_overall = self._get_status(target, progress_individual=progress_individual, label="kills")
                        result += f"  {status} Murder '{target_faction}' ships in '{target_system}'" + "\n"

                    case MissionTargetType.MISSION_FAIL:
                        progress_individual: int|None = None if faction_activity is None else faction_activity.get('MissionFailed')
                        status, target_overall = self._get_status(target, progress_individual=progress_individual, label="fails")
                        result += f"  {status} Fail missions against '{target_faction}' in '{target_system}'" + "\n"


        return result


    def _get_status(self, target: dict, numeric: bool = True, progress_individual: int|None = None, label: str|None = None) -> tuple[str, int]:
        """Build a string showing the status of a particular mission or sub-mission, showing both overall and individual progress

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
            return f"[√]", target_overall
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

