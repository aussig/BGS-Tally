import tkinter as tk

from bgstally.constants import CheckStates, DiscordActivity, DiscordFleetCarrier
from config import config


class State:
    """
    Manage plugin user state and preferences
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.load()


    def load(self):
        """
        Load our state
        """
        # UI preference fields
        self.Status:tk.StringVar = tk.StringVar(value=config.get_str('BGST_Status', default=CheckStates.STATE_ON))
        self.ShowZeroActivitySystems:tk.StringVar = tk.StringVar(value=config.get_str('XShowZeroActivity', default=CheckStates.STATE_ON))
        self.AbbreviateFactionNames:tk.StringVar = tk.StringVar(value=config.get_str('XAbbreviate', default=CheckStates.STATE_OFF))
        self.IncludeSecondaryInf:tk.StringVar = tk.StringVar(value=config.get_str('XSecondaryInf', default=CheckStates.STATE_ON))
        self.DiscordUsername:tk.StringVar = tk.StringVar(value=config.get_str('XDiscordUsername', default=""))
        self.EnableOverlay:tk.StringVar = tk.StringVar(value=config.get_str('XEnableOverlay', default=CheckStates.STATE_ON))
        self.EnableOverlayCurrentTick:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlayCurrentTick', default=CheckStates.STATE_ON))
        self.EnableOverlayActivity:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlayActivity', default=CheckStates.STATE_ON))
        self.EnableOverlayTWProgress:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlayTWProgress', default=CheckStates.STATE_ON))
        self.EnableOverlaySystem:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlaySystem', default=CheckStates.STATE_ON))
        self.EnableOverlayWarning:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlayWarning', default=CheckStates.STATE_ON))
        self.EnableOverlayCMDR:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlayCMDR', default=CheckStates.STATE_ON))
        self.EnableSystemActivityByDefault:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableSystemActivityByDefault', default=CheckStates.STATE_ON))
        self.DetailedInf:tk.StringVar = tk.StringVar(value=config.get_str('BGST_DetailedInf', default=CheckStates.STATE_OFF))
        self.DetailedTrade:tk.StringVar = tk.StringVar(value=config.get_str('BGST_DetailedTrade', default=CheckStates.STATE_ON))
        self.DiscordActivity:tk.StringVar = tk.StringVar(value=config.get_str('BGST_DiscordActivity', default=DiscordActivity.BOTH))
        self.DiscordFleetCarrier: tk.StringVar = tk.StringVar(value=config.get_str('BGST_DiscordFleetCarrier', default=DiscordFleetCarrier.BOTH))

        # TODO: Legacy values, used to migrate initial state, remove in future version
        self.DiscordBGSWebhook:tk.StringVar = tk.StringVar(value=config.get_str('XDiscordWebhook', default=""))
        self.DiscordCMDRInformationWebhook:tk.StringVar = tk.StringVar(value=config.get_str("BGST_DiscordCMDRInformationWebhook", default=""))
        self.DiscordFCMaterialsWebhook:tk.StringVar = tk.StringVar(value=config.get_str("BGST_DiscordFCMaterialsWebhook", default=""))
        self.DiscordFCOperationsWebhook:tk.StringVar = tk.StringVar(value=config.get_str("BGST_DiscordFCOperationsWebhook", default=""))
        self.DiscordTWWebhook:tk.StringVar = tk.StringVar(value=config.get_str("XDiscordTWWebhook", default=""))

        # Persistent values
        self.current_system_id:str = config.get_str('XCurrentSystemID', default="")
        self.station_faction:str = config.get_str('XStationFaction', default = "")
        self.station_type:str = config.get_str('XStationType', default ="")
        self.discord_lang:str|None = config.get_str('BGST_DiscordLang', default="")
        self.discord_formatter:str|None = config.get_str('BGST_DiscordFormatter', default="")

        # Non-persistent values
        self.last_settlement_approached:dict = {}
        self.last_spacecz_approached:dict = {}
        self.last_megaship_approached:dict = {}
        self.last_ships_targeted:dict = {}
        self.last_ship_targeted:dict = {}

        self.refresh()


    def refresh(self):
        """
        Update all our mirror thread-safe values from their tk equivalents
        """
        self.enable_overlay:bool = (self.EnableOverlay.get() == CheckStates.STATE_ON)
        self.enable_overlay_current_tick:bool = (self.EnableOverlayCurrentTick.get() == CheckStates.STATE_ON)
        self.enable_overlay_activity:bool = (self.EnableOverlayActivity.get() == CheckStates.STATE_ON)
        self.enable_overlay_tw_progress:bool = (self.EnableOverlayTWProgress.get() == CheckStates.STATE_ON)
        self.enable_overlay_system:bool = (self.EnableOverlaySystem.get() == CheckStates.STATE_ON)
        self.enable_overlay_warning:bool = (self.EnableOverlayWarning.get() == CheckStates.STATE_ON)
        self.enable_overlay_cmdr:bool = (self.EnableOverlayCMDR.get() == CheckStates.STATE_ON)

        self.abbreviate_faction_names:bool = (self.AbbreviateFactionNames.get() == CheckStates.STATE_ON)
        self.secondary_inf:bool = (self.IncludeSecondaryInf.get() == CheckStates.STATE_ON)
        self.detailed_inf:bool = (self.DetailedInf.get() == CheckStates.STATE_ON)
        self.detailed_trade:bool = (self.DetailedTrade.get() == CheckStates.STATE_ON)


    def save(self):
        """
        Save our state
        """

        # UI preference fields
        config.set('BGST_Status', self.Status.get())
        config.set('XShowZeroActivity', self.ShowZeroActivitySystems.get())
        config.set('XAbbreviate', self.AbbreviateFactionNames.get())
        config.set('XSecondaryInf', self.IncludeSecondaryInf.get())
        config.set('XDiscordUsername', self.DiscordUsername.get())
        config.set('XEnableOverlay', self.EnableOverlay.get())
        config.set('BGST_EnableOverlayCurrentTick', self.EnableOverlayCurrentTick.get())
        config.set('BGST_EnableOverlayActivity', self.EnableOverlayActivity.get())
        config.set('BGST_EnableOverlayTWProgress', self.EnableOverlayTWProgress.get())
        config.set('BGST_EnableOverlaySystem', self.EnableOverlaySystem.get())
        config.set('BGST_EnableOverlayWarning', self.EnableOverlayWarning.get())
        config.set('BGST_EnableOverlayCMDR', self.EnableOverlayCMDR.get())
        config.set('BGST_EnableSystemActivityByDefault', self.EnableSystemActivityByDefault.get())
        config.set('BGST_DetailedInf', self.DetailedInf.get())
        config.set('BGST_DetailedTrade', self.DetailedTrade.get())
        config.set('BGST_DiscordActivity', self.DiscordActivity.get())
        config.set('BGST_DiscordFleetCarrier', self.DiscordFleetCarrier.get())

        # Persistent values
        config.set('XCurrentSystemID', self.current_system_id if self.current_system_id != None else "")
        config.set('XStationFaction', self.station_faction if self.station_faction != None else "")
        config.set('XStationType', self.station_type if self.station_type != None else "")
        config.set('BGST_DiscordLang', self.discord_lang if self.discord_lang != None else "")
        config.set('BGST_DiscordFormatter', self.discord_formatter if self.discord_formatter != None else "")
