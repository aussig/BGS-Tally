import tkinter as tk

from bgstally.constants import CheckStates, DiscordActivity
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
        self.EnableOverlayCurrentTick:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlayCurrentTick', default=CheckStates.STATE_ON))
        self.EnableOverlayActivity:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlayActivity', default=CheckStates.STATE_ON))
        self.EnableOverlayTWProgress:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlayTWProgress', default=CheckStates.STATE_ON))
        self.EnableOverlaySystem:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlaySystem', default=CheckStates.STATE_ON))
        self.EnableOverlayWarning:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlayWarning', default=CheckStates.STATE_ON))
        self.EnableOverlayCMDR:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlayCMDR', default=CheckStates.STATE_ON))
        self.EnableOverlayObjectives:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlayObjectives', default=CheckStates.STATE_ON))
        self.EnableOverlayColonisation:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlayColonisation', default=CheckStates.STATE_ON))
        self.EnableSystemActivityByDefault:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableSystemActivityByDefault', default=CheckStates.STATE_ON))
        self.EnableShowMerits:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableShowMerits', default=CheckStates.STATE_ON))
        self.DetailedInf:tk.StringVar = tk.StringVar(value=config.get_str('BGST_DetailedInf', default=CheckStates.STATE_OFF))
        self.DetailedTrade:tk.StringVar = tk.StringVar(value=config.get_str('BGST_DetailedTrade', default=CheckStates.STATE_ON))
        self.DiscordActivity:tk.StringVar = tk.StringVar(value=config.get_str('BGST_DiscordActivity', default=DiscordActivity.BOTH))
        self.DiscordAvatarURL:tk.StringVar = tk.StringVar(value=config.get_str('BGST_DiscordAvatarURL', default=""))
        self.DiscordBGSTWAutomatic:tk.StringVar = tk.StringVar(value=config.get_str('BGST_DiscordBGSTWAutomatic', default=CheckStates.STATE_OFF))

        self.ColonisationMaxCommodities:tk.StringVar = tk.StringVar(value=config.get_str('BGST_ColonisationMaxCommodities', default="20"))
        self.ColonisationRCAPIKey:tk.StringVar = tk.StringVar(value=config.get_str('BGST_ColonisationRCAPIKey', default=""))

        self.FcSellingCommodities:tk.StringVar = tk.StringVar(value=config.get_str('BGST_FcSellingCommodities', default=CheckStates.STATE_ON))
        self.FcBuyingCommodities:tk.StringVar = tk.StringVar(value=config.get_str('BGST_FcBuyingCommodities', default=CheckStates.STATE_ON))
        self.FcSellingMaterials:tk.StringVar = tk.StringVar(value=config.get_str('BGST_FcSellingMaterials', default=CheckStates.STATE_ON))
        self.FcBuyingMaterials:tk.StringVar = tk.StringVar(value=config.get_str('BGST_FcBuyingMaterials', default=CheckStates.STATE_ON))
        self.FcCargo:tk.StringVar = tk.StringVar(value=config.get_str('BGST_FcCargo', default=CheckStates.STATE_ON))
        self.FcLocker:tk.StringVar = tk.StringVar(value=config.get_str('BGST_FcLocker', default=CheckStates.STATE_ON))

        # Legacy values migrating to new names
        # TODO: Remove migration in future version
        self.ShowZeroActivitySystems:tk.StringVar = tk.StringVar(value=config.get_str('BGST_ShowZeroActivity', default=config.get_str('XShowZeroActivity', default=CheckStates.STATE_ON)))
        self.AbbreviateFactionNames:tk.StringVar = tk.StringVar(value=config.get_str('BGST_AbbreviateFactions', default=config.get_str('XAbbreviate', default=CheckStates.STATE_OFF)))
        self.IncludeSecondaryInf:tk.StringVar = tk.StringVar(value=config.get_str('BGST_SecondaryInf', default=config.get_str('XSecondaryInf', default=CheckStates.STATE_ON)))
        self.DiscordUsername:tk.StringVar = tk.StringVar(value=config.get_str('BGST_DiscordUsername', default=config.get_str('XDiscordUsername', default="")))
        self.EnableOverlay:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableOverlay', default=config.get_str('XEnableOverlay', default=CheckStates.STATE_ON)))
        self.current_system_id:str = config.get_str('BGST_CurrentSystemID', default=config.get_str('XCurrentSystemID', default=""))
        self.station_faction:str = config.get_str('BGST_StationFaction', default=config.get_str('XStationFaction', default = ""))
        self.station_type:str = config.get_str('BGST_StationType', default=config.get_str('XStationType', default =""))

        # TODO: Remove deletion in future version
        config.delete('XShowZeroActivity', suppress=True)  # Remove legacy config keys
        config.delete('XAbbreviate', suppress=True) # Remove legacy config keys
        config.delete('XSecondaryInf', suppress=True)  # Remove legacy config keys
        config.delete('XDiscordUsername', suppress=True)  # Remove legacy config keys
        config.delete('XEnableOverlay', suppress=True)  # Remove legacy config keys
        config.delete('XCurrentSystemID', suppress=True)  # Remove legacy config keys
        config.delete('XStationFaction', suppress=True)  # Remove legacy config keys
        config.delete('XStationType', suppress=True)  # Remove legacy config keys
        config.delete('XStatus', suppress=True)  # Remove legacy config keys
        config.delete('XDiscordPostStyle', suppress=True)  # Remove legacy config keys

        # Persistent values
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
        self.enable_overlay_objectives:bool = (self.EnableOverlayObjectives.get() == CheckStates.STATE_ON)
        self.enable_overlay_colonisation:bool = (self.EnableOverlayColonisation.get() == CheckStates.STATE_ON)

        self.buying_commodities:bool = (self.FcBuyingCommodities.get() == CheckStates.STATE_ON)
        self.selling_commodities:bool = (self.FcSellingCommodities.get() == CheckStates.STATE_ON)
        self.buying_materials:bool = (self.FcBuyingMaterials.get() == CheckStates.STATE_ON)
        self.selling_materials:bool = (self.FcSellingMaterials.get() == CheckStates.STATE_ON)
        self.cargo:bool = (self.FcCargo.get() == CheckStates.STATE_ON)
        self.locker:bool = (self.FcLocker.get() == CheckStates.STATE_ON)

        self.abbreviate_faction_names:bool = (self.AbbreviateFactionNames.get() == CheckStates.STATE_ON)
        self.secondary_inf:bool = (self.IncludeSecondaryInf.get() == CheckStates.STATE_ON)
        self.detailed_inf:bool = (self.DetailedInf.get() == CheckStates.STATE_ON)
        self.detailed_trade:bool = (self.DetailedTrade.get() == CheckStates.STATE_ON)
        self.discord_bgstw_automatic:bool = (self.DiscordBGSTWAutomatic.get() == CheckStates.STATE_ON)
        self.showmerits:bool = (self.EnableShowMerits.get() == CheckStates.STATE_ON)


    def save(self):
        """
        Save our state
        """

        # UI preference fields
        config.set('BGST_Status', self.Status.get())
        config.set('BGST_ShowZeroActivity', self.ShowZeroActivitySystems.get())
        config.set('BGST_AbbreviateFactions', self.AbbreviateFactionNames.get())
        config.set('BGST_SecondaryInf', self.IncludeSecondaryInf.get())
        config.set('BGST_DiscordUsername', self.DiscordUsername.get())
        config.set('BGST_EnableOverlay', self.EnableOverlay.get())
        config.set('BGST_EnableOverlayCurrentTick', self.EnableOverlayCurrentTick.get())
        config.set('BGST_EnableOverlayActivity', self.EnableOverlayActivity.get())
        config.set('BGST_EnableOverlayTWProgress', self.EnableOverlayTWProgress.get())
        config.set('BGST_EnableOverlaySystem', self.EnableOverlaySystem.get())
        config.set('BGST_EnableOverlayWarning', self.EnableOverlayWarning.get())
        config.set('BGST_EnableOverlayCMDR', self.EnableOverlayCMDR.get())
        config.set('BGST_EnableOverlayObjectives', self.EnableOverlayObjectives.get())
        config.set('BGST_EnableOverlayColonisation', self.EnableOverlayColonisation.get())
        config.set('BGST_EnableSystemActivityByDefault', self.EnableSystemActivityByDefault.get())
        config.set('BGST_EnableShowMerits', self.EnableShowMerits.get())
        config.set('BGST_DetailedInf', self.DetailedInf.get())
        config.set('BGST_DetailedTrade', self.DetailedTrade.get())
        config.set('BGST_DiscordActivity', self.DiscordActivity.get())
        config.set('BGST_DiscordAvatarURL', self.DiscordAvatarURL.get())
        config.set('BGST_DiscordBGSTWAutomatic', self.DiscordBGSTWAutomatic.get())
        config.set('BGST_FcSellingCommodities', self.FcSellingCommodities.get())
        config.set('BGST_FcBuyingCommodities', self.FcBuyingCommodities.get())
        config.set('BGST_FcSellingMaterials', self.FcSellingMaterials.get())
        config.set('BGST_FcBuyingMaterials', self.FcBuyingMaterials.get())
        config.set('BGST_FcCargo', self.FcCargo.get())
        config.set('BGST_FcLocker', self.FcLocker.get())
        config.set('BGST_ColonisationMaxCommodities', self.ColonisationMaxCommodities.get())
        config.set('BGST_ColonisationRCAPIKey', self.ColonisationRCAPIKey.get())

        # Persistent values
        config.set('BGST_CurrentSystemID', self.current_system_id if self.current_system_id != None else "")
        config.set('BGST_StationFaction', self.station_faction if self.station_faction != None else "")
        config.set('BGST_StationType', self.station_type if self.station_type != None else "")
        config.set('BGST_DiscordLang', self.discord_lang if self.discord_lang != None else "")
        config.set('BGST_DiscordFormatter', self.discord_formatter if self.discord_formatter != None else "")
