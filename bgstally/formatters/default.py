from bgstally.activity import STATES_ELECTION, STATES_WAR, Activity
from bgstally.constants import CheckStates, DiscordActivity
from bgstally.debug import Debug
from bgstally.formatters.base import FieldActivityFormatterInterface
from bgstally.utils import _, __, human_format, is_number
from thirdparty.colors import *


class DefaultActivityFormatter(FieldActivityFormatterInterface):
    """The default output formatter. Produces coloured text using ANSI formatting and UTF8 emojis
    to represent activity when sending to Discord, and equivalent string representations when not.

    The DefaultFormatter's get_text() method is used to deliver formatted text to the activity windows
    """

    def __init__(self, bgstally):
        """Instantiate class

        Args:
            bgstally (BGSTally): The BGSTally object
        """
        super().__init__(bgstally)


    def get_name(self) -> str:
        """Get the name of this formatter for presenting in the UI

        Returns:
            str: The name
        """
        return _("Default") # LANG: Name of default output formatter


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

        for system in activity.systems.copy().values(): # Use a copy for thread-safe operation
            if system_names is not None and system['System'] not in system_names: continue
            system_text: str = ""

            if activity_mode == DiscordActivity.THARGOIDWAR or activity_mode == DiscordActivity.BOTH:
                system_text += self._build_tw_system_text(system, True, lang)

            if (activity_mode == DiscordActivity.BGS or activity_mode == DiscordActivity.BOTH) and system.get('tw_status') is None:
                for faction in system['Factions'].values():
                    if faction['Enabled'] != CheckStates.STATE_ON: continue
                    system_text += self._build_faction_text(faction, True, lang)

            if system_text != "":
                system_text = system_text.replace("'", "")
                discord_field = {'name': system['System'], 'value': f"```ansi\n{system_text}```"}
                discord_fields.append(discord_field)

        return discord_fields



    #
    # Private functions
    #

    def _build_text(self, activity: Activity, activity_mode: DiscordActivity, system_names: list = None, lang: str = None, discord: bool = True) -> str:
        """Generate formatted text for a given instance of Activity.

        Args:
            activity (Activity): The Activity object containing the activity to post
            activity_mode (DiscordActivity): Determines the type(s) of activity to post
            system_names (list, optional): A list of system names to restrict the output for. If None, all systems are included. Defaults to None.
            lang (str, optional): The language code for this post. Defaults to None.
            discord (bool, optional): True if the destination is Discord (so can include Discord-specific formatting such
            as ```ansi blocks and UTF8 emoji characters), False if not. Defaults to True.

        Returns:
            str: The output text
        """
        text: str = ""
        # Force plain text if we are not posting to Discord
        fp: bool = not discord

        for system in activity.systems.copy().values(): # Use a copy for thread-safe operation
            if system_names is not None and system['System'] not in system_names: continue
            system_text: str = ""

            if activity_mode == DiscordActivity.THARGOIDWAR or activity_mode == DiscordActivity.BOTH:
                system_text += self._build_tw_system_text(system, discord, lang)

            if (activity_mode == DiscordActivity.BGS or activity_mode == DiscordActivity.BOTH) and system.get('tw_status') is None:
                for faction in system['Factions'].values():
                    if faction['Enabled'] != CheckStates.STATE_ON: continue
                    system_text += self._build_faction_text(faction, discord, lang)

            if system_text != "":
                if discord: text += f"```ansi\n{color_wrap(system['System'], 'white', None, 'bold', fp=fp)}\n{system_text}```"
                else: text += f"{color_wrap(system['System'], 'white', None, 'bold', fp=fp)}\n{system_text}"

        if discord and activity.discord_notes is not None and activity.discord_notes != "": text += "\n" + activity.discord_notes

        return text.replace("'", "")


    def _build_faction_text(self, faction: dict, discord: bool, lang: str) -> str:
        """Generate formatted text for a faction

        Args:
            faction (dict): The faction data
            discord (bool): True if the output is destined for Discord
            lang (str): The language code for this post.

        Returns:
            str: The output text
        """
        activity_text: str = ""
        # Force plain text if we are not posting to Discord
        fp: bool = not discord

        activity_text += self._build_inf_text(faction['MissionPoints'], faction['MissionPointsSecondary'], faction['FactionState'], discord, lang)
        activity_text += red("BVs", fp=fp) + " " + green(human_format(faction['Bounties']), fp=fp) + " " if faction['Bounties'] != 0 else "" # LANG: Discord heading, abbreviation for bounty vouchers
        activity_text += red("CBs", fp=fp) + " " + green(human_format(faction['CombatBonds']), fp=fp) + " " if faction['CombatBonds'] != 0 else "" # LANG: Discord heading, abbreviation for combat bonds
        activity_text += self._build_trade_text(faction['TradePurchase'], faction['TradeProfit'], faction['TradeBuy'], faction['TradeSell'], discord, lang)
        activity_text += cyan(__("TrdBMProfit", lang), fp=fp) + " " + green(human_format(faction['BlackMarketProfit']), fp=fp) + " " if faction['BlackMarketProfit'] != 0 else "" # LANG: Discord heading, abbreviation for trade black market profit
        activity_text += white(__("Expl", lang), fp=fp) + " " + green(human_format(faction['CartData']), fp=fp) + " " if faction['CartData'] != 0 else "" # LANG: Discord heading, abbreviation for exploration
        # activity_text += grey(__('Exo', lang), fp=fp) + " " + green(human_format(faction['ExoData']), fp=fp) + " " if faction['ExoData'] != 0 else "" # LANG: Discord heading, abbreviation for exobiology
        activity_text += red(__("Murders", lang), fp=fp) + " " + green(faction['Murdered'], fp=fp) + " " if faction['Murdered'] != 0 else "" # LANG: Discord heading
        activity_text += red(__("GroundMurders", lang), fp=fp) + " " + green(faction['GroundMurdered'], fp=fp) + " " if faction['GroundMurdered'] != 0 else "" # LANG: Discord heading
        activity_text += yellow(__("Scenarios", lang), fp=fp) + " " + green(faction['Scenarios'], fp=fp) + " " if faction['Scenarios'] != 0 else "" # LANG: Discord heading
        activity_text += magenta(__("Fails", lang), fp=fp) + " " + green(faction['MissionFailed'], fp=fp) + " " if faction['MissionFailed'] != 0 else "" # LANG: Discord heading, abbreviation for failed missions
        activity_text += self._build_cz_text(faction.get('SpaceCZ', {}), __("SpaceCZs", lang), discord) # LANG: Discord heading, abbreviation for space conflict zones
        activity_text += self._build_cz_text(faction.get('GroundCZ', {}), __("GroundCZs", lang), discord) # LANG: Discord heading, abbreviation for ground conflict zones
        activity_text += self._build_sandr_text(faction.get('SandR', {}), discord, lang)

        faction_name = self._build_faction_name(faction['Faction'])
        faction_text = f"{color_wrap(faction_name, 'yellow', None, 'bold', fp=fp)} {activity_text}\n" if activity_text != "" else ""

        for settlement_name in faction.get('GroundCZSettlements', {}):
            if faction['GroundCZSettlements'][settlement_name]['enabled'] == CheckStates.STATE_ON:
                faction_text += f"  {'⚔️' if discord else '[X]'} {settlement_name} x {green(faction['GroundCZSettlements'][settlement_name]['count'], fp=fp)}\n"

        return faction_text


    def _build_tw_system_text(self, system: dict, discord: bool, lang: str) -> str:
        """Create formatted text for Thargoid War in a system

        Args:
            system (dict): The system data
            discord (bool): True if the output is destined for Discord
            lang (str): The language code for this post.

        Returns:
            str: The output text
        """
        system_text: str = ""
        system_stations: dict = {}
        # Force plain text if we are not posting to Discord
        fp: bool = not discord

        # Faction-specific tally
        for faction in system['Factions'].values():
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
        kills: int = sum(system['TWKills'].values())
        sandr: int = sum(int(d['delivered']) for d in system['TWSandR'].values())
        reactivate: int = system['TWReactivate']
        if kills > 0 or sandr > 0 or reactivate > 0:
            system_text += ("🍀 " if discord else "TW ") + __("System activity", lang) + "\n" # LANG: Discord heading
            if kills > 0:
                system_text += ("  💀 (" + __("kills", lang) + "): " if discord else "[" + __("kills", lang) + "]: ") + self._build_tw_vessels_text(system['TWKills'], discord) + " \n" # LANG: Discord heading

            if sandr > 0:
                system_text += "  "
                pods: int = system['TWSandR']['dp']['delivered'] + system['TWSandR']['op']['delivered']
                if pods > 0: system_text += ("⚰️" if discord else "[" + __("esc-pod", lang) + "]") + " x " + green(pods, fp=fp) + " " # LANG: Discord heading, abbreviation for escape pod
                tps: int = system['TWSandR']['tp']['delivered']
                if tps > 0: system_text += ("🏮" if discord else "[" + __("bio-pod", lang) + "]") + " x " + green(tps, fp=fp) + " " # LANG: Discord heading
                bbs: int = system['TWSandR']['bb']['delivered']
                if bbs > 0: system_text += ("⬛" if discord else "[" + __("bb", lang) + "]") + " x " + green(bbs, fp=fp) + " " # LANG: Discord heading, abbreviation for black box
                tissue: int = system['TWSandR']['t']['delivered']
                if tissue > 0: system_text += ("🌱" if discord else "[" + __("ts", lang) + "]") + " x " + green(tissue, fp=fp) + " " # LANG: Discord heading, abbreviation for tissue sample
                system_text += "\n"
            if reactivate > 0:
                system_text += ("  🛠️" if discord else "[" + __("reac", lang) + "]") + " x " + green(reactivate, fp=fp) + " " # LANG: Discord heading, abbreviation for reactivation (TW missions)
                system_text += __("settlements", lang) + "\n" # LANG: Discord heading

        # Station-specific tally
        for system_station_name, system_station in system_stations.items():
            system_text += f"{'🍀' if discord else 'TW'} {system_station_name}: {green(system_station['mission_count_total'], fp=fp)} " + __("missions", lang) + "\n" # LANG: Discord heading
            if (system_station['escapepods']['m']['sum'] > 0):
                system_text += ("  ❕" if discord else "[" + __("wounded", lang) + "]") + " x " + green(system_station['escapepods']['m']['sum'], fp=fp) + " - " + green(system_station['escapepods']['m']['count'], fp=fp) + " " # LANG: Discord heading
                system_text += __("missions", lang) + "\n" # LANG: Discord heading
            if (system_station['escapepods']['h']['sum'] > 0):
                system_text += ("  ❗" if discord else "[" + __("crit", lang) + "]") + " x " + green(system_station['escapepods']['h']['sum'], fp=fp) + " - " + green(system_station['escapepods']['h']['count'], fp=fp) + " " # LANG: Discord heading, abbreviation for critically injured
                system_text += __("missions", lang) + "\n" # LANG: Discord heading
            if (system_station['cargo']['sum'] > 0):
                system_text += ("  📦" if discord else "[" + __("cargo", lang) + "]") + " x " + green(system_station['cargo']['sum'], fp=fp) + " - " + green(system_station['cargo']['count'], fp=fp) + " " # LANG: Discord heading
                system_text += __("missions", lang) + "\n" # LANG: Discord heading
            if (system_station['escapepods']['l']['sum'] > 0):
                system_text += ("  ⚕️" if discord else "[" + __("injured", lang) + "]") + " x " + green(system_station['escapepods']['l']['sum'], fp=fp) + " - " + green(system_station['escapepods']['l']['count'], fp=fp) + " " # LANG: Discord heading
                system_text += __("missions", lang) + "\n" # LANG: Discord heading
            if (system_station['passengers']['sum'] > 0):
                system_text += ("  🧍" if discord else "[" + __("passeng", lang) + "]") + " x " + green(system_station['passengers']['sum'], fp=fp) + " - " + green(system_station['passengers']['count'], fp=fp) + " " # LANG: Discord heading, abbreviation for passengers
                system_text += __("missions", lang) + "\n" # LANG: Discord heading
            if (sum(x['sum'] for x in system_station['massacre'].values())) > 0:
                system_text += ("  💀 (" + __("mm", lang) + ")" if discord else "[" + __("mm", lang) + "]") + ": " + self._build_tw_vessels_text(system_station['massacre'], discord) + " - " + green((sum(x['count'] for x in system_station['massacre'].values())), fp=fp) + " " # LANG: Discord heading, abbreviation for massacre (missions)
                system_text += __("missions", lang) + "\n" # LANG: Discord heading
            if (system_station['reactivate'] > 0):
                system_text += ("  🛠️" if discord else "[" + __("reac", lang) + "]") + " x " + green(system_station['reactivate'], fp=fp) + " " # LANG: Discord heading, abbreviation for TW reactivation (missions)
                system_text += __("missions", lang) + "\n" # LANG: Discord heading

        return system_text


    def _build_inf_text(self, inf_data: dict, secondary_inf_data: dict, faction_state: str, discord: bool, lang: str) -> str:
        """Create a complete summary of INF for the faction, including both primary and secondary if user has requested

        Args:
            inf_data (dict): Dict containing INF, key = '1' - '5' or 'm'
            secondary_inf_data (dict): Dict containing secondary INF, key = '1' - '5' or 'm'
            faction_state (str): Current faction state
            discord (bool): True if creating for Discord
            lang (str): The language code for this post.

        Returns:
            str: INF summary
        """
        text: str = ""
        # Force plain text if we are not posting to Discord
        fp: bool = not discord

        inf: int = sum((1 if k == 'm' else int(k)) * int(v) for k, v in inf_data.items())
        inf_sec: int = sum((1 if k == 'm' else int(k)) * int(v) for k, v in secondary_inf_data.items())

        if inf != 0 or (inf_sec != 0 and self.bgstally.state.secondary_inf):
            if faction_state in STATES_ELECTION:
                text += blue(__("ElectionINF", lang), fp=fp) + " " # LANG: Discord heading, abbreviation for election INF
            elif faction_state in STATES_WAR:
                text += blue(__("WarINF", lang), fp=fp) + " " # LANG: Discord heading, abbreviation for war INF
            else:
                text += blue(__("INF", lang), fp=fp) + " " # LANG: Discord heading, abbreviation for INF

            if self.bgstally.state.secondary_inf:
                text += self._build_inf_individual(inf, inf_data, "🅟" if discord else "[P]", discord)
                text += self._build_inf_individual(inf_sec, secondary_inf_data, "🅢" if discord else "[S]", discord)
            else:
                text += self._build_inf_individual(inf, inf_data, "", discord)

        return text


    def _build_inf_individual(self, inf:int, inf_data: dict, prefix: str, discord: bool) -> str:
        """Create a summary of either primary or secondary INF, with detailed breakdown if user has requested

        Args:
            inf (int): Total INF
            inf_data (dict): dict containing INF, key = '1' - '5' or 'm'
            prefix (str): Prefix label (🅟 or 🅢 or empty)
            discord (bool): True if creating for Discord

        Returns:
            str: INF summary
        """
        text: str = ""
        if inf == 0: return text

        # Force plain text if we are not posting to Discord
        fp: bool = not discord

        inf_str: str = f"{'+' if inf > 0 else ''}{inf}"
        text += f"{prefix}{green(inf_str, fp=fp)} "

        if self.bgstally.state.detailed_inf:
            detailed_inf: str = ""
            if inf_data.get('1', 0) != 0: detailed_inf += f"{'➊' if discord else '+'} x {green(inf_data['1'], fp=fp)} "
            if inf_data.get('2', 0) != 0: detailed_inf += f"{'➋' if discord else '++'} x {green(inf_data['2'], fp=fp)} "
            if inf_data.get('3', 0) != 0: detailed_inf += f"{'➌' if discord else '+++'} x {green(inf_data['3'], fp=fp)} "
            if inf_data.get('4', 0) != 0: detailed_inf += f"{'➍' if discord else '++++'} x {green(inf_data['4'], fp=fp)} "
            if inf_data.get('5', 0) != 0: detailed_inf += f"{'➎' if discord else '+++++'} x {green(inf_data['5'], fp=fp)} "
            if detailed_inf != "": text += f"({detailed_inf.rstrip()}) "

        return text


    def _build_trade_text(self, trade_purchase: int, trade_profit: int, trade_buy: list, trade_sell: list, discord: bool, lang: str) -> str:
        """Create a summary of trade, with detailed breakdown if user has requested

        Args:
            trade_purchase (int): Legacy total trade purchase value (before trade was tracked in brackets).
            trade_profit (int): Legacy total trade profit value (before trade was tracked in brackets).
            trade_buy (list): List of trade purchases with each entry corresponding to a trade bracket.
            trade_sell (list): List of trade sales with each entry corresponding to a trade bracket.
            discord (bool): True if creating for Discord
            lang (str): The language code for this post.

        Returns:
            str: Trade summary
        """
        text: str = ""

        # Force plain text if we are not posting to Discord
        fp: bool = not discord

        if trade_purchase > 0:
            # Legacy - Used a single value for purchase value / profit
            text += cyan(__("TrdBuy", lang), fp=fp) + " " + green(human_format(trade_purchase), fp=fp) + " " if trade_purchase != 0 else "" # LANG: Discord heading, abbreviation for trade buy
            text += cyan(__("TrdProfit", lang), fp=fp) + " " + green(human_format(trade_profit), fp=fp) + " " if trade_profit != 0 else "" # LANG: Discord heading, abbreviation for trade profit
        elif not self.bgstally.state.detailed_trade:
            # Modern, simple trade report - Combine buy at all brackets and profit at all brackets
            buy_total: int = sum(int(d['value']) for d in trade_buy)
            profit_total: int = sum(int(d['profit']) for d in trade_sell)
            text += cyan(__("TrdBuy", lang), fp=fp) + " " + green(human_format(buy_total), fp=fp) + " " if buy_total != 0 else "" # LANG: Discord heading, abbreviation for trade buy
            text += cyan(__("TrdProfit", lang), fp=fp) + " " + green(human_format(profit_total), fp=fp) + " " if profit_total != 0 else "" # LANG: Discord heading, abbreviation for trade profit
        else:
            # Modern, detailed trade report - Split into values per supply / demand bracket
            if sum(int(d['value']) for d in trade_buy) > 0:
                # Buy brackets currently range from 1 - 3
                text += cyan(__("TrdBuy", lang), fp=fp) + " "
                if int(trade_buy[1]['value']) != 0: text += f"{'🅻' if discord else '[L]'}:{green(human_format(trade_buy[1]['value']), fp=fp)} "
                if int(trade_buy[2]['value']) != 0: text += f"{'🅼' if discord else '[M]'}:{green(human_format(trade_buy[2]['value']), fp=fp)} "
                if int(trade_buy[3]['value']) != 0: text += f"{'🅷' if discord else '[H]'}:{green(human_format(trade_buy[3]['value']), fp=fp)} "
            if sum(int(d['value']) for d in trade_sell) > 0:
                # Sell brackets currently range from 0 - 3
                text += cyan(__("TrdProfit", lang), fp=fp) + " "
                if int(trade_sell[0]['profit']) != 0: text += f"{'🆉' if discord else '[Z]'}:{green(human_format(trade_sell[0]['profit']), fp=fp)} "
                if int(trade_sell[1]['profit']) != 0: text += f"{'🅻' if discord else '[L]'}:{green(human_format(trade_sell[1]['profit']), fp=fp)} "
                if int(trade_sell[2]['profit']) != 0: text += f"{'🅼' if discord else '[M]'}:{green(human_format(trade_sell[2]['profit']), fp=fp)} "
                if int(trade_sell[3]['profit']) != 0: text += f"{'🅷' if discord else '[H]'}:{green(human_format(trade_sell[3]['profit']), fp=fp)} "

        return text


    def _build_cz_text(self, cz_data: dict, prefix: str, discord: bool) -> str:
        """Create a summary of Conflict Zone activity

        Args:
            cz_data (dict): The CZ data
            prefix (str): A prefix to include before the output text
            discord (bool): True if creating for Discord

        Returns:
            str: CZ summary
        """
        if cz_data == {}: return ""
        text: str = ""
        # Force plain text if we are not posting to Discord
        fp: bool = not discord

        if 'l' in cz_data and cz_data['l'] != "" and int(cz_data['l']) != 0: text += f"L x {green(cz_data['l'], fp=fp)} "
        if 'm' in cz_data and cz_data['m'] != "" and int(cz_data['m']) != 0: text += f"M x {green(cz_data['m'], fp=fp)} "
        if 'h' in cz_data and cz_data['h'] != "" and int(cz_data['h']) != 0: text += f"H x {green(cz_data['h'], fp=fp)} "

        objectives: str = ""
        if 'cs' in cz_data and cz_data['cs'] != "" and int(cz_data['cs']) != 0: objectives += f"{'👑' if discord else 'Cap Ship'}:{green(cz_data['cs'], fp=fp)} " # Cap Ship
        if 'so' in cz_data and cz_data['so'] != "" and int(cz_data['so']) != 0: objectives += f"{'🔠' if discord else 'Spec Ops'}:{green(cz_data['so'], fp=fp)} " # Spec Ops
        if 'cp' in cz_data and cz_data['cp'] != "" and int(cz_data['cp']) != 0: objectives += f"{'👨‍✈️' if discord else 'Capt'}:{green(cz_data['cp'], fp=fp)} " # Captain
        if 'pr' in cz_data and cz_data['pr'] != "" and int(cz_data['pr']) != 0: objectives += f"{'✒️' if discord else 'Propagand'}:{green(cz_data['pr'], fp=fp)} " # Propagandist
        if objectives != "": text += f"({objectives.rstrip()}) "

        if text != "": text = f"{red(prefix, fp=fp)} {text} "
        return text


    def _build_tw_vessels_text(self, tw_data: dict, discord: bool) -> str:
        """Create a summary of TW activity.

        Args:
            tw_data (dict): A contains either:
                key = str representing thargoid vessel type; value = dict containing 'sum' property with int total for that vessel
                key = str representing thargoid vessel type; value = int total for that vessel
            discord (bool): True if creating for Discord

        Returns:
            str: TW vessels summary
        """
        if tw_data == {}: return ""
        text: str = ""
        # Force plain text if we are not posting to Discord
        fp: bool = not discord
        first: bool = True

        for k, v in tw_data.items():
            label: str = ""
            value: int = 0

            if k == 'ba': label = "Ba"    # Banshee
            elif k == 'sg': label = "S/G" # Scythe / Glaive
            else: label = k.upper()       # All others

            if isinstance(v, dict): value = int(v.get('sum', 0))
            else: value = int(v)
            if value == 0: continue

            if not first: text += ", "
            text += f"{red(label, fp=fp)} x {green(value, fp=fp)}"

            first = False

        return text


    def _build_sandr_text(self, sandr_data: dict, discord: bool, lang: str) -> str:
        """Create a summary of BGS search and rescue activity

        Args:
            sandr_data (dict): dict containing an entry for each type of SandR handin
            discord (bool): True if this text is destined for Discord
            lang (str): The language code for this post.

        Returns:
            str: S&R activity summary
        """
        if sandr_data == {}: return ""
        # Force plain text if we are not posting to Discord
        fp: bool = not discord

        value: int = int(sum(sandr_data.values()))
        if value == 0: return ""

        return white(__("SandR", lang), fp=fp) + " " + green(value, fp=fp) + " " # LANG: Discord heading, abbreviation for search and rescue


    def _build_faction_name(self, faction_name: str) -> str:
        """Shorten the faction name if the user has chosen to

        Args:
            faction_name (str): The full faction name

        Returns:
            str: The shortened faction name
        """
        if self.bgstally.state.abbreviate_faction_names:
            return "".join((i if is_number(i) or "-" in i else i[0]) for i in faction_name.split())
        else:
            return faction_name


    def _get_new_aggregate_tw_station_data(self) -> dict:
        """Get a new data structure for aggregating Thargoid War station data when displaying in text reports

        Returns:
            dict: Data for a TW station with no activity
        """
        return {'mission_count_total': 0,
                'passengers': {'count': 0, 'sum': 0},
                'escapepods': {'l': {'count': 0, 'sum': 0}, 'm': {'count': 0, 'sum': 0}, 'h': {'count': 0, 'sum': 0}},
                'cargo': {'count': 0, 'sum': 0},
                'massacre': {'s': {'count': 0, 'sum': 0}, 'c': {'count': 0, 'sum': 0}, 'b': {'count': 0, 'sum': 0}, 'm': {'count': 0, 'sum': 0}, 'h': {'count': 0, 'sum': 0}, 'o': {'count': 0, 'sum': 0}},
                'reactivate': 0}
