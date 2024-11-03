from datetime import datetime, timedelta, timezone
import time
import traceback
import re
from bgstally.activity import STATES_ELECTION, STATES_WAR, Activity
from bgstally.constants import CheckStates, DiscordActivity
from bgstally.debug import Debug
from bgstally.formatters.default import DefaultActivityFormatter
#from bgstally.formatters.base import FieldActivityFormatterInterface
from bgstally.utils import _, __, human_format, is_number
from thirdparty.colors import *

class CLBActivityFormatter(DefaultActivityFormatter):
    """Activity formatter that outputs Lorum Ipsum
    """

    def __init__(self, bgstally):
        """Instantiate class

        Args:
            bgstally (BGSTally): The BGSTally object
        """
        super().__init__(bgstally)


    def get_name(self) -> str:
        """Get the name of this formatter

        Returns:
            str: The name of this formatter for choosing in the UI
        """
        return 'Celestial Light Brigade'

    def is_visible(self) -> bool:
        """Should this formatter be visible to the user as a choice.

        Returns:
            bool: True if visible, false if not
        """
        return True

    def get_overlay(self, activity: Activity, activity_mode: DiscordActivity, system_names: list = None, lang: str = None) -> str:
        """Get the in-game overlay text for a given instance of Activity. The in-game overlay
        doesn't support any ANSI colouring and very few UTF-8 special characters. Basically,
        only plain text is safe.

        Args:
            activity (Activity): The Activity object containing the activity to post
            activity_mode (DiscordActivity): Determines the type(s) of activity to post
            system_names (list, optional): A list of system names to restrict the output for. If None, all systems are included. Defaults to None.
            lang (str, optional): The language code for this post. Defaults to None.

        Returns:
            str: The output text
        """
        return self._build_text(activity, activity_mode, system_names, lang, False)

    def get_text(self, activity: Activity, activity_mode: DiscordActivity, system_names: list = None, lang: str = None) -> str:
        """Generate formatted text for a given instance of Activity. Must be implemented by subclasses.
        This method is used for getting the text for the 'copy and paste' function, and for direct posting
        to Discord for those Formatters that use text style posts (vs Discord embed style posts)

        Args:
            activity (Activity): The Activity object containing the activity to post
            activity_mode (DiscordActivity): Determines the type(s) of activity to post
            discord (bool, optional): True if the destination is Discord (so can include Discord-specific formatting such
            as ```ansi blocks and UTF8 emoji characters), False if not. Defaults to False.
            system_names (list, optional): A list of system names to restrict the output for. If None, all systems are included. Defaults to None.
            lang (str, optional): The language code for this post. Defaults to None.

        Returns:
            str: The output text
        """
        return self._build_text(activity, activity_mode, system_names, lang, True)

    def get_fields(self, activity: Activity, activity_mode: DiscordActivity, system_names: list = None, lang: str = None) -> list:
        """Generate a list of discord embed fields, conforming to the embed field spec defined here:
        https://birdie0.github.io/discord-webhooks-guide/structure/embed/fields.html - i.e. each field should be a dict
        containing 'name' and 'value' str keys, and optionally an 'inline' bool key

        Args:
            activity (Activity): The Activity object containing the activity to post
            activity_mode (DiscordActivity): Determines the type(s) of activity to post
            system_names (list, optional): A list of system names to restrict the output for. If None, all systems are included. Defaults to None.
            lang (str, optional): The language code for this post. Defaults to None.

        Returns:
            list[dict]: A list of dicts, each containing an embed field containing 'name' and 'value' str keys, and optionally an 'inline' bool key
        """

        discord_fields = []

        for system in sorted(activity.systems.copy().values(), key=lambda d: d['System']): # Use a copy for thread-safe operation
            if system_names is not None and system['System'] not in system_names:
                continue
            system_text: str = ""
            if activity_mode == DiscordActivity.THARGOIDWAR or activity_mode == DiscordActivity.BOTH:
                system_text += self._build_tw_system(system, True, lang)

            if (activity_mode == DiscordActivity.BGS or activity_mode == DiscordActivity.BOTH) and system.get('tw_status') is None:
                for faction in sorted(system['Factions'].values(), key=lambda d: d['Faction']):
                    if faction['Enabled'] != CheckStates.STATE_ON: continue
                    system_text += self._build_faction(faction, True, lang)

            if system_text != "":
