from os import mkdir, path
from threading import Thread
from time import sleep

import semantic_version
from companion import CAPIData, SERVER_LIVE
from config import appversion, config
from monitor import monitor

from bgstally.activity import Activity
from bgstally.activitymanager import ActivityManager
from bgstally.apimanager import APIManager
from bgstally.config import Config
from bgstally.constants import FOLDER_DATA, UpdateUIPolicy
from bgstally.debug import Debug
from bgstally.discord import Discord
from bgstally.fleetcarrier import FleetCarrier
from bgstally.market import Market
from bgstally.missionlog import MissionLog
from bgstally.overlay import Overlay
from bgstally.requestmanager import RequestManager
from bgstally.state import State
from bgstally.targetlog import TargetLog
from bgstally.tick import Tick
from bgstally.ui import UI
from bgstally.updatemanager import UpdateManager

TIME_WORKER_PERIOD_S = 60


class BGSTally:
    """
    Main plugin class
    """
    def __init__(self, plugin_name: str, version: semantic_version.Version):
        self.plugin_name:str = plugin_name
        self.version: semantic_version.Version = version


    def plugin_start(self, plugin_dir: str):
        """
        The plugin is starting up. Initialise all our objects.
        """
        self.plugin_dir = plugin_dir

        data_filepath = path.join(self.plugin_dir, FOLDER_DATA)
        if not path.exists(data_filepath): mkdir(data_filepath)

        # Classes
        self.debug:Debug = Debug(self)
        self.config:Config = Config(self)
        self.state:State = State(self)
        self.mission_log:MissionLog = MissionLog(self)
        self.target_log:TargetLog = TargetLog(self)
        self.discord:Discord = Discord(self)
        self.tick:Tick = Tick(self, True)
        self.overlay:Overlay = Overlay(self)
        self.activity_manager:ActivityManager = ActivityManager(self)
        self.fleet_carrier:FleetCarrier = FleetCarrier(self)
        self.market:Market = Market(self)
        self.request_manager:RequestManager = RequestManager(self)
        self.api_manager:APIManager = APIManager(self)
        self.update_manager:UpdateManager = UpdateManager(self)
        self.ui:UI = UI(self)

        self.thread:Thread = Thread(target=self._worker, name="BGSTally Main worker")
        self.thread.daemon = True
        self.thread.start()


    def plugin_stop(self):
        """
        The plugin is shutting down.
        """
        self.ui.shut_down()
        self.save_data()

        if self.update_manager.update_available:
            self.update_manager.update_plugin()


    def journal_entry(self, cmdr, is_beta, system, station, entry, state):
        """
        Parse an incoming journal entry and store the data we need
        """

        # Live galaxy check
        try:
            if not monitor.is_live_galaxy() or is_beta: return
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
            case 'ApproachSettlement' if state['Odyssey']:
                activity.settlement_approached(entry, self.state)
                dirty = True

            case 'CommitCrime':
                activity.crime_committed(entry, self.state)
                dirty = True

            case 'Docked':
                self.state.station_faction = entry['StationFaction']['Name']
                self.state.station_type = entry['StationType']
                dirty = True

            case 'FactionKillBond' if state['Odyssey']:
                activity.cb_received(entry, self.state)
                dirty = True

            case 'Location' | 'StartUp' if entry.get('Docked') == True:
                self.state.station_type = entry['StationType']
                dirty = True

            case 'Market':
                self.market.load()

            case 'MarketBuy':
                activity.trade_purchased(entry, self.state)
                dirty = True

            case 'MarketSell':
                activity.trade_sold(entry, self.state)
                dirty = True

            case 'MissionAbandoned':
                self.mission_log.delete_mission_by_id(entry.get('MissionID'))
                dirty = True

            case 'MissionAccepted':
                self.mission_log.add_mission(entry.get('Name', ""), entry.get('Faction', ""), entry.get('MissionID', ""), entry.get('Expiry', ""), system, station,
                    entry.get('Count', -1), entry.get('PassengerCount', -1), entry.get('KillCount', -1))
                dirty = True

            case 'MissionCompleted':
                activity.mission_completed(entry, self.mission_log)
                dirty = True

            case 'MissionFailed':
                activity.mission_failed(entry, self.mission_log)
                dirty = True

            case 'RedeemVoucher' if entry.get('Type') == 'bounty':
                activity.bv_redeemed(entry, self.state)
                dirty = True

            case 'RedeemVoucher' if entry.get('Type') == 'CombatBond':
                activity.cb_redeemed(entry, self.state)
                dirty = True

            case 'SellExplorationData' | 'MultiSellExplorationData':
                activity.exploration_data_sold(entry, self.state)
                dirty = True

            case 'SellOrganicData':
                activity.organic_data_sold(entry, self.state)
                dirty = True

            case 'ShipTargeted':
                activity.ship_targeted(entry, self.state)
                self.target_log.ship_targeted(entry, system)
                dirty = True

        if dirty:
            self.save_data()
            self.api_manager.send_activity(activity, cmdr)

        self.api_manager.send_event(entry, activity, cmdr)


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
        # TODO: Don't need to save all this all the time, be more selective
        self.mission_log.save()
        self.target_log.save()
        self.tick.save()
        self.activity_manager.save()
        self.state.save()
        self.fleet_carrier.save()
        self.api_manager.save()


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
