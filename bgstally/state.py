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
        self.DiscordFCWebhook:tk.StringVar = tk.StringVar(value=config.get_str("XDiscordFCWebhook", default=""))
        self.DiscordTWWebhook:tk.StringVar = tk.StringVar(value=config.get_str("XDiscordTWWebhook", default=""))
        self.DiscordUsername:tk.StringVar = tk.StringVar(value=config.get_str('XDiscordUsername', default=""))
        self.DiscordPostStyle:tk.StringVar = tk.StringVar(value=config.get_str('XDiscordPostStyle', default=DiscordPostStyle.EMBED))
        self.DiscordActivity:tk.StringVar = tk.StringVar(value=config.get_str('XDiscordActivity', default=DiscordActivity.BOTH))
        self.EnableOverlay:tk.StringVar = tk.StringVar(value=config.get_str('XEnableOverlay', default=CheckStates.STATE_ON))

        self.APIActivitiesURL:tk.StringVar = tk.StringVar(value=config.get_str('BGST_APIActivitiesURL', default=""))
        self.APIActivitiesKey:tk.StringVar = tk.StringVar(value=config.get_str('BGST_APIActivitiesKey', default=""))
        self.APIEventsURL:tk.StringVar = tk.StringVar(value=config.get_str('BGST_APIEventsURL', default=""))
        self.APIEventsKey:tk.StringVar = tk.StringVar(value=config.get_str('BGST_APIEventsKey', default=""))

        # Persistent values
        self.current_system_id:str = config.get_str('XCurrentSystemID')
        self.station_faction:str = config.get_str('XStationFaction')
        self.station_type:str = config.get_str('XStationType')

        # Non-persistent values
        self.last_settlement_approached:Dict = {}
        self.last_ship_targeted:Dict = {}

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
        config.set('XDiscordFCWebhook', self.DiscordFCWebhook.get())
        config.set('XDiscordTWWebhook', self.DiscordTWWebhook.get())
        config.set('XDiscordUsername', self.DiscordUsername.get())
        config.set('XDiscordPostStyle', self.DiscordPostStyle.get())
        config.set('XDiscordActivity', self.DiscordActivity.get())
        config.set('XEnableOverlay', self.EnableOverlay.get())

        config.set('BGST_APIActivitiesURL', self.APIActivitiesURL.get())
        config.set('BGST_APIActivitiesKey', self.APIActivitiesKey.get())
        config.set('BGST_APIEventsURL', self.APIEventsURL.get())
        config.set('BGST_APIEventsKey', self.APIEventsKey.get())

        # Persistent values
        config.set('XCurrentSystemID', self.current_system_id if self.current_system_id != None else "")
        config.set('XStationFaction', self.station_faction if self.station_faction != None else "")
        config.set('XStationType', self.station_type if self.station_type != None else "")
