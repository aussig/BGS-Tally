from enum import Enum

from bgstally.utils import human_format

class MissionTargetType(str, Enum):
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

        # Create list of instances of each subclass of FormatterInterface
        self._objectives: list[dict] = []


    def get_objectives(self) -> list:
        """Get the available objectives

        Returns:
            dict: key = formatter class name, value = formatter public name
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
            for mission in objective.get('missions', []):
                result += mission.get('title', "<untitled mission>") + " (" + mission.get('type', "") + ")" + "\n"
                result += "  " + mission.get('description', "") + "\n"
                target_system: str = mission.get('system', "<unknown system>")
                faction: str = mission.get('faction', "<unknown faction>")
                opposing_faction: str = mission.get('opposing_faction', "<unknown faction>")

                for target in mission.get('global_targets', []):
                    target_faction: str = target.get('faction') if target.get('faction') else faction
                    opposing_target_faction: str = target.get('faction') if target.get('faction') else opposing_faction

                    try:
                        value: int = int(target.get('value', 0))
                    except ValueError:
                        value: int = 0

                    match target.get('type'):
                        case MissionTargetType.INF:
                            if value > 0:
                                result += f"    Boost '{target_faction}' in '{target_system}' by {value} INF" + "\n"
                            elif value < 0:
                                result += f"    Undermine '{target_faction}' in '{target_system}' by {value} INF" + "\n"
                            else:
                                result += f"    Boost '{target_faction}' in '{target_system}' with as much INF as possible" + "\n"

                        case MissionTargetType.BV:
                            result += f"    Hand in {human_format(value)} CR of Bounty Vouchers for '{target_faction}' in '{target_system}'" + "\n"

                        case MissionTargetType.CB:
                            result += f"    Hand in {human_format(value)} CR of Combat Bonds for '{target_faction}' in '{target_system}'" + "\n"

                        case MissionTargetType.EXPL:
                            result += f"    Hand in {human_format(value)} CR of Exploration Data for '{target_faction}' in '{target_system}'" + "\n"

                        case MissionTargetType.TRADE_PROFIT:
                            result += f"    Generate {human_format(value)} CR of Trade Profit '{target_faction}' in '{target_system}'" + "\n"

                        case MissionTargetType.BM_PROF:
                            result += f"    Generate {human_format(value)} CR of Black Market Profit '{target_faction}' in '{target_system}'" + "\n"

                        case MissionTargetType.GROUND_CZ:
                            result += f"    Fight for '{target_faction}' at on-ground CZs in '{target_system}' ({value} wins)" + "\n"

                            if target.get('settlements'):
                                for settlement in target.get('settlements', []):
                                    settlement_value: str = settlement.get('value', "0")
                                    result += f"      Fight at '{settlement.get('name', '<unknown>')} ({settlement_value} wins)" + "\n"

                        case MissionTargetType.SPACE_CZ:
                            result += f"    Fight for '{target_faction}' at in-space CZs in '{target_system}' ({value} wins)" + "\n"

                        case MissionTargetType.MURDER:
                            result += f"    Murder {value} ships of the '{opposing_target_faction}' in '{target_system}'" + "\n"

                        case MissionTargetType.MISSION_FAIL:
                            result += f"    Fail {value} missions for the '{opposing_target_faction}' in '{target_system}'" + "\n"

        return result
