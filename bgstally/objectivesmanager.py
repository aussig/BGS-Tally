from enum import Enum

from bgstally.utils import human_format

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

        for objective in self._objectives:
            result += objective.get('title', "<untitled objective>") + "\n"
            result += "  › " + objective.get('description', "") + "\n"

            for mission in objective.get('missions', []):
                mission_system: str = mission.get('system')
                mission_station: str = mission.get('station')
                mission_faction: str = mission.get('faction')

                match mission.get('type'):
                    case MissionType.RECON: result += "  º " + "Recon Mission" + "\n"
                    case MissionType.WIN_WAR: result += "  º " + "Win a War" + "\n"
                    case MissionType.DRAW_WAR: result += "  º " + "Draw a War" + "\n"
                    case MissionType.WIN_ELECTION: result += "  º " + "Win an Election" + "\n"
                    case MissionType.DRAW_ELECTION: result += "  º " + "Draw an Election" + "\n"
                    case MissionType.BOOST: result += "  º " + "Boost a Faction" + "\n"
                    case MissionType.EXPAND: result += "  º " + "Expand from a System" + "\n"
                    case MissionType.REDUCE: result += "  º " + "Reduce a Faction" + "\n"
                    case MissionType.RETREAT: result += "  º " + "Retreat a Faction from a System" + "\n"
                    case MissionType.EQUALISE: result += "  º " + "Equalise two Factions" + "\n"

                for target in mission.get('targets', []):
                    target_system = target.get('system', mission_system)
                    target_station = target.get('station', mission_station)
                    target_faction = target.get('faction', mission_faction)

                    try:
                        value: int = int(target.get('value', 1))
                    except ValueError:
                        value: int = 1
                    try:
                        progress: int = int(target.get('progress', 0))
                    except ValueError:
                        progress: int = 0

                    if value > 0 and progress >= value:
                        flag: str = "√ [done]"
                        complete: bool = True
                    else:
                        flag: str = "•"
                        complete: bool = False

                    match target.get('type'):
                        case MissionTargetType.VISIT:
                            if target_station:
                                result += f"    {flag} Access the market in station '{target_station}' in '{target_system}'" + "\n"
                            else:
                                result += f"    {flag} Visit system '{target_system}'" + "\n"

                        case MissionTargetType.INF:
                            status: str = flag if complete else f"{flag} [{progress} / {value} INF]"
                            if value > 0:
                                result += f"    {status} Boost '{target_faction}' in '{target_system}'" + "\n"
                            elif value < 0:
                                result += f"    {status} Undermine '{target_faction}' in '{target_system}'" + "\n"
                            else:
                                result += f"    {flag} Boost '{target_faction}' in '{target_system}' with as much INF as possible" + "\n"

                        case MissionTargetType.BV:
                            status: str = flag if complete else f"{flag} [{human_format(progress)} / {human_format(value)} CR]"
                            result += f"    {status} Hand in Bounty Vouchers for '{target_faction}' in '{target_system}'" + "\n"

                        case MissionTargetType.CB:
                            status: str = flag if complete else f"{flag} [{human_format(progress)} / {human_format(value)} CR]"
                            result += f"    {status} Hand in Combat Bonds for '{target_faction}' in '{target_system}'" + "\n"

                        case MissionTargetType.EXPL:
                            status: str = flag if complete else f"{flag} [{human_format(progress)} / {human_format(value)} CR]"
                            result += f"    {status} Hand in Exploration Data for '{target_faction}' in '{target_system}'" + "\n"

                        case MissionTargetType.TRADE_PROFIT:
                            status: str = flag if complete else f"{flag} [{human_format(progress)} / {human_format(value)} CR]"
                            result += f"    {status} Generate Trade Profit for '{target_faction}' in '{target_system}'" + "\n"

                        case MissionTargetType.BM_PROF:
                            status: str = flag if complete else f"{flag} [{human_format(progress)} / {human_format(value)} CR]"
                            result += f"    {status} Generate Black Market Profit for '{target_faction}' in '{target_system}'" + "\n"

                        case MissionTargetType.GROUND_CZ:
                            status: str = flag if complete else f"{flag} [{progress} / {value} wins]"
                            result += f"    {status} Fight for '{target_faction}' at on-ground CZs in '{target_system}'" + "\n"

                            if target.get('settlements'):
                                for settlement in target.get('settlements', []):
                                    settlement_value: str = settlement.get('value', "0")
                                    settlement_progress: str = settlement.get('progress', "0")

                                    if settlement_value > 0 and settlement_progress >= settlement_value:
                                        flag: str = "√ [done]"
                                        complete: bool = True
                                    else:
                                        flag: str = "•"
                                        complete: bool = False

                                    status: str = flag if complete else f"{flag} [{settlement_progress} / {settlement_value} wins]"

                                    result += f"      {status} Fight at '{settlement.get('name', '<unknown>')}'" + "\n"

                        case MissionTargetType.SPACE_CZ:
                            status: str = flag if complete else f"{flag} [{progress} / {value} wins]"
                            result += f"    {status} Fight for '{target_faction}' at in-space CZs in '{target_system}'" + "\n"

                        case MissionTargetType.MURDER:
                            status: str = flag if complete else f"{flag} [{progress} / {value} kills]"
                            result += f"    {status} Murder ships of the '{target_faction}' in '{target_system}'" + "\n"

                        case MissionTargetType.MISSION_FAIL:
                            status: str = flag if complete else f"{flag} [{progress} / {value} fails]"
                            result += f"    {status} Fail missions against the '{target_faction}' in '{target_system}'" + "\n"


        return result
