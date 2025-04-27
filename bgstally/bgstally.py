import sys
from os import mkdir, path
from threading import Thread
from time import sleep

import semantic_version
from companion import SERVER_LIVE, CAPIData
from monitor import monitor

from bgstally.activity import Activity
from bgstally.activitymanager import ActivityManager
from bgstally.apimanager import APIManager
from bgstally.colonisation import Colonisation
from bgstally.config import Config
from bgstally.constants import FOLDER_OTHER_DATA, UpdateUIPolicy
from bgstally.debug import Debug
from bgstally.discord import Discord
from bgstally.fleetcarrier import FleetCarrier
from bgstally.formatters.default import DefaultActivityFormatter
from bgstally.formattermanager import ActivityFormatterManager
from bgstally.market import Market
from bgstally.missionlog import MissionLog
from bgstally.objectivesmanager import ObjectivesManager
from bgstally.overlay import Overlay
from bgstally.requestmanager import RequestManager
from bgstally.state import State
from bgstally.targetmanager import TargetManager
from bgstally.tick import Tick
from bgstally.ui import UI
from bgstally.updatemanager import UpdateManager
from bgstally.utils import _, get_by_path
from bgstally.webhookmanager import WebhookManager
from config import appversion, config

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

        # Debug and Config Classes
        self.debug: Debug = Debug(self)
        self.config: Config = Config(self)

        # True only if we are running a dev version
        self.dev_mode: bool = False

        # Load sentry to track errors during development - Hard check on "dev" versions ONLY (which never go out to testers)
        # If you are a developer and want to use sentry, install the sentry_sdk inside the ./thirdparty folder and add your full dsn
        # (starting https://) to a 'sentry' entry in config.ini file. Set the plugin version in load.py to include a 'dev' prerelease,
        # e.g. "3.3.0-dev"
        if type(self.version.prerelease) is tuple and len(self.version.prerelease) > 0 and self.version.prerelease[0] == "dev":
            self.dev_mode = True
            sys.path.append(path.join(plugin_dir, 'thirdparty'))
            try:
                import sentry_sdk
                sentry_sdk.init(
                    dsn=self.config.apikey_sentry()
                )
                Debug.logger.info("Enabling Sentry Error Logging")
            except ImportError:
                pass

        data_filepath = path.join(self.plugin_dir, FOLDER_OTHER_DATA)
        if not path.exists(data_filepath): mkdir(data_filepath)

        # Main Classes
        self.state: State = State(self)
        self.mission_log: MissionLog = MissionLog(self)
        self.target_manager: TargetManager = TargetManager(self)
        self.discord: Discord = Discord(self)
        self.tick: Tick = Tick(self, True)
        self.overlay: Overlay = Overlay(self)
        self.activity_manager: ActivityManager = ActivityManager(self)
        self.fleet_carrier: FleetCarrier = FleetCarrier(self)
        self.market: Market = Market(self)
        self.request_manager: RequestManager = RequestManager(self)
        self.api_manager: APIManager = APIManager(self)
        self.webhook_manager: WebhookManager = WebhookManager(self)
        self.update_manager: UpdateManager = UpdateManager(self)
        self.ui: UI = UI(self)
        self.formatter_manager: ActivityFormatterManager = ActivityFormatterManager(self)
        self.objectives_manager: ObjectivesManager = ObjectivesManager(self)
        self.colonisation: Colonisation = Colonisation(self)
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
            if not monitor.is_live_galaxy() or is_beta: return
        except Exception as e:
            self.debug.logger.error(f"The EDMC Version is too old, please upgrade to v5.6.0 or later", exc_info=e)
            return

        activity: Activity = self.activity_manager.get_current_activity()

        # Total hack for now. We need cmdr in Activity to allow us to send it to the API when the user changes values in the UI.
        # What **should** happen is each Activity object should be associated with a single CMDR, and then all reporting
        # kept separate per CMDR.
        activity.cmdr = cmdr

        dirty: bool = False

        if entry.get('event') in ['StartUp', 'Location', 'FSDJump', 'CarrierJump']:
            activity.system_entered(entry, self.state)
            self.colonisation.journal_entry(cmdr, is_beta, system, station, entry, state)
            dirty = True

        mission:dict = self.mission_log.get_mission(entry.get('MissionID'))

        match entry.get('event'):
            case 'ApproachSettlement' if state['Odyssey']:
                activity.settlement_approached(entry, self.state)
                dirty = True

            case 'Bounty':
                activity.bv_received(entry, self.state, cmdr)
                dirty = True

            case 'CapShipBond':
                activity.cap_ship_bond_received(entry, cmdr)
                dirty = True

            case 'Cargo':
                self.colonisation.journal_entry(cmdr, is_beta, system, station, entry, state)
                activity.cargo(entry)

            case 'CarrierJumpCancelled':
                self.fleet_carrier.jump_cancelled()

            case 'CarrierJumpRequest':
                self.fleet_carrier.jump_requested(entry)

            case 'CarrierStats':
                self.fleet_carrier.stats_received(entry)

            case 'CarrierTradeOrder':
                self.fleet_carrier.trade_order(entry)

            case 'CollectCargo':
                activity.cargo_collected(entry, self.state)
                dirty = True

            case 'CommitCrime':
                activity.crime_committed(entry, self.state)
                dirty = True

            case 'Died':
                self.target_manager.died(entry, system)

            case 'Docked':
                self.state.station_faction = get_by_path(entry, ['StationFaction', 'Name'], self.state.station_faction) # Default to existing value
                self.state.station_type = entry.get('StationType', "")
                self.state.current_system_id = entry.get('SystemAddress' ,"")
                self.state.current_system = entry.get('SystemName' ,"")
                self.colonisation.journal_entry(cmdr, is_beta, system, station, entry, state)
                dirty = True

            case 'EjectCargo':
                activity.cargo_ejected(entry)
                dirty = True

            case 'FactionKillBond' if state['Odyssey']:
                activity.cb_received(entry, self.state, cmdr)
                dirty = True

            case 'Friends' if entry.get('Status') == "Requested":
                self.target_manager.friend_request(entry, system)

            case 'Friends' if entry.get('Status') == "Added":
                self.target_manager.friend_added(entry, system)

            case 'FSDJump':
                self.state.current_system_id = entry.get('SystemAddress')
                self.state.current_system = entry.get('SystemSystem')
                self.dirty = True

            case 'Interdicted':
                self.target_manager.interdicted(entry, system)

            case 'Location' | 'StartUp' if entry.get('Docked') == True:
                self.state.station_faction = get_by_path(entry, ['StationFaction', 'Name'], self.state.station_faction) # Default to existing value
                dirty = True

            case 'Loadout':
                # Update cargo capacity from Loadout event
                if 'CargoCapacity' in entry:
                    self.state.cargo_capacity = entry.get('CargoCapacity')
                    self.ui.update_plugin_frame()

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
                self.mission_log.add_mission(entry.get('Name', ""), entry.get('Faction', ""), entry.get('MissionID', ""), entry.get('Expiry', ""),
                                             entry.get('DestinationSystem', ""), entry.get('DestinationSettlement', ""), system, station,
                                             entry.get('Count', -1), entry.get('PassengerCount', -1), entry.get('KillCount', -1),
                                             entry.get('TargetFaction', ""))
                dirty = True

            case 'MissionCompleted':
                activity.mission_completed(entry, self.mission_log)
                dirty = True

            case 'MissionFailed':
                activity.mission_failed(entry, self.mission_log)
                dirty = True

            case 'ReceiveText':
                self.target_manager.received_text(entry, system)

            case 'RedeemVoucher' if entry.get('Type') == 'bounty':
                activity.bv_redeemed(entry, self.state)
                dirty = True

            case 'RedeemVoucher' if entry.get('Type') == 'CombatBond':
                activity.cb_redeemed(entry, self.state)
                dirty = True

            case 'Resurrect':
                activity.player_resurrected()
                dirty = True

            case 'SearchAndRescue':
                activity.search_and_rescue(entry, self.state)
                dirty = True

            case 'SellExplorationData' | 'MultiSellExplorationData':
                activity.exploration_data_sold(entry, self.state)
                dirty = True

            case 'SellOrganicData':
                activity.organic_data_sold(entry, self.state)
                dirty = True

            case 'ShipTargeted':
                activity.ship_targeted(entry, self.state)
                self.target_manager.ship_targeted(entry, system)
                dirty = True

            case 'SupercruiseDestinationDrop':
                activity.destination_dropped(entry, self.state)
                dirty = True

            case 'SupercruiseEntry':
                self.state.current_body = None
                activity.supercruise(entry, self.state)

            case 'SupercruiseExit':
                self.state.current_body = entry.get('Body')
                dirty = True

            case 'Undocked' if entry.get('Taxi') == False:
                self.state.station_faction = ""
                self.state.station_type = ""

            case 'WingInvite':
                self.target_manager.team_invite(entry, system)

            # Colonisation events
            case 'ColonisationSystemClaim':
                self.colonisation.journal_entry(cmdr, is_beta, system, station, entry, state)
                dirty = True

            case 'ColonisationBeaconDeployed':
                self.colonisation.journal_entry(cmdr, is_beta, system, station, entry, state)
                dirty = True

            case 'ColonisationConstructionDepot':
                self.colonisation.journal_entry(cmdr, is_beta, system, station, entry, state)
                dirty = True

            case 'ColonisationContribution':
                self.colonisation.journal_entry(cmdr, is_beta, system, station, entry, state)
                dirty = True

        if dirty:
            self.save_data()
            self.api_manager.send_activity(activity, cmdr)

        self.api_manager.send_event(entry, activity, cmdr, mission)


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
        self.target_manager.save()
        self.tick.save()
        self.activity_manager.save()
        self.state.save()
        self.fleet_carrier.save()
        self.api_manager.save()
        self.webhook_manager.save()
        self.colonisation.save()


    def new_tick(self, force: bool, uipolicy: UpdateUIPolicy):
        """
        Start a new tick.
        """
        if force: self.tick.force_tick()
        if not self.activity_manager.new_tick(self.tick, force): return

        match uipolicy:
            case UpdateUIPolicy.IMMEDIATE:
                self.ui.update_plugin_frame()
            case UpdateUIPolicy.LATER:
                self.ui.frame.after(1000, self.ui.update_plugin_frame())

        self.overlay.display_message("tickwarn", _("NEW TICK DETECTED!"), True, 180, "green") # LANG: Overlay message


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