#                system_text = system_text.replace("     ", " ")
#                system_text = system_text.replace("   ", "")
                discord_field = {'name': system['System'], 'value': f"```ansi\n{system_text}```"}
                discord_fields.append(discord_field)

        return discord_fields

    #
    # Private functions
    #

    def _build_text(self, activity: Activity, activity_mode: DiscordActivity, system_names: list = None, lang: str = None, discord: bool = True) -> str:
        try:
            text:str = ""
            # Force plain text if we are not posting to Discord
            fp: bool = not discord

            for system in sorted(activity.systems.copy().values(), key=lambda d: d['System']): # Use a copy for thread-safe operation
                if system_names is not None and system['System'] not in system_names:
                    continue

                system_text:str = ""

                if activity_mode == DiscordActivity.THARGOIDWAR or activity_mode == DiscordActivity.BOTH:
                    system_text += self._build_tw_system(system, True, lang)

                if (activity_mode == DiscordActivity.BGS or activity_mode == DiscordActivity.BOTH) and system.get('tw_status') is None:
                    for faction in sorted(system['Factions'].values(), key=lambda d: d['Faction']):
                        if faction['Enabled'] != CheckStates.STATE_ON:
                            continue
                        system_text += self._build_faction(faction, DiscordActivity, lang)

                if system_text != "":
                    text += f"\n {color_wrap(system['System'], 'white', None, 'bold', fp=fp)}\n{system_text}"

            if discord and activity.discord_notes is not None and activity.discord_notes != "":
                text += "\n" + activity.discord_notes

            offset = time.mktime(datetime.now().timetuple()) - time.mktime(datetime.now(timezone.utc).timetuple())
            tick = round(time.mktime(activity.tick_time.timetuple()) + offset)
            text = f"### {__('BGS Report', lang)} - {__('Tick', lang)} : <t:{tick}>\n```ansi{text}```"
            #else:
            #    text = "BGS Report - Tick : " + self.tick_time.strftime(DATETIME_FORMAT_TITLE) + "\n\n" + text
            return text

        except BaseException as error:
            return f"{traceback.format_exc()}\n An exception occurred: {error}"

    def _build_inf_text(self, inf_data: dict, secondary_inf_data: dict, faction_state: str, discord: bool, lang: str) -> str:
        """
        Create a complete summary of INF for the faction, including both primary and secondary if user has requested

        Args:
            inf_data (dict): Dict containing INF, key = '1' - '5' or 'm'
            secondary_inf_data (dict): Dict containing secondary INF, key = '1' - '5' or 'm'
            faction_state (str): Current faction state
            discord (bool): True if creating for Discord

        Returns:
            str: INF summary
        """
        fp: bool = not discord

        inf:int = sum((1 if k == 'm' else int(k)) * int(v) for k, v in inf_data.items())
        if self.bgstally.state.secondary_inf:
            inf += sum((1 if k == 'm' else int(k)) * int(v) for k, v in secondary_inf_data.items())

        if faction_state in STATES_ELECTION:
            type = __("Election Inf", lang)
        elif faction_state in STATES_WAR:
            type = __("War Inf", lang)
        else:
            type = __("Inf", lang)
        if inf > 0:
            return f"{green('+' + str(inf), fp=fp)} {type}"

        return ""

    def _build_faction(self, faction: dict, discord: bool, lang: str) -> str:
        """
        Generate formatted text for a faction
        """
        # Force plain text if we are not posting to Discord
        fp: bool = not discord

        # Start with the main influence items.

        activity = []
        inf = self._build_inf_text(faction['MissionPoints'], faction['MissionPointsSecondary'], faction['FactionState'], discord, lang)
        if inf != "":
            activity.append(inf)

        # For all the other high level actions just loop through these and sum them up.
        actions = {"Bounties" : "Bounties",
                      "CombatBonds" : "Bonds",
                      "SpaceCZ" : "SCZ",
                      "GroundCZ" : "GCZ",
                      "BlackMarketProfit" : "BlackMarket",
                      "CartData" : "Carto",
                      "ExoData" : "Exo",
                      "Murdered" : "Ship Murders",
                      "GroundMurdered" : "Foot Murders",
                      "Scenarios" : "Scenarios",
                      "MissionFailed" : "Failed",
                      'TradeBuy': 'Spent',
                      'TradeSell': "Profit",
                      "SandR" : "S&R Units"
                      }

        for a in actions:
            if faction.get(a):
                amt = 0
                # The total value depends on the data type.
                if isinstance(faction[a], int):
                    amt = faction[a]
                if isinstance(faction[a], list):
                    amt: int = sum(int(d['value']) for d in faction[a]) # Sum the value
                if isinstance(faction[a], dict):
                    amt: int = sum(int(v) for k, v in faction[a].items()) # Count the records
                if amt > 0:
                    activity.append(f"{green(human_format(amt), fp=fp)} {__(actions[a], lang)}")

        activity_discord_text = ', '.join(activity)

        # Now do the detailed sections
        if self.bgstally.state.detailed_inf:
            activity_discord_text += self._build_faction_details(faction, discord, lang)

        if activity_discord_text == "":
            return ""

        # Faction name and summary of activities
        faction_name = self._process_faction_name(faction['Faction'])
        if faction['Faction'] == self.get_name():
            faction_discord_text = f"   {yellow(faction_name, fp=fp)} : {activity_discord_text}\n"
        else:
            faction_discord_text = f"   {blue(faction_name, fp=fp)} : {activity_discord_text}\n"

        return faction_discord_text

    def _build_faction_details(self, faction: dict, discord: bool, lang: str) -> str:
        """
          Build the detailed faction information if required
        """
        activity = []
        fp: bool = not discord

        # Breakdown of Space CZs
        scz = faction.get('SpaceCZ')
        for w in ['h', 'm', 'l']:
            if w in scz and int(scz[w]) != 0:
                activity.append(grey(f"     {str(scz[w])} [{w.upper()}] {__('Space', lang)}"))

        # Details of Ground CZs so we know where folks have and haven't fought
        for settlement_name in faction.get('GroundCZSettlements', {}):
            if faction['GroundCZSettlements'][settlement_name]['enabled'] == CheckStates.STATE_ON:
                activity.append(grey(f"     {faction['GroundCZSettlements'][settlement_name]['count']} [{faction['GroundCZSettlements'][settlement_name]['type'].upper()}] {__('Ground', lang)} - {settlement_name}"))

        # Trade details
        if self.bgstally.state.detailed_trade:
            for action, desc in {'TradeBuy': 'Spent', 'TradeSell': "Profit"}.items():
                for t, d in {3 : "H", 2 : "M", 1 : "L", 0 : "Z"}.items():
                    if faction[action][t] and faction[action][t]['value'] > 0:
                        activity.append(grey(f"     {human_format(faction[action][t]['value'])} [{d}] {__(desc, lang)} ({str(faction[action][t]['items'])}T)"))

        # Breakdown of mission influence
        for t, d in {'MissionPoints' : 'P', 'MissionPointsSecondary' : 'S'}.items():
            if self.bgstally.state.secondary_inf or t != 'MissionPointsSecondary':
                for i in range(1, 6):
                    if faction[t].get(str(i), 0) != 0:
                        activity.append(grey(f"     {faction[t][str(i)]} [{d}] {__('Inf', lang)}{'+' * i}", fp=fp))

        # Search and rescue, we treat this as detailed inf
        if 'SandR' in faction:
            for t, d in {'op': 'Occupied Escape Pod', 'dp' : 'Damaged Escape Pod', 'bb' : 'Black Box'}.items():
                if faction['SandR'][t]:
                    activity.append(grey(f"     {faction['SandR'][t]} {__(d, lang)}", fp=fp))

        if len(activity) == 0:
            return ""

        return "\n" + "\n".join(activity)

    def _process_faction_name(self, faction_name):
        """
        Shorten the faction name if the user has chosen to
        """
        if self.bgstally.state.abbreviate_faction_names:
            return "".join((i if is_number(i) or "-" in i else i[0]) for i in faction_name.split())
        else:
            return faction_name
