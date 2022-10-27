from threading import Thread
from time import sleep
from typing import Optional

import plug
import requests
from config import config

from bgstally import Activity
from bgstally import ActivityManager
from bgstally import Debug
from bgstally import Discord
from bgstally import UpdateUIPolicy
from bgstally import MissionLog
from bgstally import Overlay
from bgstally import State
from bgstally import Tick
from bgstally import UI

URL_PLUGIN_VERSION = "https://api.github.com/repos/aussig/BGS-Tally/releases/latest"
TIME_WORKER_PERIOD_S = 60


class BGSTally:
    """
    Main plugin class
    """
    def __init__(self, plugin_name: str, version:str):
        self.plugin_name:str = plugin_name
        self.version:str = version
        self.git_version:str = "0.0.0"


    def plugin_start(self, plugin_dir: str):
        """
        The plugin is starting up. Initialise all our objects.
        """
        self.plugin_dir = plugin_dir

        # Classes
        self.debug: Debug = Debug(self)
        self.state: State = State(self)
        self.mission_log: MissionLog = MissionLog(self)
        self.discord: Discord = Discord(self)
        self.tick: Tick = Tick(self, True)
        self.overlay = Overlay(self)
        self.activity_manager: ActivityManager = ActivityManager(self)
        self.ui: UI = UI(self)

        self.thread: Optional[Thread] = Thread(target=self._worker, name="BGSTally Main worker")
        self.thread.daemon = True
        self.thread.start()


    def plugin_stop(self):
        """
        The plugin is shutting down.
        """
        self.ui.shut_down()
        self.save_data()


    def journal_entry(self, cmdr, is_beta, system, station, entry, state):
        """
        Parse an incoming journal entry and store the data we need
        """
        activity: Activity = self.activity_manager.get_current_activity()
        dirty: bool = False

        if entry['event'] in ['Location', 'FSDJump', 'CarrierJump']:
            if self.check_tick(UpdateUIPolicy.IMMEDIATE):
                # New activity will be generated with a new tick
                activity = self.activity_manager.get_current_activity()

            activity.system_entered(entry, self.state)
            dirty = True

        match entry['event']:
            case 'Docked':
                self.state.station_faction = entry['StationFaction']['Name']
                self.state.station_type = entry['StationType']
                dirty = True

            case 'Location' | 'StartUp' if entry['Docked'] == True:
                self.state.station_type = entry['StationType']
                dirty = True

            case 'SellExplorationData' | 'MultiSellExplorationData':
                activity.exploration_data_sold(entry, self.state)
                dirty = True

            case 'SellOrganicData':
                activity.organic_data_sold(entry, self.state)
                dirty = True

            case 'RedeemVoucher' if entry['Type'] == 'bounty':
                activity.bv_redeemed(entry, self.state)
                dirty = True

            case 'RedeemVoucher' if entry['Type'] == 'CombatBond':
                activity.cb_redeemed(entry, self.state)
                dirty = True

            case 'MarketBuy':
                activity.trade_purchased(entry, self.state)
                dirty = True

            case 'MarketSell':
                activity.trade_sold(entry, self.state)
                dirty = True

            case 'MissionAccepted':
                self.mission_log.add_mission(entry['Name'], entry['Faction'], entry['MissionID'], entry['Expiry'], system)
                dirty = True

            case 'MissionAbandoned':
                self.mission_log.delete_mission_by_id(entry['MissionID'])
                dirty = True

            case 'MissionFailed':
                activity.mission_failed(entry, self.mission_log)
                dirty = True

            case 'MissionCompleted':
                activity.mission_completed(entry, self.mission_log)
                dirty = True

            case 'ShipTargeted':
                activity.ship_targeted(entry, self.state)
                dirty = True

            case 'CommitCrime':
                activity.crime_committed(entry, self.state)
                dirty = True

            case 'ApproachSettlement' if state['Odyssey']:
                activity.settlement_approached(entry, self.state)
                dirty = True

            case 'FactionKillBond' if state['Odyssey']:
                activity.cb_received(entry, self.state)
                dirty = True

        if dirty: self.save_data()


    def check_version(self):
        """
        Check for a new plugin version
        """
        try:
            response = requests.get(URL_PLUGIN_VERSION, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.debug.logger.warning(f"Unable to fetch latest plugin version", exc_info=e)
            plug.show_error(f"BGS-Tally: Unable to fetch latest plugin version")
            return None
        else:
            latest = response.json()
            self.git_version = latest['tag_name']

        return True


    def check_tick(self, uipolicy: UpdateUIPolicy):
        """
        Check for a new tick
        """
        tick_success = self.tick.fetch_tick()

        if tick_success:
            self.new_tick(False, uipolicy)
            return True
        else:
            return tick_success


    def save_data(self):
        """
        Save all data structures
        """
        self.mission_log.save()
        self.tick.save()
        self.activity_manager.save()
        self.state.save()


    def new_tick(self, force: bool, uipolicy: UpdateUIPolicy):
        """
        Start a new tick.
        """
        if force: self.tick.force_tick()
        self.activity_manager.new_tick(self.tick)

        match uipolicy:
            case UpdateUIPolicy.IMMEDIATE:
                self.ui.update_plugin_frame()
            case UpdateUIPolicy.LATER:
                self.ui.frame.after(1000, self.ui.update_plugin_frame())

        self.overlay.display_message("tickwarn", f"NEW TICK DETECTED!", True, 180, "green")


    def _worker(self) -> None:
        """
        Handle thread work
        """
        Debug.logger.debug("Starting Main Worker...")

        while True:
            if config.shutting_down:
                Debug.logger.debug("Shutting down Main Worker...")
                return

            sleep(TIME_WORKER_PERIOD_S)

            self.check_tick(UpdateUIPolicy.LATER) # Must not update UI directly from a thread
