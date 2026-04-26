import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bgstally.bgstally import BGSTally

from bgstally.activity import STATES_ELECTION, STATES_WAR, Activity
from bgstally.constants import CheckStates, DiscordActivity, DiscordPostStyle
from bgstally.debug import Debug
from bgstally.formatters.default import DefaultActivityFormatter
from bgstally.utils import _, __, catch_exceptions, human_format, is_number
from thirdparty.colors import *


class CLBActivityFormatter(DefaultActivityFormatter):
    """
    Activity formatter that outputs in a format suitable for Celestial Light Brigade Discord channel
    """

    def __init__(self, bgstally: 'BGSTally'):
        super().__init__(bgstally)


    def get_name(self) -> str:
        """Get the name of this formatter """
        return 'Celestial Light Brigade'

    def is_visible(self) -> bool:
        """Should this formatter be visible to the user as a choice. """
        return True

    @catch_exceptions
    def get_overlay(self, activity:Activity, activity_mode:DiscordActivity, system_names:list|None = None, lang:str = "") -> str:
        """
        Get the in-game overlay text for a given instance of Activity. The in-game overlay
        doesn't support any ANSI colouring and very few UTF-8 special characters. Basically,
        only plain text is safe.
        """
        return self._build_text(activity, activity_mode, system_names, lang, False)

    @catch_exceptions
    def get_text(self, activity:Activity, activity_mode:DiscordActivity, system_names:list|None = None, lang:str = "") -> str:
        """
        Generate formatted text for a given instance of Activity. Must be implemented by subclasses.
        This method is used for getting the text for the 'copy and paste' function, and for direct posting
        to Discord for those Formatters that use text style posts (vs Discord embed style posts)
        """
        return self._build_text(activity, activity_mode, system_names, lang, True)

    @catch_exceptions
    def get_fields(self, activity:Activity, activity_mode:DiscordActivity, system_names:list|None = None, lang:str = "") -> list:
        """
        Generate a list of discord embed fields, conforming to the embed field spec defined here:
        https://birdie0.github.io/discord-webhooks-guide/structure/embed/fields.html - i.e. each field should be a dict
        containing 'name' and 'value' str keys, and optionally an 'inline' bool key
        """
        discord_fields = []

        for system in sorted(activity.systems.copy().values(), key=lambda d: d['System']): # Use a copy for thread-safe operation
            if system_names is not None and system['System'] not in system_names: continue
            if not self.include_system(system): continue

            system_text: str = ""
            if activity_mode == DiscordActivity.THARGOIDWAR or activity_mode == DiscordActivity.BOTH:
                system_text += self._build_tw_system(system, lang, True)

            if (activity_mode == DiscordActivity.BGS or activity_mode == DiscordActivity.BOTH) and system.get('tw_status') is None:
                for faction in sorted(system['Factions'].values(), key=lambda d: d['Faction']):
                    if faction['Enabled'] != CheckStates.STATE_ON: continue
                    if not self.include_faction(faction): continue

                    system_text += self._build_faction(faction, lang, True)

            if system_text != "":
                discord_field = {'name': self.get_system_display_name(system['System']), 'value': f"```ansi\n{system_text}```"}
                discord_fields.append(discord_field)

        return discord_fields

    def get_mode(self) -> DiscordPostStyle:
        """ Get the output format mode that this Formatter supports. """
        return DiscordPostStyle.TEXT

    #
    # Private functions
    #

    def _build_text(self, activity:Activity, activity_mode:DiscordActivity, system_names:list|None = None, lang:str = "", discord:bool = True) -> str:
        """ Generate formatted text for a given instance of Activity. """

        text:str = ""
        # Force plain text if we are not posting to Discord
        fp: bool = not discord

        for system in sorted(activity.systems.copy().values(), key=lambda d: d['System']): # Use a copy for thread-safe operation
            if system_names is not None and system['System'] not in system_names: continue
            if not self.include_system(system): continue

            system_text:str = ""

            if activity_mode == DiscordActivity.THARGOIDWAR or activity_mode == DiscordActivity.BOTH:
                system_text += self._build_tw_system(system, lang, True)

            if (activity_mode == DiscordActivity.BGS or activity_mode == DiscordActivity.BOTH) and system.get('tw_status') is None:
                for faction in sorted(system['Factions'].values(), key=lambda d: d['Faction']):
                    if faction['Enabled'] != CheckStates.STATE_ON: continue
                    if not self.include_faction(faction): continue

                    system_text += self._build_faction(faction, lang, discord)

            if system_text != "":
                text += f"\n {color_wrap(self.get_system_display_name(system['System']), 'white', None, 'bold', fp=fp)}\n{system_text}"

        if text == "": return ""

        if discord and activity.discord_notes is not None and activity.discord_notes != "":
            text += "\n" + activity.discord_notes

        offset = time.mktime(datetime.now().timetuple()) - time.mktime(datetime.now(timezone.utc).timetuple())
        tick = round(time.mktime(activity.tick_time.timetuple()) + offset)

        return f"### {__('BGS Report', lang)} - {__('Tick', lang)} : <t:{tick}>\n```ansi{text}```"  # LANG: BGS Report Tick time


    def _build_inf_text(self, inf_data:dict, secondary_inf_data:dict, faction_state:str, lang:str = "", discord:bool = False) -> str:
        """ Create a complete summary of INF for the faction, including both primary and secondary if user has requested it. """
        fp:bool = not discord

        inf:int = sum((1 if k == 'm' else int(k)) * int(v) for k, v in inf_data.items())
        if self.bgstally.state.secondary_inf:
            inf += sum((1 if k == 'm' else int(k)) * int(v) for k, v in secondary_inf_data.items())

        if faction_state in STATES_ELECTION:
            type = __("Election Inf", lang) # LANG: Election Influence in Discord report
        elif faction_state in STATES_WAR:
            type = __("War Inf", lang) # LANG: War Influence in Discord report
        else:
            type = __("Inf", lang) # LANG: Influence in Discord report
        if inf == 0:
            return ""

        return f"{green('+' + str(inf), fp=fp)} {type}"

    def _build_faction(self, faction:dict, lang:str = "", discord:bool = False) -> str:
        """ Generate formatted text for a faction """
        # Force plain text if we are not posting to Discord
        fp: bool = not discord

        # Start with the main influence items.
        activity = []
        inf = self._build_inf_text(faction['MissionPoints'], faction['MissionPointsSecondary'], faction['FactionState'], lang, discord)
        if inf != "":
            activity.append(inf)

        # For all the other high level actions just loop through these and sum them up.
        actions = {"Bounties" : __("Bounties", lang), # LANG: Bounties in Discord report
                      "CombatBonds" : __("Bonds", lang), # LANG: Bonds in Discord report
                      "SpaceCZ" : __("SCZ", lang), # LANG: Space CZ in Discord report
                      "GroundCZ" : __("GCZ", lang), # LANG: Ground CZ in Discord report
                      "BlackMarketProfit" : __("BlackMarket", lang), # LANG: Black Market profit in Discord report
                      "CartData" : __("Carto", lang), # LANG: Cartographic data sold in Discord report
                      "ExoData" : __("Exo", lang), # LANG: Exobiological data sold in Discord report
                      "Murdered" : __("Ship Murders", lang), # LANG: Ship Murders in Discord report
                      "GroundMurdered" : __("Foot Murders", lang), # LANG: Foot Murders in Discord report
                      "Scenarios" : __("Scenarios", lang), # LANG: Scenarios in Discord report
                      "MissionFailed" : __("Failed", lang), # LANG: Missions Failed in Discord report
                      'TradeBuy': __('Spent', lang), # LANG: Trade Buy in Discord report
                      'TradeSell': __('Profit', lang), # LANG: Trade Sell in Discord report
                      "SandR" : __("S&R Units", lang) # LANG: Search and Rescue units in Discord report
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
                    activity.append(f"{green(human_format(amt), fp=fp)} {actions[a]}") #

        activity_discord_text = ', '.join(activity)

        # Now do the detailed sections
        if self.bgstally.state.detailed_inf:
            activity_discord_text += self._build_faction_details(faction, lang, discord)

        if activity_discord_text == "":
            return ""

        # Faction name and summary of activities
        faction_name = self._abreviate_faction_name(faction['Faction'])
        if faction['Faction'] == self.get_name():
             return f"   {yellow(faction_name, fp=fp)} : {activity_discord_text}\n"

        return f"   {blue(faction_name, fp=fp)} : {activity_discord_text}\n"


    def _build_faction_details(self, faction:dict, lang:str = "", discord:bool = False) -> str:
        """ Build the detailed faction information if required """
        activity = []
        fp: bool = not discord

        # Breakdown of Space CZs
        scz = faction.get('SpaceCZ')
        for w in ['h', 'm', 'l']:
            if scz != None and w in scz and int(scz[w]) != 0:
                activity.append(grey(f"     {str(scz[w])} [{w.upper()}] {__('Space', lang)}")) # LANG: Space CZ details in Discord report

        # Details of Ground CZs so we know where folks have and haven't fought
        for settlement_name in faction.get('GroundCZSettlements', {}):
            if faction['GroundCZSettlements'][settlement_name]['enabled'] == CheckStates.STATE_ON:
                activity.append(grey(f"     {faction['GroundCZSettlements'][settlement_name]['count']} [{faction['GroundCZSettlements'][settlement_name]['type'].upper()}] {__('Ground', lang)} - {settlement_name}")) # LANG: Ground CZ details in Discord report

        # Trade details
        if self.bgstally.state.detailed_trade:
            for action, desc in {'TradeBuy': __('Spent', lang), 'TradeSell': __('Profit', lang)}.items(): # LANG: Trade in Discord report
                for t, d in {3 : "H", 2 : "M", 1 : "L", 0 : "Z"}.items():
                    if faction[action][t] and faction[action][t]['value'] > 0:
                        activity.append(grey(f"     {human_format(faction[action][t]['value'])} [{d}] {desc} ({str(faction[action][t]['items'])}T)")) # LANG: Trade details in Discord report

        # Breakdown of mission influence
        for t, d in {'MissionPoints' : 'P', 'MissionPointsSecondary' : 'S'}.items():
            if self.bgstally.state.secondary_inf or t != 'MissionPointsSecondary':
                for i in range(1, 6):
                    if faction[t].get(str(i), 0) != 0:
                        activity.append(grey(f"     {faction[t][str(i)]} [{d}] {__('Inf', lang)}{'+' * i}", fp=fp)) # LANG: Mission influence details in Discord report

        # Search and rescue, we treat this as detailed inf
        if 'SandR' in faction:
            for t, d in {'op': __('Occupied Escape Pod', lang), 'dp' : __('Damaged Escape Pod', lang), 'bb' : __('Black Box', lang)}.items(): # LANG: Search and Rescue in Discord report
                if faction['SandR'][t]:
                    activity.append(grey(f"     {faction['SandR'][t]} {d}", fp=fp))

        if len(activity) == 0:
            return ""

        return "\n" + "\n".join(activity)


    def _abreviate_faction_name(self, faction_name:str) -> str:
        """ Shorten the faction name if the user has chosen to abbreviate faction names. """
        if self.bgstally.state.abbreviate_faction_names == False:
            return faction_name

        return "".join((i if is_number(i) or "-" in i else i[0]) for i in faction_name.split())


    def _build_tw_system(self, system:dict, lang:str = "", discord:bool = False) -> str:
        """ Ought to implement this but for now just call the parent function. """

        # Yes, the discord & lang params are reversed. They're inconsistent in the parent class but consistent in this one.
        # lang first because it's almost always present, discord second because it isn't.
        return super()._build_tw_system(system, discord, lang)
