import tkinter as tk
from functools import partial
from os import path
from tkinter import PhotoImage, ttk
from typing import Dict

from bgstally.activity import STATES_WAR, STATES_ELECTION, Activity
from bgstally.constants import FOLDER_ASSETS, CheckStates, CZs, DiscordActivity, DiscordChannel, DiscordPostStyle
from bgstally.debug import Debug
from bgstally.discord import DATETIME_FORMAT
from bgstally.widgets import TextPlus
from thirdparty.ScrollableNotebook import ScrollableNotebook
from theme import theme

DATETIME_FORMAT_WINDOWTITLE = "%Y-%m-%d %H:%M:%S"


class WindowActivity:
    """
    Handles an activity window
    """

    def __init__(self, bgstally, ui, activity: Activity):
        self.bgstally = bgstally
        self.ui = ui

        self.image_tab_active_enabled = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_enabled.png"))
        self.image_tab_active_part_enabled = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_part_enabled.png"))
        self.image_tab_active_disabled = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_disabled.png"))
        self.image_tab_inactive_enabled = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_inactive_enabled.png"))
        self.image_tab_inactive_part_enabled = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_inactive_part_enabled.png"))
        self.image_tab_inactive_disabled = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_inactive_disabled.png"))

        self._show(activity)


    def _show(self, activity: Activity):
        """
        Show our window
        """
        Form = tk.Toplevel(self.ui.frame)
        Form.title("BGS Tally - After Tick at: " + activity.tick_time.strftime(DATETIME_FORMAT_WINDOWTITLE))
        Form.geometry("1200x800")

        ContainerFrame = ttk.Frame(Form)
        ContainerFrame.pack(fill=tk.BOTH, expand=1)
        TabParent=ScrollableNotebook(ContainerFrame, wheelscroll=False, tabmenu=True)
        TabParent.pack(fill=tk.BOTH, expand=1, side=tk.TOP, padx=5, pady=5)

        DiscordFrame = ttk.Frame(ContainerFrame)
        DiscordFrame.pack(fill=tk.BOTH, padx=5, pady=5)
        DiscordFrame.columnconfigure(0, weight=2)
        DiscordFrame.columnconfigure(1, weight=1)
        ttk.Label(DiscordFrame, text="Discord Report", font=self.ui.heading_font).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(DiscordFrame, text="Discord Options", font=self.ui.heading_font).grid(row=0, column=1, sticky=tk.W)
        ttk.Label(DiscordFrame, text="Double-check on-ground CZ tallies, sizes are not always correct", foreground='#f00').grid(row=1, column=0, columnspan=2, sticky=tk.W)

        DiscordTextFrame = ttk.Frame(DiscordFrame)
        DiscordTextFrame.grid(row=2, column=0, pady=5, sticky=tk.NSEW)
        DiscordText = TextPlus(DiscordTextFrame, state='disabled', wrap=tk.WORD, height=14, font=("Helvetica", 9))
        DiscordScroll = tk.Scrollbar(DiscordTextFrame, orient=tk.VERTICAL, command=DiscordText.yview)
        DiscordText['yscrollcommand'] = DiscordScroll.set
        DiscordScroll.pack(fill=tk.Y, side=tk.RIGHT)
        DiscordText.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        DiscordOptionsFrame = ttk.Frame(DiscordFrame)
        DiscordOptionsFrame.grid(row=2, column=1, padx=5, pady=5, sticky=tk.NW)
        current_row = 1
        ttk.Label(DiscordOptionsFrame, text="Post Format").grid(row=current_row, column=0, padx=10, sticky=tk.W)
        ttk.Radiobutton(DiscordOptionsFrame, text="Modern", variable=self.bgstally.state.DiscordPostStyle, value=DiscordPostStyle.EMBED).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        ttk.Radiobutton(DiscordOptionsFrame, text="Legacy", variable=self.bgstally.state.DiscordPostStyle, value=DiscordPostStyle.TEXT).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        ttk.Label(DiscordOptionsFrame, text="Activity to Include").grid(row=current_row, column=0, padx=10, sticky=tk.W)
        ttk.Radiobutton(DiscordOptionsFrame, text="BGS", variable=self.bgstally.state.DiscordActivity, value=DiscordActivity.BGS, command=partial(self._option_change, DiscordText, activity)).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        ttk.Radiobutton(DiscordOptionsFrame, text="Thargoid War", variable=self.bgstally.state.DiscordActivity, value=DiscordActivity.THARGOIDWAR, command=partial(self._option_change, DiscordText, activity)).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        ttk.Radiobutton(DiscordOptionsFrame, text="Both", variable=self.bgstally.state.DiscordActivity, value=DiscordActivity.BOTH, command=partial(self._option_change, DiscordText, activity)).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        ttk.Label(DiscordOptionsFrame, text="Other Options").grid(row=current_row, column=0, padx=10, sticky=tk.W)
        ttk.Checkbutton(DiscordOptionsFrame, text="Abbreviate Faction Names", variable=self.bgstally.state.AbbreviateFactionNames, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=partial(self._option_change, DiscordText, activity)).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1
        ttk.Checkbutton(DiscordOptionsFrame, text="Include Secondary INF", variable=self.bgstally.state.IncludeSecondaryInf, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=partial(self._option_change, DiscordText, activity)).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1

        system_list = activity.get_ordered_systems()

        tab_index = 0

        for system_id in system_list:
            system = activity.systems[system_id]

            if self.bgstally.state.ShowZeroActivitySystems.get() == CheckStates.STATE_OFF \
                and system['zero_system_activity'] \
                and str(system_id) != self.bgstally.state.current_system_id: continue

            tab = ttk.Frame(TabParent)
            tab.columnconfigure(1, weight=1) # Make the second column (faction name) fill available space
            TabParent.add(tab, text=system['System'], compound='right', image=self.image_tab_active_enabled)

            FactionEnableCheckbuttons = []

            ttk.Label(tab, text="Include", font=self.ui.heading_font).grid(row=0, column=0, padx=2, pady=2)
            EnableAllCheckbutton = ttk.Checkbutton(tab)
            EnableAllCheckbutton.grid(row=1, column=0, padx=2, pady=2)
            EnableAllCheckbutton.configure(command=partial(self._enable_all_factions_change, TabParent, tab_index, EnableAllCheckbutton, FactionEnableCheckbuttons, DiscordText, activity, system))
            EnableAllCheckbutton.state(['!alternate'])
            ttk.Label(tab, text="Faction", font=self.ui.heading_font).grid(row=0, column=1, padx=2, pady=2)
            ttk.Label(tab, text="State", font=self.ui.heading_font).grid(row=0, column=2, padx=2, pady=2)
            ttk.Label(tab, text="INF", font=self.ui.heading_font, anchor=tk.CENTER).grid(row=0, column=3, columnspan=2, padx=2)
            ttk.Label(tab, text="Pri", font=self.ui.heading_font).grid(row=1, column=3, padx=2, pady=2)
            ttk.Label(tab, text="Sec", font=self.ui.heading_font).grid(row=1, column=4, padx=2, pady=2)
            ttk.Label(tab, text="Trade", font=self.ui.heading_font, anchor=tk.CENTER).grid(row=0, column=5, columnspan=3, padx=2)
            ttk.Label(tab, text="Purch", font=self.ui.heading_font).grid(row=1, column=5, padx=2, pady=2)
            ttk.Label(tab, text="Prof", font=self.ui.heading_font).grid(row=1, column=6, padx=2, pady=2)
            ttk.Label(tab, text="BM Prof", font=self.ui.heading_font).grid(row=1, column=7, padx=2, pady=2)
            ttk.Label(tab, text="BVs", font=self.ui.heading_font).grid(row=0, column=8, padx=2, pady=2)
            ttk.Label(tab, text="Expl", font=self.ui.heading_font).grid(row=0, column=9, padx=2, pady=2)
            ttk.Label(tab, text="Exo", font=self.ui.heading_font).grid(row=0, column=10, padx=2, pady=2)
            ttk.Label(tab, text="CBs", font=self.ui.heading_font).grid(row=0, column=11, padx=2, pady=2)
            ttk.Label(tab, text="Fails", font=self.ui.heading_font).grid(row=0, column=12, padx=2, pady=2)
            ttk.Label(tab, text="Murders", font=self.ui.heading_font).grid(row=0, column=13, padx=2, pady=2)
            ttk.Label(tab, text="Scens", font=self.ui.heading_font).grid(row=0, column=14, padx=2, pady=2)
            ttk.Label(tab, text="Space CZs", font=self.ui.heading_font, anchor=tk.CENTER).grid(row=0, column=15, columnspan=3, padx=2)
            ttk.Label(tab, text="L", font=self.ui.heading_font).grid(row=1, column=15, padx=2, pady=2)
            ttk.Label(tab, text="M", font=self.ui.heading_font).grid(row=1, column=16, padx=2, pady=2)
            ttk.Label(tab, text="H", font=self.ui.heading_font).grid(row=1, column=17, padx=2, pady=2)
            ttk.Label(tab, text="On-foot CZs", font=self.ui.heading_font, anchor=tk.CENTER).grid(row=0, column=18, columnspan=3, padx=2)
            ttk.Label(tab, text="L", font=self.ui.heading_font).grid(row=1, column=18, padx=2, pady=2)
            ttk.Label(tab, text="M", font=self.ui.heading_font).grid(row=1, column=19, padx=2, pady=2)
            ttk.Label(tab, text="H", font=self.ui.heading_font).grid(row=1, column=20, padx=2, pady=2)
            ttk.Separator(tab, orient=tk.HORIZONTAL).grid(columnspan=21, padx=2, pady=5, sticky=tk.EW)

            header_rows = 3
            x = 0

            for faction in system['Factions'].values():
                EnableCheckbutton = ttk.Checkbutton(tab)
                EnableCheckbutton.grid(row=x + header_rows, column=0, sticky=tk.N, padx=2, pady=2)
                EnableCheckbutton.configure(command=partial(self._enable_faction_change, TabParent, tab_index, EnableAllCheckbutton, FactionEnableCheckbuttons, DiscordText, activity, system, faction, x))
                EnableCheckbutton.state(['selected', '!alternate'] if faction['Enabled'] == CheckStates.STATE_ON else ['!selected', '!alternate'])
                FactionEnableCheckbuttons.append(EnableCheckbutton)

                FactionNameFrame = ttk.Frame(tab)
                FactionNameFrame.grid(row=x + header_rows, column=1, sticky=tk.NW)
                FactionName = ttk.Label(FactionNameFrame, text=faction['Faction'])
                FactionName.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=2, pady=2)
                FactionName.bind("<Button-1>", partial(self._faction_name_clicked, TabParent, tab_index, EnableCheckbutton, EnableAllCheckbutton, FactionEnableCheckbuttons, DiscordText, activity, system, faction, x))
                settlement_row_index = 1
                for settlement_name in faction.get('GroundCZSettlements', {}):
                    SettlementCheckbutton = ttk.Checkbutton(FactionNameFrame)
                    SettlementCheckbutton.grid(row=settlement_row_index, column=0, padx=2, pady=2)
                    SettlementCheckbutton.configure(command=partial(self._enable_settlement_change, SettlementCheckbutton, settlement_name, DiscordText, activity, faction, x))
                    SettlementCheckbutton.state(['selected', '!alternate'] if faction['GroundCZSettlements'][settlement_name]['enabled'] == CheckStates.STATE_ON else ['!selected', '!alternate'])
                    SettlementName = ttk.Label(FactionNameFrame, text=f"{settlement_name} ({faction['GroundCZSettlements'][settlement_name]['type'].upper()})")
                    SettlementName.grid(row=settlement_row_index, column=1, sticky=tk.W, padx=2, pady=2)
                    SettlementName.bind("<Button-1>", partial(self._settlement_name_clicked, SettlementCheckbutton, settlement_name, DiscordText, activity, faction, x))
                    settlement_row_index += 1

                ttk.Label(tab, text=faction['FactionState']).grid(row=x + header_rows, column=2, sticky=tk.N)
                MissionPointsVar = tk.IntVar(value=faction['MissionPoints'])
                ttk.Spinbox(tab, from_=-999, to=999, width=3, textvariable=MissionPointsVar).grid(row=x + header_rows, column=3, sticky=tk.N, padx=2, pady=2)
                MissionPointsVar.trace('w', partial(self._mission_points_change, TabParent, tab_index, MissionPointsVar, True, EnableAllCheckbutton, DiscordText, activity, system, faction, x))
                MissionPointsSecVar = tk.IntVar(value=faction['MissionPointsSecondary'])
                ttk.Spinbox(tab, from_=-999, to=999, width=3, textvariable=MissionPointsSecVar).grid(row=x + header_rows, column=4, sticky=tk.N, padx=2, pady=2)
                MissionPointsSecVar.trace('w', partial(self._mission_points_change, TabParent, tab_index, MissionPointsSecVar, False, EnableAllCheckbutton, DiscordText, activity, system, faction, x))
                ttk.Label(tab, text=self._human_format(faction['TradePurchase'])).grid(row=x + header_rows, column=5, sticky=tk.N)
                ttk.Label(tab, text=self._human_format(faction['TradeProfit'])).grid(row=x + header_rows, column=6, sticky=tk.N)
                ttk.Label(tab, text=self._human_format(faction['BlackMarketProfit'])).grid(row=x + header_rows, column=7, sticky=tk.N)
                ttk.Label(tab, text=self._human_format(faction['Bounties'])).grid(row=x + header_rows, column=8, sticky=tk.N)
                ttk.Label(tab, text=self._human_format(faction['CartData'])).grid(row=x + header_rows, column=9, sticky=tk.N)
                ttk.Label(tab, text=self._human_format(faction['ExoData'])).grid(row=x + header_rows, column=10, sticky=tk.N)
                ttk.Label(tab, text=self._human_format(faction['CombatBonds'])).grid(row=x + header_rows, column=11, sticky=tk.N)
                ttk.Label(tab, text=faction['MissionFailed']).grid(row=x + header_rows, column=12, sticky=tk.N)
                ttk.Label(tab, text=faction['Murdered']).grid(row=x + header_rows, column=13, sticky=tk.N)
                ScenariosVar = tk.IntVar(value=faction['Scenarios'])
                ttk.Spinbox(tab, from_=0, to=999, width=3, textvariable=ScenariosVar).grid(row=x + header_rows, column=14, sticky=tk.N, padx=2, pady=2)
                ScenariosVar.trace('w', partial(self._scenarios_change, TabParent, tab_index, ScenariosVar, EnableAllCheckbutton, DiscordText, activity, system, faction, x))

                if (faction['FactionState'] in STATES_WAR):
                    CZSpaceLVar = tk.StringVar(value=faction['SpaceCZ'].get('l', '0'))
                    ttk.Spinbox(tab, from_=0, to=999, width=3, textvariable=CZSpaceLVar).grid(row=x + header_rows, column=15, sticky=tk.N, padx=2, pady=2)
                    CZSpaceMVar = tk.StringVar(value=faction['SpaceCZ'].get('m', '0'))
                    ttk.Spinbox(tab, from_=0, to=999, width=3, textvariable=CZSpaceMVar).grid(row=x + header_rows, column=16, sticky=tk.N, padx=2, pady=2)
                    CZSpaceHVar = tk.StringVar(value=faction['SpaceCZ'].get('h', '0'))
                    ttk.Spinbox(tab, from_=0, to=999, width=3, textvariable=CZSpaceHVar).grid(row=x + header_rows, column=17, sticky=tk.N, padx=2, pady=2)
                    CZGroundLVar = tk.StringVar(value=faction['GroundCZ'].get('l', '0'))
                    ttk.Spinbox(tab, from_=0, to=999, width=3, textvariable=CZGroundLVar).grid(row=x + header_rows, column=18, sticky=tk.N, padx=2, pady=2)
                    CZGroundMVar = tk.StringVar(value=faction['GroundCZ'].get('m', '0'))
                    ttk.Spinbox(tab, from_=0, to=999, width=3, textvariable=CZGroundMVar).grid(row=x + header_rows, column=19, sticky=tk.N, padx=2, pady=2)
                    CZGroundHVar = tk.StringVar(value=faction['GroundCZ'].get('h', '0'))
                    ttk.Spinbox(tab, from_=0, to=999, width=3, textvariable=CZGroundHVar).grid(row=x + header_rows, column=20, sticky=tk.N, padx=2, pady=2)
                    # Watch for changes on all SpinBox Variables. This approach catches any change, including manual editing, while using 'command' callbacks only catches clicks
                    CZSpaceLVar.trace('w', partial(self._cz_change, TabParent, tab_index, CZSpaceLVar, EnableAllCheckbutton, DiscordText, CZs.SPACE_LOW, activity, system, faction, x))
                    CZSpaceMVar.trace('w', partial(self._cz_change, TabParent, tab_index, CZSpaceMVar, EnableAllCheckbutton, DiscordText, CZs.SPACE_MED, activity, system, faction, x))
                    CZSpaceHVar.trace('w', partial(self._cz_change, TabParent, tab_index, CZSpaceHVar, EnableAllCheckbutton, DiscordText, CZs.SPACE_HIGH, activity, system, faction, x))
                    CZGroundLVar.trace('w', partial(self._cz_change, TabParent, tab_index, CZGroundLVar, EnableAllCheckbutton, DiscordText, CZs.GROUND_LOW, activity, system, faction, x))
                    CZGroundMVar.trace('w', partial(self._cz_change, TabParent, tab_index, CZGroundMVar, EnableAllCheckbutton, DiscordText, CZs.GROUND_MED, activity, system, faction, x))
                    CZGroundHVar.trace('w', partial(self._cz_change, TabParent, tab_index, CZGroundHVar, EnableAllCheckbutton, DiscordText, CZs.GROUND_HIGH, activity, system, faction, x))

                x += 1

            self._update_enable_all_factions_checkbutton(TabParent, tab_index, EnableAllCheckbutton, FactionEnableCheckbuttons, system)

            tab.pack_forget()
            tab_index += 1

        self._update_discord_field(DiscordText, activity)

        ttk.Button(ContainerFrame, text="Copy to Clipboard (Legacy Format)", command=partial(self._copy_to_clipboard, ContainerFrame, DiscordText)).pack(side=tk.LEFT, padx=5, pady=5)
        if self.bgstally.discord.is_webhook_valid(DiscordChannel.BGS): ttk.Button(ContainerFrame, text="Post to Discord", command=partial(self._post_to_discord, activity)).pack(side=tk.RIGHT, padx=5, pady=5)

        theme.update(ContainerFrame)

        # Ignore all scroll wheel events on spinboxes, to avoid accidental inputs
        Form.bind_class('TSpinbox', '<MouseWheel>', lambda event : "break")


    def _update_discord_field(self, DiscordText, activity: Activity):
        """
        Update the contents of the Discord text field
        """
        DiscordText.configure(state='normal')
        DiscordText.delete('1.0', 'end-1c')
        DiscordText.insert(tk.INSERT, self._generate_discord_text(activity, self.bgstally.state.DiscordActivity.get()))
        DiscordText.configure(state='disabled')


    def _post_to_discord(self, activity: Activity):
        """
        Callback to post to discord
        """
        if self.bgstally.state.DiscordPostStyle.get() == DiscordPostStyle.TEXT:
            if self.bgstally.state.DiscordActivity.get() == DiscordActivity.BGS:
                # BGS Only - one post to BGS channel
                discord_text:str = self._generate_discord_text(activity, DiscordActivity.BGS)
                activity.discord_bgs_messageid = self.bgstally.discord.post_plaintext(discord_text, activity.discord_bgs_messageid, DiscordChannel.BGS)
            elif self.bgstally.state.DiscordActivity.get() == DiscordActivity.THARGOIDWAR:
                # TW Only - one post to TW channel
                discord_text:str = self._generate_discord_text(activity, DiscordActivity.THARGOIDWAR)
                activity.discord_tw_messageid = self.bgstally.discord.post_plaintext(discord_text, activity.discord_tw_messageid, DiscordChannel.THARGOIDWAR)
            elif self.bgstally.discord.is_webhook_valid(DiscordChannel.THARGOIDWAR):
                # Both, TW channel is available - two posts, one to each channel
                discord_text:str = self._generate_discord_text(activity, DiscordActivity.BGS)
                activity.discord_bgs_messageid = self.bgstally.discord.post_plaintext(discord_text, activity.discord_bgs_messageid, DiscordChannel.BGS)
                discord_text:str = self._generate_discord_text(activity, DiscordActivity.THARGOIDWAR)
                activity.discord_tw_messageid = self.bgstally.discord.post_plaintext(discord_text, activity.discord_tw_messageid, DiscordChannel.THARGOIDWAR)
            else:
                # Both, TW channel is not available - one combined post to BGS channel
                discord_text:str = self._generate_discord_text(activity, DiscordActivity.BOTH)
                activity.discord_bgs_messageid = self.bgstally.discord.post_plaintext(discord_text, activity.discord_bgs_messageid, DiscordChannel.BGS)
        else:
            if self.bgstally.state.DiscordActivity.get() == DiscordActivity.BGS:
                # BGS Only - one post to BGS channel
                discord_fields:Dict = self._generate_discord_embed_fields(activity, DiscordActivity.BGS)
                activity.discord_bgs_messageid = self.bgstally.discord.post_embed(f"BGS Activity after tick: {activity.tick_time.strftime(DATETIME_FORMAT)}", "", discord_fields, activity.discord_bgs_messageid, DiscordChannel.BGS)
            elif self.bgstally.state.DiscordActivity.get() == DiscordActivity.THARGOIDWAR:
                # TW Only - one post to TW channel
                discord_fields:Dict = self._generate_discord_embed_fields(activity, DiscordActivity.THARGOIDWAR)
                activity.discord_tw_messageid = self.bgstally.discord.post_embed(f"TW Activity after tick: {activity.tick_time.strftime(DATETIME_FORMAT)}", "", discord_fields, activity.discord_tw_messageid, DiscordChannel.THARGOIDWAR)
            elif self.bgstally.discord.is_webhook_valid(DiscordChannel.THARGOIDWAR):
                # Both, TW channel is available - two posts, one to each channel
                discord_fields:Dict = self._generate_discord_embed_fields(activity, DiscordActivity.BGS)
                activity.discord_bgs_messageid = self.bgstally.discord.post_embed(f"BGS Activity after tick: {activity.tick_time.strftime(DATETIME_FORMAT)}", "", discord_fields, activity.discord_bgs_messageid, DiscordChannel.BGS)
                discord_fields:Dict = self._generate_discord_embed_fields(activity, DiscordActivity.THARGOIDWAR)
                activity.discord_tw_messageid = self.bgstally.discord.post_embed(f"TW Activity after tick: {activity.tick_time.strftime(DATETIME_FORMAT)}", "", discord_fields, activity.discord_tw_messageid, DiscordChannel.THARGOIDWAR)
            else:
                # Both, TW channel is not available - one combined post to BGS channel
                discord_fields:Dict = self._generate_discord_embed_fields(activity, DiscordActivity.BOTH)
                activity.discord_bgs_messageid = self.bgstally.discord.post_embed(f"Activity after tick: {activity.tick_time.strftime(DATETIME_FORMAT)}", "", discord_fields, activity.discord_bgs_messageid, DiscordChannel.BGS)


    def _option_change(self, DiscordText, activity: Activity):
        """
        Callback when one of the Discord options is changed
        """
        self._update_discord_field(DiscordText, activity)


    def _enable_faction_change(self, notebook: ScrollableNotebook, tab_index: int, EnableAllCheckbutton, FactionEnableCheckbuttons, DiscordText, activity: Activity, system, faction, faction_index, *args):
        """
        Callback for when a Faction Enable Checkbutton is changed
        """
        faction['Enabled'] = CheckStates.STATE_ON if FactionEnableCheckbuttons[faction_index].instate(['selected']) else CheckStates.STATE_OFF
        self._update_enable_all_factions_checkbutton(notebook, tab_index, EnableAllCheckbutton, FactionEnableCheckbuttons, system)
        self._update_discord_field(DiscordText, activity)


    def _enable_all_factions_change(self, notebook: ScrollableNotebook, tab_index: int, EnableAllCheckbutton, FactionEnableCheckbuttons, DiscordText, activity: Activity, system, *args):
        """
        Callback for when the Enable All Factions Checkbutton is changed
        """
        x = 0
        for faction in system['Factions'].values():
            if EnableAllCheckbutton.instate(['selected']):
                FactionEnableCheckbuttons[x].state(['selected'])
                faction['Enabled'] = CheckStates.STATE_ON
            else:
                FactionEnableCheckbuttons[x].state(['!selected'])
                faction['Enabled'] = CheckStates.STATE_OFF
            x += 1

        self._update_tab_image(notebook, tab_index, EnableAllCheckbutton, system)
        self._update_discord_field(DiscordText, activity)


    def _enable_settlement_change(self, SettlementCheckbutton, settlement_name, DiscordText, activity: Activity, faction, faction_index, *args):
        """
        Callback for when a Settlement Enable Checkbutton is changed
        """
        faction['GroundCZSettlements'][settlement_name]['enabled'] = CheckStates.STATE_ON if SettlementCheckbutton.instate(['selected']) else CheckStates.STATE_OFF
        self._update_discord_field(DiscordText, activity)


    def _update_enable_all_factions_checkbutton(self, notebook: ScrollableNotebook, tab_index: int, EnableAllCheckbutton, FactionEnableCheckbuttons, system):
        """
        Update the 'Enable all factions' checkbox to the correct state based on which individual factions are enabled
        """
        any_on = False
        any_off = False
        z = len(FactionEnableCheckbuttons)
        for x in range(0, z):
            if FactionEnableCheckbuttons[x].instate(['selected']): any_on = True
            if FactionEnableCheckbuttons[x].instate(['!selected']): any_off = True

        if any_on == True:
            if any_off == True:
                EnableAllCheckbutton.state(['alternate', '!selected'])
            else:
                EnableAllCheckbutton.state(['!alternate', 'selected'])
        else:
            EnableAllCheckbutton.state(['!alternate', '!selected'])

        self._update_tab_image(notebook, tab_index, EnableAllCheckbutton, system)


    def _faction_name_clicked(self, notebook: ScrollableNotebook, tab_index: int, EnableCheckbutton, EnableAllCheckbutton, FactionEnableCheckbuttons, DiscordText, activity: Activity, system, faction, faction_index, *args):
        """
        Callback when a faction name is clicked. Toggle enabled state.
        """
        if EnableCheckbutton.instate(['selected']): EnableCheckbutton.state(['!selected'])
        else: EnableCheckbutton.state(['selected'])
        self._enable_faction_change(notebook, tab_index, EnableAllCheckbutton, FactionEnableCheckbuttons, DiscordText, activity, system, faction, faction_index, *args)


    def _settlement_name_clicked(self, SettlementCheckbutton, settlement_name, DiscordText, activity: Activity, faction, faction_index, *args):
        """
        Callback when a settlement name is clicked. Toggle enabled state.
        """
        if SettlementCheckbutton.instate(['selected']): SettlementCheckbutton.state(['!selected'])
        else: SettlementCheckbutton.state(['selected'])
        self._enable_settlement_change(SettlementCheckbutton, settlement_name, DiscordText, activity, faction, faction_index, *args)


    def _cz_change(self, notebook: ScrollableNotebook, tab_index: int, CZVar, EnableAllCheckbutton, DiscordText, cz_type, activity: Activity, system, faction, faction_index, *args):
        """
        Callback (set as a variable trace) for when a CZ Variable is changed
        """
        if cz_type == CZs.SPACE_LOW:
            faction['SpaceCZ']['l'] = CZVar.get()
        elif cz_type == CZs.SPACE_MED:
            faction['SpaceCZ']['m'] = CZVar.get()
        elif cz_type == CZs.SPACE_HIGH:
            faction['SpaceCZ']['h'] = CZVar.get()
        elif cz_type == CZs.GROUND_LOW:
            faction['GroundCZ']['l'] = CZVar.get()
        elif cz_type == CZs.GROUND_MED:
            faction['GroundCZ']['m'] = CZVar.get()
        elif cz_type == CZs.GROUND_HIGH:
            faction['GroundCZ']['h'] = CZVar.get()

        activity.recalculate_zero_activity()
        self._update_tab_image(notebook, tab_index, EnableAllCheckbutton, system)
        self._update_discord_field(DiscordText, activity)


    def _mission_points_change(self, notebook: ScrollableNotebook, tab_index: int, MissionPointsVar, primary, EnableAllCheckbutton, DiscordText, activity: Activity, system, faction, faction_index, *args):
        """
        Callback (set as a variable trace) for when a mission points Variable is changed
        """
        if primary:
            faction['MissionPoints'] = MissionPointsVar.get()
        else:
            faction['MissionPointsSecondary'] = MissionPointsVar.get()

        activity.recalculate_zero_activity()
        self._update_tab_image(notebook, tab_index, EnableAllCheckbutton, system)
        self._update_discord_field(DiscordText, activity)


    def _scenarios_change(self, notebook: ScrollableNotebook, tab_index: int, ScenariosVar, EnableAllCheckbutton, DiscordText, activity: Activity, system, faction, faction_index, *args):
        """
        Callback (set as a variable trace) for when the scenarios Variable is changed
        """
        faction['Scenarios'] = ScenariosVar.get()

        activity.recalculate_zero_activity()
        self._update_tab_image(notebook, tab_index, EnableAllCheckbutton, system)
        self._update_discord_field(DiscordText, activity)


    def _update_tab_image(self, notebook: ScrollableNotebook, tab_index: int, EnableAllCheckbutton, system: Dict):
        """
        Update the image alongside the tab title
        """
        if EnableAllCheckbutton.instate(['selected']):
            if system['zero_system_activity']: notebook.notebookTab.tab(tab_index, image=self.image_tab_inactive_enabled)
            else: notebook.notebookTab.tab(tab_index, image=self.image_tab_active_enabled)
        else:
            if EnableAllCheckbutton.instate(['alternate']):
                if system['zero_system_activity']: notebook.notebookTab.tab(tab_index, image=self.image_tab_inactive_part_enabled)
                else: notebook.notebookTab.tab(tab_index, image=self.image_tab_active_part_enabled)
            else:
                if system['zero_system_activity']: notebook.notebookTab.tab(tab_index, image=self.image_tab_inactive_disabled)
                else: notebook.notebookTab.tab(tab_index, image=self.image_tab_active_disabled)


    def _process_faction_name(self, faction_name):
        """
        Shorten the faction name if the user has chosen to
        """
        if self.bgstally.state.AbbreviateFactionNames.get() == CheckStates.STATE_ON:
            return ''.join((i if i.isnumeric() else i[0]) for i in faction_name.split())
        else:
            return faction_name


    def _generate_discord_text(self, activity: Activity, activity_mode: DiscordActivity):
        """
        Generate text for a plain text Discord post
        """
        discord_text = ""

        for system in activity.systems.values():
            system_discord_text = ""

            if activity_mode == DiscordActivity.THARGOIDWAR or activity_mode == DiscordActivity.BOTH:
                system_discord_text += self._generate_tw_system_discord_text(system)

            if activity_mode == DiscordActivity.BGS or activity_mode == DiscordActivity.BOTH:
                for faction in system['Factions'].values():
                    if faction['Enabled'] != CheckStates.STATE_ON: continue
                    system_discord_text += self._generate_faction_discord_text(faction)

            if system_discord_text != "":
                discord_text += f"```css\n{system['System']}\n{system_discord_text}```"

        return discord_text.replace("'", "")


    def _generate_discord_embed_fields(self, activity: Activity, activity_mode: DiscordActivity):
        """
        Generate fields for a Discord post with embed
        """
        discord_fields = []

        for system in activity.systems.values():
            system_discord_text = ""

            if activity_mode == DiscordActivity.THARGOIDWAR or activity_mode == DiscordActivity.BOTH:
                system_discord_text += self._generate_tw_system_discord_text(system)

            if activity_mode == DiscordActivity.BGS or activity_mode == DiscordActivity.BOTH:
                for faction in system['Factions'].values():
                    if faction['Enabled'] != CheckStates.STATE_ON: continue
                    system_discord_text += self._generate_faction_discord_text(faction)

            if system_discord_text != "":
                system_discord_text = system_discord_text.replace("'", "")
                discord_field = {'name': system['System'], 'value': f"```css\n{system_discord_text}```"}
                discord_fields.append(discord_field)

        return discord_fields


    def _generate_faction_discord_text(self, faction:Dict):
        """
        Generate formatted Discord text for a faction
        """
        activity_discord_text = ""

        inf = faction['MissionPoints']
        if self.bgstally.state.IncludeSecondaryInf.get() == CheckStates.STATE_ON: inf += faction['MissionPointsSecondary']

        if faction['FactionState'] in STATES_ELECTION:
            activity_discord_text += f".ElectionINF +{inf}; " if inf > 0 else f".ElectionINF {inf}; " if inf < 0 else ""
        elif faction['FactionState'] in STATES_WAR:
            activity_discord_text += f".WarINF +{inf}; " if inf > 0 else f".WarINF {inf}; " if inf < 0 else ""
        else:
            activity_discord_text += f".INF +{inf}; " if inf > 0 else f".INF {inf}; " if inf < 0 else ""

        activity_discord_text += f".BVs {self._human_format(faction['Bounties'])}; " if faction['Bounties'] != 0 else ""
        activity_discord_text += f".CBs {self._human_format(faction['CombatBonds'])}; " if faction['CombatBonds'] != 0 else ""
        activity_discord_text += f".TrdPurchase {self._human_format(faction['TradePurchase'])}; " if faction['TradePurchase'] != 0 else ""
        activity_discord_text += f".TrdProfit {self._human_format(faction['TradeProfit'])}; " if faction['TradeProfit'] != 0 else ""
        activity_discord_text += f".TrdBMProfit {self._human_format(faction['BlackMarketProfit'])}; " if faction['BlackMarketProfit'] != 0 else ""
        activity_discord_text += f".Expl {self._human_format(faction['CartData'])}; " if faction['CartData'] != 0 else ""
        activity_discord_text += f".Exo {self._human_format(faction['ExoData'])}; " if faction['ExoData'] != 0 else ""
        activity_discord_text += f".Murders {faction['Murdered']}; " if faction['Murdered'] != 0 else ""
        activity_discord_text += f".Scenarios {faction['Scenarios']}; " if faction['Scenarios'] != 0 else ""
        activity_discord_text += f".Fails {faction['MissionFailed']}; " if faction['MissionFailed'] != 0 else ""
        space_cz = self._build_cz_text(faction.get('SpaceCZ', {}), "SpaceCZs")
        activity_discord_text += f"{space_cz}; " if space_cz != "" else ""
        ground_cz = self._build_cz_text(faction.get('GroundCZ', {}), "GroundCZs")
        activity_discord_text += f"{ground_cz}; " if ground_cz != "" else ""

        faction_name = self._process_faction_name(faction['Faction'])
        faction_discord_text = f"[{faction_name}] - {activity_discord_text}\n" if activity_discord_text != "" else ""

        for settlement_name in faction.get('GroundCZSettlements', {}):
            if faction['GroundCZSettlements'][settlement_name]['enabled'] == CheckStates.STATE_ON:
                faction_discord_text += f"  ⚔️ {settlement_name} x {faction['GroundCZSettlements'][settlement_name]['count']}\n"

        return faction_discord_text


    def _generate_tw_system_discord_text(self, system:Dict):
        """
        Create formatted Discord text for Thargoid War in a system
        """
        system_discord_text = ""
        system_stations = {}

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
                system_station['mission_count_total'] += faction_station['passengers']['l']['count'] + faction_station['passengers']['m']['count'] + faction_station['passengers']['h']['count']
                # Current understanding is it is important to report each type of escape pod evac mission separately
                system_station['escapepods']['l']['count'] += faction_station['escapepods']['l']['count']
                system_station['escapepods']['l']['sum'] += faction_station['escapepods']['l']['sum']
                system_station['escapepods']['m']['count'] += faction_station['escapepods']['m']['count']
                system_station['escapepods']['m']['sum'] += faction_station['escapepods']['m']['sum']
                system_station['escapepods']['h']['count'] += faction_station['escapepods']['h']['count']
                system_station['escapepods']['h']['sum'] += faction_station['escapepods']['h']['sum']
                system_station['mission_count_total'] += faction_station['escapepods']['l']['count'] + faction_station['escapepods']['m']['count'] + faction_station['escapepods']['h']['count']
                # We don't track different priorities of cargo missions
                system_station['cargo']['count'] += faction_station['cargo']['count']
                system_station['cargo']['sum'] += faction_station['cargo']['sum']
                system_station['mission_count_total'] += faction_station['cargo']['count']

        for system_station_name, system_station in system_stations.items():
            system_discord_text += f"🍀 {system_station_name}: {system_station['mission_count_total']} missions\n"
            if (system_station['escapepods']['m']['sum'] > 0):
                system_discord_text += f"  ❕ x {system_station['escapepods']['m']['sum']} - {system_station['escapepods']['m']['count']} missions\n"
            if (system_station['escapepods']['h']['sum'] > 0):
                system_discord_text += f"  ❗ x {system_station['escapepods']['h']['sum']} - {system_station['escapepods']['h']['count']} missions\n"
            if (system_station['cargo']['sum'] > 0):
                system_discord_text += f"  📦 x {system_station['cargo']['sum']} - {system_station['cargo']['count']} missions\n"
            if (system_station['escapepods']['l']['sum'] > 0):
                system_discord_text += f"  ⚕️ x {system_station['escapepods']['l']['sum']} - {system_station['escapepods']['l']['count']} missions\n"
            if (system_station['passengers']['sum'] > 0):
                system_discord_text += f"  🧍 x {system_station['passengers']['sum']} - {system_station['passengers']['count']} missions\n"

        return system_discord_text


    def _get_new_aggregate_tw_station_data(self):
        """
        Get a new data structure for storing Thargoid War station data
        """
        return {'mission_count_total': 0,
                'passengers': {'count': 0, 'sum': 0},
                'escapepods': {'l': {'count': 0, 'sum': 0}, 'm': {'count': 0, 'sum': 0}, 'h': {'count': 0, 'sum': 0}},
                'cargo': {'count': 0, 'sum': 0}}


    def _build_cz_text(self, cz_data, prefix):
        """
        Create a summary of Conflict Zone activity
        """
        if cz_data == {}: return ""
        text = ""

        if 'l' in cz_data and cz_data['l'] != '0' and cz_data['l'] != '': text += f"{cz_data['l']}xL "
        if 'm' in cz_data and cz_data['m'] != '0' and cz_data['m'] != '': text += f"{cz_data['m']}xM "
        if 'h' in cz_data and cz_data['h'] != '0' and cz_data['h'] != '': text += f"{cz_data['h']}xH "

        if text != '': text = f".{prefix} {text}"
        return text


    def _human_format(self, num):
        """
        Format a BGS value into shortened human-readable text
        """
        num = float('{:.3g}'.format(num))
        magnitude = 0
        while abs(num) >= 1000:
            magnitude += 1
            num /= 1000.0
        return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])


    def _copy_to_clipboard(self, Form, DiscordText):
        """
        Get all text from the Discord field and put it in the Copy buffer
        """
        Form.clipboard_clear()
        Form.event_generate("<<TextModified>>")
        Form.clipboard_append(DiscordText.get('1.0', 'end-1c'))
        Form.update()

