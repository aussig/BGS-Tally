import tkinter as tk
from typing import Dict

from config import config

from bgstally.constants import CheckStates, DiscordActivity, DiscordPostStyle


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
        self.Status:tk.StringVar = tk.StringVar(value=config.get_str('XStatus', default="Active"))
        self.ShowZeroActivitySystems:tk.StringVar = tk.StringVar(value=config.get_str('XShowZeroActivity', default=CheckStates.STATE_ON))
        self.AbbreviateFactionNames:tk.StringVar = tk.StringVar(value=config.get_str('XAbbreviate', default=CheckStates.STATE_OFF))
        self.IncludeSecondaryInf:tk.StringVar = tk.StringVar(value=config.get_str('XSecondaryInf', default=CheckStates.STATE_ON))
        self.DiscordBGSWebhook:tk.StringVar = tk.StringVar(value=config.get_str('XDiscordWebhook', default=""))
        self.DiscordCMDRInformationWebhook:tk.StringVar = tk.StringVar(value=config.get_str("BGST_DiscordCMDRInformationWebhook", default=""))
        self.DiscordFCMaterialsWebhook:tk.StringVar = tk.StringVar(value=config.get_str("BGST_DiscordFCMaterialsWebhook", default=""))
        self.DiscordFCOperationsWebhook:tk.StringVar = tk.StringVar(value=config.get_str("BGST_DiscordFCOperationsWebhook", default=""))
        self.DiscordTWWebhook:tk.StringVar = tk.StringVar(value=config.get_str("XDiscordTWWebhook", default=""))
        self.DiscordUsername:tk.StringVar = tk.StringVar(value=config.get_str('XDiscordUsername', default=""))
        self.DiscordPostStyle:tk.StringVar = tk.StringVar(value=config.get_str('XDiscordPostStyle', default=DiscordPostStyle.EMBED))
        self.DiscordActivity:tk.StringVar = tk.StringVar(value=config.get_str('XDiscordActivity', default=DiscordActivity.BOTH))
        self.EnableOverlay:tk.StringVar = tk.StringVar(value=config.get_str('XEnableOverlay', default=CheckStates.STATE_ON))
        self.EnableOverlayCurrentTick:tk.StringVar = tk.StringVar(value=config.get_str('XEnableOverlayCurrentTick', default=CheckStates.STATE_ON))
        self.EnableSystemActivityByDefault:tk.StringVar = tk.StringVar(value=config.get_str('BGST_EnableSystemActivityByDefault', default=CheckStates.STATE_ON))

        # Persistent values
        self.current_system_id:str = config.get_str('XCurrentSystemID', default="")
        self.station_faction:str = config.get_str('XStationFaction', default = "")
        self.station_type:str = config.get_str('XStationType', default ="")

        # Non-persistent values
        self.last_settlement_approached:Dict = {}
        self.last_spacecz_approached:Dict = {}
        self.last_ships_targeted:Dict = {}
        self.system_tw_status = None

        self.refresh()


    def refresh(self):
        """
        Update all our mirror thread-safe values from their tk equivalents
        """
        self.enable_overlay:bool = (self.EnableOverlay.get() == CheckStates.STATE_ON)

    def save(self):
        """
        Save our state
        """

        # UI preference fields
        config.set('XStatus', self.Status.get())
        config.set('XShowZeroActivity', self.ShowZeroActivitySystems.get())
        config.set('XAbbreviate', self.AbbreviateFactionNames.get())
        config.set('XSecondaryInf', self.IncludeSecondaryInf.get())
        config.set('XDiscordWebhook', self.DiscordBGSWebhook.get())
        config.set('BGST_DiscordCMDRInformationWebhook', self.DiscordCMDRInformationWebhook.get())
        config.set('BGST_DiscordFCMaterialsWebhook', self.DiscordFCMaterialsWebhook.get())
        config.set('BGST_DiscordFCOperationsWebhook', self.DiscordFCOperationsWebhook.get())
        config.set('XDiscordTWWebhook', self.DiscordTWWebhook.get())
        config.set('XDiscordUsername', self.DiscordUsername.get())
        config.set('XDiscordPostStyle', self.DiscordPostStyle.get())
        config.set('XDiscordActivity', self.DiscordActivity.get())
        config.set('XEnableOverlay', self.EnableOverlay.get())
        config.set('XEnableOverlayCurrentTick', self.EnableOverlayCurrentTick.get())
        config.set('BGST_EnableSystemActivityByDefault', self.EnableSystemActivityByDefault.get())

        # Persistent values
        config.set('XCurrentSystemID', self.current_system_id if self.current_system_id != None else "")
        config.set('XStationFaction', self.station_faction if self.station_faction != None else "")
        config.set('XStationType', self.station_type if self.station_type != None else "")
        config.set('XStationType', self.station_type if self.station_type != None else "")
