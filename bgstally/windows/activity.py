import tkinter as tk
from functools import partial
from os import path
from tkinter import PhotoImage, ttk

from ttkHyperlinkLabel import HyperlinkLabel

from bgstally.activity import STATES_WAR, Activity
from bgstally.constants import (COLOUR_HEADING_1, FOLDER_ASSETS, FONT_HEADING_1, FONT_HEADING_2, FONT_TEXT, CheckStates, CZs, DiscordActivity, DiscordChannel,
                                DiscordPostStyle)
from bgstally.debug import Debug
from bgstally.utils import _, __, human_format
from bgstally.widgets import DiscordAnsiColorText, TextPlus
from thirdparty.colors import *
from thirdparty.ScrollableNotebook import ScrollableNotebook
from thirdparty.Tooltip import ToolTip

LIMIT_TABS = 60


class WindowActivity:
    """
    Handles an activity window
    """

    def __init__(self, bgstally, ui, activity: Activity):
        self.bgstally = bgstally
        self.activity:Activity = activity
        self.toplevel:tk.Toplevel = None
        self.window_geometry:dict = None

        self.image_tab_active_enabled = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_enabled.png"))
        self.image_tab_active_part_enabled = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_part_enabled.png"))
        self.image_tab_active_disabled = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_active_disabled.png"))
        self.image_tab_inactive_enabled = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_inactive_enabled.png"))
        self.image_tab_inactive_part_enabled = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_inactive_part_enabled.png"))
        self.image_tab_inactive_disabled = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "tab_inactive_disabled.png"))

        self.show(activity)


    def show(self, activity: Activity):
        """
        Show our window
        """
        # If we already have a window, save its geometry and close it before we create a new one.
        if self.toplevel is not None and self.toplevel.winfo_exists():
            self._store_window_geometry()
            self.toplevel.destroy()

        self.toplevel = tk.Toplevel(self.bgstally.ui.frame)
        self.toplevel.title(_("{plugin_name} - Activity After Tick at: {tick_time}").format(plugin_name=self.bgstally.plugin_name, tick_time=activity.get_title())) # LANG: Activity window title
        self.toplevel.protocol("WM_DELETE_WINDOW", self._window_closed)
        self.toplevel.iconphoto(False, self.bgstally.ui.image_logo_bgstally_32, self.bgstally.ui.image_logo_bgstally_16)

        if self.window_geometry is not None:
            self.toplevel.geometry(f"+{self.window_geometry['x']}+{self.window_geometry['y']}")

        ContainerFrame = ttk.Frame(self.toplevel)
        ContainerFrame.pack(fill=tk.BOTH, expand=tk.YES)
        nb_tab=ScrollableNotebook(ContainerFrame, wheelscroll=False, tabmenu=True)
        nb_tab.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)

        frm_buttons:ttk.Frame = ttk.Frame(ContainerFrame)
        frm_buttons.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(frm_buttons, text=_("Copy to Clipboard (Legacy Format)"), command=partial(self._copy_to_clipboard, ContainerFrame, activity)).pack(side=tk.LEFT, padx=5, pady=5) # LANG: Button label
        self.btn_post_to_discord: ttk.Button = ttk.Button(frm_buttons, text=_("Post to Discord"), command=partial(self._post_to_discord, activity), # LANG: Button label
                                                          state=(tk.NORMAL if self._discord_button_available() else tk.DISABLED))
        self.btn_post_to_discord.pack(side=tk.RIGHT, padx=5, pady=5)
        activity_type_options: dict = {DiscordActivity.BOTH: _("All"), # LANG: Dropdown menu on activity window
                                       DiscordActivity.BGS: _("BGS Only"), # LANG: Dropdown menu on activity window
                                       DiscordActivity.THARGOIDWAR: _("TW Only")} # LANG: Dropdown menu on activity window
        activity_type_var: tk.StringVar = tk.StringVar(value=activity_type_options.get(self.bgstally.state.DiscordActivity.get(), DiscordActivity.BOTH))
        self.mnu_activity_type: ttk.OptionMenu = ttk.OptionMenu(frm_buttons, activity_type_var, activity_type_var.get(),
                                                               *activity_type_options.values(),
                                                               command=partial(self._activity_type_selected, activity_type_options), direction='above')
        self.mnu_activity_type.pack(side=tk.RIGHT, pady=5)
        ttk.Label(frm_buttons, text="Activity to post:").pack(side=tk.RIGHT, pady=5)

        frm_discord = ttk.Frame(ContainerFrame)
        frm_discord.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        frm_discord.columnconfigure(0, weight=2)
        frm_discord.columnconfigure(1, weight=1)
        lbl_discord_report:ttk.Label = ttk.Label(frm_discord, text=_("❓ Discord Report Preview"), font=FONT_HEADING_2, cursor="hand2") # LANG: Label on activity window
        lbl_discord_report.grid(row=0, column=0, sticky=tk.W)
        lbl_discord_report.bind("<Button-1>", self._show_legend_window)
        ToolTip(lbl_discord_report, text=_("Show legend window")) # LANG: Activity window tooltip
        ttk.Label(frm_discord, text=_("Discord Additional Notes"), font=FONT_HEADING_2).grid(row=0, column=1, sticky=tk.W) # LANG: Label on activity window
        ttk.Label(frm_discord, text=_("Discord Options"), font=FONT_HEADING_2).grid(row=0, column=2, sticky=tk.W) # LANG: Label on activity window
        ttk.Label(frm_discord, text=_("Double-check on-ground CZ tallies, sizes are not always correct"), foreground='#f00').grid(row=1, column=0, columnspan=3, sticky=tk.W) # LANG: Label on activity window

        frm_discordtext = ttk.Frame(frm_discord)
        frm_discordtext.grid(row=2, column=0, pady=5, sticky=tk.NSEW)
        txt_discord = DiscordAnsiColorText(frm_discordtext, state=tk.DISABLED, wrap=tk.WORD, bg="Gray13", height=15, font=FONT_TEXT)
        sb_discord = tk.Scrollbar(frm_discordtext, orient=tk.VERTICAL, command=txt_discord.yview)
        txt_discord['yscrollcommand'] = sb_discord.set
        sb_discord.pack(fill=tk.Y, side=tk.RIGHT)
        txt_discord.pack(fill=tk.BOTH, side=tk.LEFT, expand=tk.YES)

        frm_discordnotes = ttk.Frame(frm_discord)
        frm_discordnotes.grid(row=2, column=1, pady=5, sticky=tk.NSEW)
        txt_discordnotes = TextPlus(frm_discordnotes, wrap=tk.WORD, width=30, height=1, font=FONT_TEXT)
        txt_discordnotes.insert(tk.END, "" if activity.discord_notes is None else activity.discord_notes)
        txt_discordnotes.bind("<<Modified>>", partial(self._discord_notes_change, txt_discordnotes, txt_discord, activity))
        sb_discordnotes = tk.Scrollbar(frm_discordnotes, orient=tk.VERTICAL, command=txt_discordnotes.yview)
        txt_discordnotes['yscrollcommand'] = sb_discordnotes.set
        sb_discordnotes.pack(fill=tk.Y, side=tk.RIGHT)
        txt_discordnotes.pack(fill=tk.BOTH, side=tk.LEFT, expand=tk.YES)

        frm_discordoptions = ttk.Frame(frm_discord)
        frm_discordoptions.grid(row=2, column=2, padx=5, pady=5, sticky=tk.NW)
        current_row = 1
        ttk.Label(frm_discordoptions, text=_("Post Format")).grid(row=current_row, column=0, padx=10, sticky=tk.W) # LANG: Radio group title
        ttk.Radiobutton(frm_discordoptions, text=_("Modern"), variable=self.bgstally.state.DiscordPostStyle, value=DiscordPostStyle.EMBED).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Radio button label
        ttk.Radiobutton(frm_discordoptions, text=_("Legacy"), variable=self.bgstally.state.DiscordPostStyle, value=DiscordPostStyle.TEXT).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Radio button label
        ttk.Label(frm_discordoptions, text=_("Other Options")).grid(row=current_row, column=0, padx=10, sticky=tk.W) # LANG: Options group title
        ttk.Checkbutton(frm_discordoptions, text=_("Abbreviate Faction Names"), variable=self.bgstally.state.AbbreviateFactionNames, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=partial(self._option_change, txt_discord, activity)).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Checkbox label
        ttk.Checkbutton(frm_discordoptions, text=_("Show Detailed INF"), variable=self.bgstally.state.DetailedInf, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=partial(self._option_change, txt_discord, activity)).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Checkbox label
        ttk.Checkbutton(frm_discordoptions, text=_("Include Secondary INF"), variable=self.bgstally.state.IncludeSecondaryInf, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=partial(self._option_change, txt_discord, activity)).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Checkbox label
        ttk.Checkbutton(frm_discordoptions, text=_("Show Detailed Trade"), variable=self.bgstally.state.DetailedTrade, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=partial(self._option_change, txt_discord, activity)).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Checkbox label
        ttk.Checkbutton(frm_discordoptions, text=_("Report Newly Visited System Activity By Default"), variable=self.bgstally.state.EnableSystemActivityByDefault, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Checkbox label

        system_list = activity.get_ordered_systems()

        tab_index = 0

        for system_id in system_list:
            if tab_index > LIMIT_TABS: # If we try to draw too many, the plugin simply hangs
                Debug.logger.warn(f"Window tab limit ({LIMIT_TABS}) exceeded, skipping remaining tabs")
                break

            system = activity.systems[system_id]

            if self.bgstally.state.ShowZeroActivitySystems.get() == CheckStates.STATE_OFF \
                and system['zero_system_activity'] \
                and str(system_id) != self.bgstally.state.current_system_id:
                continue

            tab:ttk.Frame = ttk.Frame(nb_tab)
            nb_tab.add(tab, text=system['System'], compound='right', image=self.image_tab_active_enabled)

            frm_header:ttk.Frame = ttk.Frame(tab)
            frm_header.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
            ttk.Label(frm_header, text=system['System'], font=FONT_HEADING_1, foreground=COLOUR_HEADING_1).grid(row=0, column=0, padx=2, pady=2, sticky=tk.W)
            HyperlinkLabel(frm_header, text=_("Inara ⤴"), url=f"https://inara.cz/elite/starsystem/?search={system['System']}", underline=True).grid(row=0, column=1, padx=2, pady=2, sticky=tk.W) # LANG: Inara link

            if self.activity == self.bgstally.activity_manager.get_current_activity():
                # Current tick activity
                chk_pin_to_overlay:ttk.Checkbutton = ttk.Checkbutton(frm_header, text=_("Pin {system_name} to Overlay").format(system_name=system['System'])) # LANG: Checkbox label
                chk_pin_to_overlay.grid(row=0, column=2, padx=2, pady=2, sticky=tk.E)
                chk_pin_to_overlay.configure(command=partial(self._pin_overlay_change, chk_pin_to_overlay, system), state=self.bgstally.ui.overlay_options_state())
                chk_pin_to_overlay.state(['selected', '!alternate'] if system.get('PinToOverlay') == CheckStates.STATE_ON else ['!selected', '!alternate'])
                frm_header.columnconfigure(2, weight=1) # Make the final column (pin checkbutton) fill available space
            else:
                # Previous tick activity
                frm_header.columnconfigure(1, weight=1) # Make the final column (Inara link) fill available space

            if system.get('tw_status') is not None:
                # TW system, skip all BGS
                ttk.Label(frm_header, text=_("Thargoid War System, no BGS Activity is Counted"), font=FONT_HEADING_2).grid(row=1, column=0, columnspan=3, padx=2, pady=2, sticky=tk.W) # LANG: Label on activity window
            elif len(system['Factions']) == 0:
                # Empty system
                ttk.Label(frm_header, text=_("Empty System, no BGS Activity Available"), font=FONT_HEADING_2).grid(row=1, column=0, columnspan=3, padx=2, pady=2, sticky=tk.W) # LANG: Label on activity window
            else:
                # BGS system
                frm_table:ttk.Frame = ttk.Frame(tab)
                frm_table.pack(fill=tk.BOTH, side=tk.TOP, padx=5, pady=5, expand=tk.YES)
                frm_table.columnconfigure(1, weight=1) # Make the second column (faction name) fill available space

                FactionEnableCheckbuttons: list = []

                ttk.Label(frm_table, text=_("Include"), font=FONT_HEADING_2).grid(row=0, column=0, padx=2, pady=2) # LANG: Checkbox label
                chk_enable_all = ttk.Checkbutton(frm_table)
                chk_enable_all.grid(row=1, column=0, padx=2, pady=2)
                chk_enable_all.configure(command=partial(self._enable_all_factions_change, nb_tab, tab_index, chk_enable_all, FactionEnableCheckbuttons, txt_discord, activity, system))
                chk_enable_all.state(['!alternate'])
                ToolTip(chk_enable_all, text=_("Enable / disable all factions")) # LANG: Activity window tooltip

                col: int = 1
                ttk.Label(frm_table, text=_("Faction"), font=FONT_HEADING_2).grid(row=0, column=col, padx=2, pady=2); col += 1 # LANG: Activity window column title
                ttk.Label(frm_table, text=_("State"), font=FONT_HEADING_2).grid(row=0, column=col, padx=2, pady=2); col += 1 # LANG: Activity window column title
                lbl_inf: ttk.Label = ttk.Label(frm_table, text="INF", font=FONT_HEADING_2, anchor=tk.CENTER) # LANG: Activity window column title, abbreviation for influence
                lbl_inf.grid(row=0, column=col, columnspan=2, padx=2)
                ToolTip(lbl_inf, text=_("Influence")) # LANG: Activity window tooltip
                lbl_pri: ttk.Label = ttk.Label(frm_table, text=_("Pri"), font=FONT_HEADING_2) # LANG: Activity window column title, abbreviation for primary
                lbl_pri.grid(row=1, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_pri, text=_("Primary")) # LANG: Activity window tooltip
                lbl_sec: ttk.Label = ttk.Label(frm_table, text=_("Sec"), font=FONT_HEADING_2) # LANG: Activity window column title, abbreviation for secondary
                lbl_sec.grid(row=1, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_sec, text=_("Secondary")) # LANG: Activity window tooltip
                ttk.Label(frm_table, text=_("Trade"), font=FONT_HEADING_2, anchor=tk.CENTER).grid(row=0, column=col, columnspan=3, padx=2) # LANG: Activity window column title
                lbl_purch: ttk.Label = ttk.Label(frm_table, text=_("Purch"), font=FONT_HEADING_2) # LANG: Activity window column title, abbreviation for purchase
                lbl_purch.grid(row=1, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_purch, text=_("Purchase at L | M | H supply")) # LANG: Activity window tooltip for purchase at low | medium | high supply
                lbl_prof: ttk.Label = ttk.Label(frm_table, text=_("Prof"), font=FONT_HEADING_2) # LANG: Activity window column title, abbreviation for profit
                lbl_prof.grid(row=1, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_prof, text=_("Profit at Z | L | M | H demand")) # LANG: Activity window tooltip for profit at zero | low | medium | high demand
                lbl_bmprof: ttk.Label = ttk.Label(frm_table, text=_("BM Prof"), font=FONT_HEADING_2) # LANG: Activity window column title, abbreviation for black market profit
                lbl_bmprof.grid(row=1, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_bmprof, text=_("Black market profit")) # LANG: Activity window tooltip
                lbl_bvs: ttk.Label = ttk.Label(frm_table, text="BVs", font=FONT_HEADING_2) # LANG: Activity window column title, abbreviation for bounty vouchers
                lbl_bvs.grid(row=0, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_bvs, text=_("Bounty vouchers")) # LANG: Activity window tooltip
                lbl_expl: ttk.Label = ttk.Label(frm_table, text=_("Expl"), font=FONT_HEADING_2)
                lbl_expl.grid(row=0, column=col, padx=2, pady=2); col += 1 # LANG: Activity window column title, abbreviation for exploration
                ToolTip(lbl_expl, text=_("Exploration data")) # LANG: Activity window tooltip
                #ttk.Label(frm_table, text=_("Exo"), font=FONT_HEADING_2).grid(row=0, column=col, padx=2, pady=2); col += 1 # LANG: Activity window column title, abbreviation for exobiology
                lbl_cbs: ttk.Label = ttk.Label(frm_table, text="CBs", font=FONT_HEADING_2) # LANG: Activity window column title, abbreviation for combat bonds
                lbl_cbs.grid(row=0, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_cbs, text=_("Combat bonds")) # LANG: Activity window tooltip
                lbl_fails: ttk.Label = ttk.Label(frm_table, text=_("Fails"), font=FONT_HEADING_2) # LANG: Activity window column title, abbreviation for mission fails
                lbl_fails.grid(row=0, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_fails, text=_("Mission fails")) # LANG: Activity window tooltip
                ttk.Label(frm_table, text=_("Murders"), font=FONT_HEADING_2, anchor=tk.CENTER).grid(row=0, column=col, columnspan=2, padx=2, pady=2) # LANG: Activity window column title
                ttk.Label(frm_table, text=_("Ground"), font=FONT_HEADING_2).grid(row=1, column=col, padx=2, pady=2); col += 1 # LANG: Activity window column title
                ttk.Label(frm_table, text=_("Ship"), font=FONT_HEADING_2).grid(row=1, column=col, padx=2, pady=2); col += 1 # LANG: Activity window column title
                lbl_scens: ttk.Label = ttk.Label(frm_table, text=_("Scens"), font=FONT_HEADING_2) # LANG: Activity window column title, abbreviation for scenarios
                lbl_scens.grid(row=0, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_scens, text=_("Scenario wins")) # LANG: Activity window tooltip
                lbl_sandr: ttk.Label = ttk.Label(frm_table, text=_("SandR"), font=FONT_HEADING_2) # LANG: Activity window column title, abbreviation for search and rescue
                lbl_sandr.grid(row=0, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_sandr, text=_("Search and rescue")) # LANG: Activity window tooltip
                lbl_spaceczs: ttk.Label = ttk.Label(frm_table, text=_("SpaceCZs"), font=FONT_HEADING_2, anchor=tk.CENTER) # LANG: Activity window column title, abbreviation for space conflict zones
                lbl_spaceczs.grid(row=0, column=col, columnspan=3, padx=2)
                ToolTip(lbl_spaceczs, text=_("Space conflict zones")) # LANG: Activity window tooltip
                lbl_spaceczl: ttk.Label = ttk.Label(frm_table, text="L", font=FONT_HEADING_2)
                lbl_spaceczl.grid(row=1, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_spaceczl, text=_("Low")) # LANG: Activity window tooltip
                lbl_spaceczm: ttk.Label = ttk.Label(frm_table, text="M", font=FONT_HEADING_2)
                lbl_spaceczm.grid(row=1, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_spaceczm, text=_("Medium")) # LANG: Activity window tooltip
                lbl_spaceczh: ttk.Label = ttk.Label(frm_table, text="H", font=FONT_HEADING_2)
                lbl_spaceczh.grid(row=1, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_spaceczh, text=_("High")) # LANG: Activity window tooltip
                lbl_groundczs: ttk.Label = ttk.Label(frm_table, text=_("GroundCZs"), font=FONT_HEADING_2, anchor=tk.CENTER)
                lbl_groundczs.grid(row=0, column=col, columnspan=3, padx=2) # LANG: Activity window column title, abbreviation for ground conflict zones
                ToolTip(lbl_groundczs, text=_("Ground conflict zones")) # LANG: Activity window tooltip
                lbl_groundczl: ttk.Label = ttk.Label(frm_table, text="L", font=FONT_HEADING_2)
                lbl_groundczl.grid(row=1, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_groundczl, text=_("Low")) # LANG: Activity window tooltip
                lbl_groundczm: ttk.Label = ttk.Label(frm_table, text="M", font=FONT_HEADING_2)
                lbl_groundczm.grid(row=1, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_groundczm, text=_("Medium")) # LANG: Activity window tooltip
                lbl_groundczh: ttk.Label = ttk.Label(frm_table, text="H", font=FONT_HEADING_2)
                lbl_groundczh.grid(row=1, column=col, padx=2, pady=2); col += 1
                ToolTip(lbl_groundczh, text=_("High")) # LANG: Activity window tooltip
                ttk.Separator(frm_table, orient=tk.HORIZONTAL).grid(columnspan=col, padx=2, pady=5, sticky=tk.EW)

                header_rows = 3
                x = 0

                for faction in system['Factions'].values():
                    chk_enable = ttk.Checkbutton(frm_table)
                    chk_enable.grid(row=x + header_rows, column=0, sticky=tk.N, padx=2, pady=2)
                    chk_enable.configure(command=partial(self._enable_faction_change, nb_tab, tab_index, chk_enable_all, FactionEnableCheckbuttons, txt_discord, activity, system, faction, x))
                    chk_enable.state(['selected', '!alternate'] if faction['Enabled'] == CheckStates.STATE_ON else ['!selected', '!alternate'])
                    ToolTip(chk_enable, text=_("Enable / disable faction")) # LANG: Activity window tooltip
                    FactionEnableCheckbuttons.append(chk_enable)

                    frm_faction = ttk.Frame(frm_table)
                    frm_faction.grid(row=x + header_rows, column=1, sticky=tk.NW)
                    lbl_faction = ttk.Label(frm_faction, text=faction['Faction'])
                    lbl_faction.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=2, pady=2)
                    lbl_faction.bind("<Button-1>", partial(self._faction_name_clicked, nb_tab, tab_index, chk_enable, chk_enable_all, FactionEnableCheckbuttons, txt_discord, activity, system, faction, x))
                    settlement_row_index = 1
                    for settlement_name in faction.get('GroundCZSettlements', {}):
                        chk_settlement = ttk.Checkbutton(frm_faction)
                        chk_settlement.grid(row=settlement_row_index, column=0, padx=2, pady=2)
                        chk_settlement.configure(command=partial(self._enable_settlement_change, chk_settlement, settlement_name, txt_discord, activity, faction, x))
                        chk_settlement.state(['selected', '!alternate'] if faction['GroundCZSettlements'][settlement_name]['enabled'] == CheckStates.STATE_ON else ['!selected', '!alternate'])
                        lbl_settlement = ttk.Label(frm_faction, text=f"{settlement_name} ({faction['GroundCZSettlements'][settlement_name]['type'].upper()})")
                        lbl_settlement.grid(row=settlement_row_index, column=1, sticky=tk.W, padx=2, pady=2)
                        lbl_settlement.bind("<Button-1>", partial(self._settlement_name_clicked, chk_settlement, settlement_name, txt_discord, activity, faction, x))
                        settlement_row_index += 1

                    col = 2
                    ttk.Label(frm_table, text=faction['FactionState']).grid(row=x + header_rows, column=col, sticky=tk.N); col += 1
                    MissionPointsVar = tk.IntVar(value=faction['MissionPoints']['m'])
                    ttk.Spinbox(frm_table, from_=-999, to=999, width=3, textvariable=MissionPointsVar).grid(row=x + header_rows, column=col, sticky=tk.N, padx=2, pady=2); col += 1
                    MissionPointsVar.trace('w', partial(self._mission_points_change, nb_tab, tab_index, MissionPointsVar, True, chk_enable_all, txt_discord, activity, system, faction, x))
                    MissionPointsSecVar = tk.IntVar(value=faction['MissionPointsSecondary']['m'])
                    ttk.Spinbox(frm_table, from_=-999, to=999, width=3, textvariable=MissionPointsSecVar).grid(row=x + header_rows, column=col, sticky=tk.N, padx=2, pady=2); col += 1
                    MissionPointsSecVar.trace('w', partial(self._mission_points_change, nb_tab, tab_index, MissionPointsSecVar, False, chk_enable_all, txt_discord, activity, system, faction, x))
                    if faction['TradePurchase'] > 0:
                        ttk.Label(frm_table, text=human_format(faction['TradePurchase'])).grid(row=x + header_rows, column=col, sticky=tk.N); col += 1
                        ttk.Label(frm_table, text=human_format(faction['TradeProfit'])).grid(row=x + header_rows, column=col, sticky=tk.N); col += 1
                    else:
                        ttk.Label(frm_table, text=f"{human_format(faction['TradeBuy'][1]['value'])} | {human_format(faction['TradeBuy'][2]['value'])} | {human_format(faction['TradeBuy'][3]['value'])}").grid(row=x + header_rows, column=col, sticky=tk.N, padx=4); col += 1
                        ttk.Label(frm_table, text=f"{human_format(faction['TradeSell'][0]['profit'])} | {human_format(faction['TradeBuy'][1]['value'])} | {human_format(faction['TradeSell'][2]['profit'])} | {human_format(faction['TradeSell'][3]['profit'])}").grid(row=x + header_rows, column=col, sticky=tk.N, padx=4); col += 1
                    ttk.Label(frm_table, text=human_format(faction['BlackMarketProfit'])).grid(row=x + header_rows, column=col, sticky=tk.N); col += 1
                    ttk.Label(frm_table, text=human_format(faction['Bounties'])).grid(row=x + header_rows, column=col, sticky=tk.N); col += 1
                    ttk.Label(frm_table, text=human_format(faction['CartData'])).grid(row=x + header_rows, column=col, sticky=tk.N); col += 1
                    #ttk.Label(frm_table, text=human_format(faction['ExoData'])).grid(row=x + header_rows, column=col, sticky=tk.N); col += 1
                    ttk.Label(frm_table, text=human_format(faction['CombatBonds'])).grid(row=x + header_rows, column=col, sticky=tk.N); col += 1
                    ttk.Label(frm_table, text=faction['MissionFailed']).grid(row=x + header_rows, column=col, sticky=tk.N); col += 1
                    ttk.Label(frm_table, text=faction['GroundMurdered']).grid(row=x + header_rows, column=col, sticky=tk.N); col += 1
                    ttk.Label(frm_table, text=faction['Murdered']).grid(row=x + header_rows, column=col, sticky=tk.N); col += 1
                    ScenariosVar = tk.IntVar(value=faction['Scenarios'])
                    ttk.Spinbox(frm_table, from_=0, to=999, width=3, textvariable=ScenariosVar).grid(row=x + header_rows, column=col, sticky=tk.N, padx=2, pady=2); col += 1
                    ScenariosVar.trace('w', partial(self._scenarios_change, nb_tab, tab_index, ScenariosVar, chk_enable_all, txt_discord, activity, system, faction, x))
                    ttk.Label(frm_table, text=sum(faction.get('SandR', {}).values())).grid(row=x + header_rows, column=col, sticky=tk.N); col += 1

                    if (faction['FactionState'] in STATES_WAR):
                        CZSpaceLVar = tk.StringVar(value=faction['SpaceCZ'].get('l', '0'))
                        ttk.Spinbox(frm_table, from_=0, to=999, width=3, textvariable=CZSpaceLVar).grid(row=x + header_rows, column=col, sticky=tk.N, padx=2, pady=2); col += 1
                        CZSpaceMVar = tk.StringVar(value=faction['SpaceCZ'].get('m', '0'))
                        ttk.Spinbox(frm_table, from_=0, to=999, width=3, textvariable=CZSpaceMVar).grid(row=x + header_rows, column=col, sticky=tk.N, padx=2, pady=2); col += 1
                        CZSpaceHVar = tk.StringVar(value=faction['SpaceCZ'].get('h', '0'))
                        ttk.Spinbox(frm_table, from_=0, to=999, width=3, textvariable=CZSpaceHVar).grid(row=x + header_rows, column=col, sticky=tk.N, padx=2, pady=2); col += 1
                        CZGroundLVar = tk.StringVar(value=faction['GroundCZ'].get('l', '0'))
                        ttk.Spinbox(frm_table, from_=0, to=999, width=3, textvariable=CZGroundLVar).grid(row=x + header_rows, column=col, sticky=tk.N, padx=2, pady=2); col += 1
                        CZGroundMVar = tk.StringVar(value=faction['GroundCZ'].get('m', '0'))
                        ttk.Spinbox(frm_table, from_=0, to=999, width=3, textvariable=CZGroundMVar).grid(row=x + header_rows, column=col, sticky=tk.N, padx=2, pady=2); col += 1
                        CZGroundHVar = tk.StringVar(value=faction['GroundCZ'].get('h', '0'))
                        ttk.Spinbox(frm_table, from_=0, to=999, width=3, textvariable=CZGroundHVar).grid(row=x + header_rows, column=col, sticky=tk.N, padx=2, pady=2); col += 1
                        # Watch for changes on all SpinBox Variables. This approach catches any change, including manual editing, while using 'command' callbacks only catches clicks
                        CZSpaceLVar.trace('w', partial(self._cz_change, nb_tab, tab_index, CZSpaceLVar, chk_enable_all, txt_discord, CZs.SPACE_LOW, activity, system, faction, x))
                        CZSpaceMVar.trace('w', partial(self._cz_change, nb_tab, tab_index, CZSpaceMVar, chk_enable_all, txt_discord, CZs.SPACE_MED, activity, system, faction, x))
                        CZSpaceHVar.trace('w', partial(self._cz_change, nb_tab, tab_index, CZSpaceHVar, chk_enable_all, txt_discord, CZs.SPACE_HIGH, activity, system, faction, x))
                        CZGroundLVar.trace('w', partial(self._cz_change, nb_tab, tab_index, CZGroundLVar, chk_enable_all, txt_discord, CZs.GROUND_LOW, activity, system, faction, x))
                        CZGroundMVar.trace('w', partial(self._cz_change, nb_tab, tab_index, CZGroundMVar, chk_enable_all, txt_discord, CZs.GROUND_MED, activity, system, faction, x))
                        CZGroundHVar.trace('w', partial(self._cz_change, nb_tab, tab_index, CZGroundHVar, chk_enable_all, txt_discord, CZs.GROUND_HIGH, activity, system, faction, x))

                    x += 1

                self._update_enable_all_factions_checkbutton(nb_tab, tab_index, chk_enable_all, FactionEnableCheckbuttons, system)

            tab_index += 1

        self._update_discord_field(txt_discord, activity)

        # Ignore all scroll wheel events on spinboxes, to avoid accidental inputs
        self.toplevel.bind_class('TSpinbox', '<MouseWheel>', lambda event : "break")

        self._store_window_geometry()


    def _window_closed(self):
        """
        Callback for when user closes the window
        """
        self._store_window_geometry()
        self.toplevel.destroy()


    def _store_window_geometry(self):
        """
        Save the current window position and dimensions
        """
        if not self.toplevel: return

        self.window_geometry = {
            'x': self.toplevel.winfo_x(),
            'y': self.toplevel.winfo_y(),
            'w': self.toplevel.winfo_width(),
            'h': self.toplevel.winfo_height()}


    def _show_legend_window(self, event):
        """
        Display a mini-window showing a legend of all icons used
        """
        self.bgstally.ui.show_legend_window()


    def _discord_button_available(self) -> bool:
        """
        Return true if the 'Post to Discord' button should be available
        """
        return self.bgstally.discord.valid_webhook_available(DiscordChannel.BGS) or self.bgstally.discord.valid_webhook_available(DiscordChannel.THARGOIDWAR)


    def _update_discord_field(self, DiscordText, activity: Activity):
        """
        Update the contents of the Discord text field
        """
        DiscordText.configure(state=tk.NORMAL)
        DiscordText.delete('1.0', 'end-1c')
        DiscordText.write(activity.generate_text(DiscordActivity.BOTH, True))
        DiscordText.configure(state=tk.DISABLED)


    def _activity_type_selected(self, activity_options: dict, value: str):
        """The user has changed the dropdown to choose the activity type to post
        """
        k: str = next(k for k, v in activity_options.items() if v == value)
        self.bgstally.state.DiscordActivity.set(k)


    def _post_to_discord(self, activity: Activity):
        """
        Callback to post to discord in the appropriate channel(s)
        """
        self.btn_post_to_discord.config(state=tk.DISABLED)

        if self.bgstally.state.DiscordPostStyle.get() == DiscordPostStyle.TEXT:
            if self.bgstally.state.DiscordActivity.get() != DiscordActivity.THARGOIDWAR:
                discord_text:str = activity.generate_text(DiscordActivity.BGS, True)
                self.bgstally.discord.post_plaintext(discord_text, activity.discord_webhook_data, DiscordChannel.BGS, self.discord_post_complete)
            if self.bgstally.state.DiscordActivity.get() != DiscordActivity.BGS:
                discord_text = activity.generate_text(DiscordActivity.THARGOIDWAR, True)
                self.bgstally.discord.post_plaintext(discord_text, activity.discord_webhook_data, DiscordChannel.THARGOIDWAR, self.discord_post_complete)
        else:
            description = "" if activity.discord_notes is None else activity.discord_notes
            if self.bgstally.state.DiscordActivity.get() != DiscordActivity.THARGOIDWAR:
                discord_fields:dict = activity.generate_discord_embed_fields(DiscordActivity.BGS)
                self.bgstally.discord.post_embed(__("BGS Activity after Tick: {tick_time}").format(tick_time=activity.get_title(True)), description, discord_fields, activity.discord_webhook_data, DiscordChannel.BGS, self.discord_post_complete) # LANG: Discord post title
            if self.bgstally.state.DiscordActivity.get() != DiscordActivity.BGS:
                discord_fields = activity.generate_discord_embed_fields(DiscordActivity.THARGOIDWAR)
                self.bgstally.discord.post_embed(__("TW Activity after Tick: {tick_time}").format(tick_time=activity.get_title(True)), description, discord_fields, activity.discord_webhook_data, DiscordChannel.THARGOIDWAR, self.discord_post_complete) # LANG: Discord post title

        activity.dirty = True # Because discord post ID has been changed

        self.btn_post_to_discord.after(5000, self._enable_post_button)


    def _enable_post_button(self):
        """
        Re-enable the post to discord button if it should be enabled
        """
        self.btn_post_to_discord.config(state=(tk.NORMAL if self._discord_button_available() else tk.DISABLED))


    def discord_post_complete(self, channel:DiscordChannel, webhook_data:dict, messageid:str):
        """
        A discord post request has completed
        """
        uuid:str = webhook_data.get('uuid')
        if uuid is None: return

        activity_webhook_data:dict = self.activity.discord_webhook_data.get(uuid, webhook_data) # Fetch current activity webhook data, default to data from callback.
        activity_webhook_data[channel] = messageid                                              # Store the returned messageid against the channel
        self.activity.discord_webhook_data[uuid] = activity_webhook_data                        # Store the webhook dict back to the activity


    def _pin_overlay_change(self, chk_pin_to_overlay:ttk.Checkbutton, system:dict):
        """
        The 'pin to overlay' checkbox has been changed, store state

        Args:
            chk_pin_to_overlay (ttk.Checkbutton): The pin to overlay CheckButton
            system (dict): The system state dict
        """
        system['PinToOverlay'] = CheckStates.STATE_ON if chk_pin_to_overlay.instate(['selected']) else CheckStates.STATE_OFF


    def _discord_notes_change(self, DiscordNotesText, DiscordText, activity: Activity, *args):
        """
        Callback when the user edits the Discord notes field
        """
        activity.discord_notes = DiscordNotesText.get("1.0", "end-1c")
        self._update_discord_field(DiscordText, activity)
        DiscordNotesText.edit_modified(False) # Ensures the <<Modified>> event is triggered next edit
        activity.dirty = True


    def _option_change(self, DiscordText, activity: Activity):
        """
        Callback when one of the Discord options is changed
        """
        self.bgstally.state.refresh()
        self.btn_post_to_discord.config(state=(tk.NORMAL if self._discord_button_available() else tk.DISABLED))
        self._update_discord_field(DiscordText, activity)


    def _enable_faction_change(self, notebook: ScrollableNotebook, tab_index: int, EnableAllCheckbutton, FactionEnableCheckbuttons, DiscordText, activity: Activity, system, faction, faction_index, *args):
        """
        Callback for when a Faction Enable Checkbutton is changed
        """
        faction['Enabled'] = CheckStates.STATE_ON if FactionEnableCheckbuttons[faction_index].instate(['selected']) else CheckStates.STATE_OFF
        self._update_enable_all_factions_checkbutton(notebook, tab_index, EnableAllCheckbutton, FactionEnableCheckbuttons, system)
        self._update_discord_field(DiscordText, activity)
        activity.dirty = True


    def _enable_all_factions_change(self, notebook: ScrollableNotebook, tab_index: int, EnableAllCheckbutton, FactionEnableCheckbuttons, DiscordText, activity: Activity, system, *args):
        """
        Callback for when the Enable All Factions Checkbutton is changed
        """
        x = 0
        for faction in system['Factions'].values():
            if EnableAllCheckbutton.instate(['selected']):
                try:
                    FactionEnableCheckbuttons[x].state(['selected'])
                except:
                    # Will happen if we're hiding BGS checkboxes in a TW system
                    pass
                faction['Enabled'] = CheckStates.STATE_ON
            else:
                try:
                    FactionEnableCheckbuttons[x].state(['!selected'])
                except:
                    # Will happen if we're hiding BGS checkboxes in a TW system
                    pass
                faction['Enabled'] = CheckStates.STATE_OFF
            x += 1

        self._update_tab_image(notebook, tab_index, EnableAllCheckbutton, system)
        self._update_discord_field(DiscordText, activity)
        activity.dirty = True


    def _enable_settlement_change(self, SettlementCheckbutton, settlement_name, DiscordText, activity: Activity, faction, faction_index, *args):
        """
        Callback for when a Settlement Enable Checkbutton is changed
        """
        faction['GroundCZSettlements'][settlement_name]['enabled'] = CheckStates.STATE_ON if SettlementCheckbutton.instate(['selected']) else CheckStates.STATE_OFF
        self._update_discord_field(DiscordText, activity)
        activity.dirty = True


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
        activity.dirty = True


    def _mission_points_change(self, notebook: ScrollableNotebook, tab_index: int, MissionPointsVar, primary, EnableAllCheckbutton, DiscordText, activity: Activity, system, faction, faction_index, *args):
        """
        Callback (set as a variable trace) for when a mission points Variable is changed
        """
        if primary:
            faction['MissionPoints']['m'] = MissionPointsVar.get()
        else:
            faction['MissionPointsSecondary']['m'] = MissionPointsVar.get()

        activity.recalculate_zero_activity()
        self._update_tab_image(notebook, tab_index, EnableAllCheckbutton, system)
        self._update_discord_field(DiscordText, activity)
        activity.dirty = True


    def _scenarios_change(self, notebook: ScrollableNotebook, tab_index: int, ScenariosVar, EnableAllCheckbutton, DiscordText, activity: Activity, system, faction, faction_index, *args):
        """
        Callback (set as a variable trace) for when the scenarios Variable is changed
        """
        faction['Scenarios'] = ScenariosVar.get()

        activity.recalculate_zero_activity()
        self._update_tab_image(notebook, tab_index, EnableAllCheckbutton, system)
        self._update_discord_field(DiscordText, activity)
        activity.dirty = True


    def _update_tab_image(self, notebook: ScrollableNotebook, tab_index: int, EnableAllCheckbutton, system: dict):
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


    def _copy_to_clipboard(self, Form:tk.Frame, activity:Activity):
        """
        Get all text from the Discord field and put it in the Copy buffer
        """
        Form.clipboard_clear()
        Form.clipboard_append(activity.generate_text(DiscordActivity.BOTH, True))
        Form.update()

