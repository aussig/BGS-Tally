from os import mkdir, path
from threading import Thread
from time import sleep
from typing import Optional

import plug
import requests
import semantic_version
from companion import CAPIData, SERVER_LIVE
from config import appversion, config
from monitor import monitor

from bgstally.activity import Activity
from bgstally.activitymanager import ActivityManager
from bgstally.config import Config
from bgstally.constants import FOLDER_DATA, UpdateUIPolicy
from bgstally.debug import Debug
from bgstally.discord import Discord
from bgstally.fleetcarrier import FleetCarrier
from bgstally.missionlog import MissionLog
from bgstally.overlay import Overlay
from bgstally.state import State
from bgstally.targetlog import TargetLog
from bgstally.tick import Tick
from bgstally.ui import UI

TIME_WORKER_PERIOD_S = 60
URL_PLUGIN_VERSION = "https://api.github.com/repos/aussig/BGS-Tally/releases/latest"


class BGSTally:
    """
    Main plugin class
    """
    def __init__(self, plugin_name: str, version: semantic_version.Version):
        self.plugin_name:str = plugin_name
        self.version: semantic_version.Version = version
        self.git_version: semantic_version.Version = semantic_version.Version.coerce("0")


    def plugin_start(self, plugin_dir: str):
        """
        The plugin is starting up. Initialise all our objects.
        """
        self.plugin_dir = plugin_dir

        data_filepath = path.join(self.plugin_dir, FOLDER_DATA)
        if not path.exists(data_filepath): mkdir(data_filepath)

        # Classes
        self.debug: Debug = Debug(self)
        self.config: Config = Config(self)
        self.state: State = State(self)
        self.mission_log: MissionLog = MissionLog(self)
        self.target_log: TargetLog = TargetLog(self)
        self.discord: Discord = Discord(self)
        self.tick: Tick = Tick(self, True)
        self.overlay = Overlay(self)
        self.activity_manager: ActivityManager = ActivityManager(self)
        self.fleet_carrier = FleetCarrier(self)
        self.ui: UI = UI(self)

        self.thread: Thread = Thread(target=self._worker, name="BGSTally Main worker")
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

        # Live galaxy check
        try:
            if not monitor.is_live_galaxy(): return
        except Exception as e:
            self.debug.logger.error(f"The EDMC Version is too old, please upgrade to v5.6.0 or later", exc_info=e)
            return

        activity: Activity = self.activity_manager.get_current_activity()
        dirty: bool = False

        if entry.get('event') in ['Location', 'FSDJump', 'CarrierJump']:
            if self.check_tick(UpdateUIPolicy.IMMEDIATE):
                # New activity will be generated with a new tick
                activity = self.activity_manager.get_current_activity()

            activity.system_entered(entry, self.state)
            dirty = True

        match entry.get('event'):
            case 'Docked':
                self.state.station_faction = entry['StationFaction']['Name']
                self.state.station_type = entry['StationType']
                dirty = True

            case 'Location' | 'StartUp' if entry.get('Docked') == True:
                self.state.station_type = entry['StationType']
                dirty = True

            case 'SellExplorationData' | 'MultiSellExplorationData':
                activity.exploration_data_sold(entry, self.state)
                dirty = True

            case 'SellOrganicData':
                activity.organic_data_sold(entry, self.state)
                dirty = True

            case 'RedeemVoucher' if entry.get('Type') == 'bounty':
                activity.bv_redeemed(entry, self.state)
                dirty = True

            case 'RedeemVoucher' if entry.get('Type') == 'CombatBond':
                activity.cb_redeemed(entry, self.state)
                dirty = True

            case 'MarketBuy':
                activity.trade_purchased(entry, self.state)
                dirty = True

            case 'MarketSell':
                activity.trade_sold(entry, self.state)
                dirty = True

            case 'MissionAccepted':
                self.mission_log.add_mission(entry.get('Name', ""), entry.get('Faction', ""), entry.get('MissionID', ""), entry.get('Expiry', ""), system, station,
                    entry.get('Count', -1), entry.get('PassengerCount', -1), entry.get('KillCount', -1))
                dirty = True

            case 'MissionAbandoned':
                self.mission_log.delete_mission_by_id(entry.get('MissionID'))
                dirty = True

            case 'MissionFailed':
                activity.mission_failed(entry, self.mission_log)
                dirty = True

            case 'MissionCompleted':
                activity.mission_completed(entry, self.mission_log)
                dirty = True

            case 'ShipTargeted':
                activity.ship_targeted(entry, self.state)
                self.target_log.ship_targeted(entry, system)
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


    def capi_fleetcarrier(self, data: CAPIData):
        """
        Fleet carrier data received from CAPI
        """
        if data.data == {} or data.get('name') is None or data['name'].get('callsign') is None:
            raise ValueError("Invalid /fleetcarrier CAPI data")

        if data.source_host != SERVER_LIVE:
            return

        self.fleet_carrier.update(data.data)
        self.ui.update_plugin_frame()


    def capi_fleetcarrier_available(self) -> bool:
        """
        Return true if the EDMC version is high enough to provide a callback for /fleetcarrier CAPI
        """
        return callable(appversion) and appversion() >= semantic_version.Version('5.8.0')


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
            self.git_version = semantic_version.Version.coerce(latest['tag_name'])

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
        self.target_log.save()
        self.tick.save()
        self.activity_manager.save()
        self.state.save()
        self.fleet_carrier.save()


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
