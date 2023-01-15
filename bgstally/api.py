
from re import match

from time import sleep

from bgstally.activity import Activity
import semantic_version
from threading import Thread
from queue import Queue
from requests import JSONDecodeError, Response

from bgstally.activity import Activity
from bgstally.constants import CheckStates, RequestMethod
from bgstally.debug import Debug
from bgstally.requestmanager import BGSTallyRequest
from bgstally.utils import get_by_path


ENDPOINT_ACTIVITIES = "activities"
ENDPOINT_DISCOVERY = "discovery"
ENDPOINT_EVENTS = "events"

NAME_DEFAULT = "The API URL you have entered has not supplied a name."
DESCRIPTION_DEFAULT = "Sending the default set of events to the API. This includes information on your location, missions, bounty vouchers, \
    trade, combat bonds and exploration data. PLEASE ENSURE YOU TRUST the application, website or system you are sending this information to."
VERSION_DEFAULT = "1.0.0"
ENDPOINTS_DEFAULT = {ENDPOINT_ACTIVITIES: {}, ENDPOINT_EVENTS: {}}
EVENTS_FILTER_DEFAULTS = {'ApproachSettlement': {}, 'CarrierJump': {}, 'CommitCrime': {}, 'Died': {}, 'Docked': {}, 'FactionKillBond': {},
    'FSDJump': {}, 'Location': {}, 'MarketBuy': {}, 'MarketSell': {}, 'MissionAbandoned': {}, 'MissionAccepted': {}, 'MissionCompleted': {},
    'MissionFailed': {}, 'MultiSellExplorationData': {}, 'RedeemVoucher': {}, 'SellExplorationData': {}, 'StartUp': {}}

TIME_ACTIVITIES_WORKER_PERIOD_S = 60
TIME_EVENTS_WORKER_PERIOD_S = 5
BATCH_EVENTS_MAX_SIZE = 10


class API:
    """
    Handles data for an API.
    """

    def __init__(self, bgstally, api_manager):
        """
        Instantiate
        """
        self.bgstally = bgstally

        # TODO: All these must be stored per API instance, not just a single shared one in state
        self.url:str = self.bgstally.state.APIURL.get().rstrip('/') + '/'
        self.key:str = self.bgstally.state.APIKey.get()
        self.activities_enabled:str = self.bgstally.state.APIActivitiesEnabled.get()
        self.events_enabled:str = self.bgstally.state.APIEventsEnabled.get()

        # Default API settings. Overridden by response from /discovery endpoint if it exists
        self.name:str = NAME_DEFAULT
        self.version:semantic_version = semantic_version.Version.coerce(VERSION_DEFAULT)
        self.description:str = DESCRIPTION_DEFAULT
        self.endpoints:dict = ENDPOINTS_DEFAULT
        self.events:dict = EVENTS_FILTER_DEFAULTS
        self.discovery_events:list = []

        # activity is used to store a single Activity object when it's been updated.
        self.activity:Activity = None

        # Events queue is used to batch up events API messages. All batched messages are sent when the worker works.
        self.events_queue:Queue = Queue()

        self.activities_thread: Thread = Thread(target=self._activities_worker, name=f"BGSTally Activities API Worker ({self.url})")
        self.activities_thread.daemon = True
        self.activities_thread.start()

        self.events_thread: Thread = Thread(target=self._events_worker, name=f"BGSTally Events API Worker ({self.url})")
        self.events_thread.daemon = True
        self.events_thread.start()

        self.bgstally.request_manager.queue_request(self.url + ENDPOINT_DISCOVERY, RequestMethod.GET, headers=api_manager.get_headers(self.key), callback=self.discovery_received)


    def discovery_received(self, success:bool, response:Response, request:BGSTallyRequest):
        """
        Discovery API information received from the server
        """
        if not success:
            Debug.logger.warning(f"Unable to discover API capabilities, falling back to defaults")
            return

        discovery_data:dict = None

        try:
            discovery_data = response.json()
        except JSONDecodeError:
            Debug.logger.warning(f"Event discovery data is invalid, falling back to defaults")
            return

        if not isinstance(discovery_data, dict):
            Debug.logger.warning(f"Event discovery data is invalid, falling back to defaults")
            return

        self.version = semantic_version.Version.coerce(discovery_data.get('version', VERSION_DEFAULT))
        self.description = discovery_data.get('description', DESCRIPTION_DEFAULT)
        self.events = discovery_data.get('events', EVENTS_FILTER_DEFAULTS)
        self.endpoints = discovery_data.get('endpoints', ENDPOINTS_DEFAULT)

        if self._discovery_events_changed():
            # Note we're in a thread
            Debug.logger.info(f"API Requested Event list has changed, ALERT USER")
            # Alert user, ask for API approval again
            # Only once approved:
            # self.discovery_events = self.events.keys()


    def send_activity(self, activity:Activity):
        """
        Activity data has been updated. Store it ready for the next send via the worker
        """
        if not self.activities_enabled == CheckStates.STATE_ON \
                or not ENDPOINT_ACTIVITIES in self.endpoints \
                or not self.bgstally.request_manager.url_valid(self.url):
            self.activity = None
            return

        self.activity = activity


    def send_event(self, event:dict):
        """
        Event has been received. Add it to the events queue.
        """
        if not self.self.events_enabled == CheckStates.STATE_ON \
                or not ENDPOINT_EVENTS in self.endpoints \
                or not self.bgstally.request_manager.url_valid(self.url):
            with self.events_queue.mutex:
                self.events_queue.queue.clear()
            return

        if event.get('event', '') not in self.events or self._is_filtered(event):
            return

        self.events_queue.put(event)


    def _discovery_events_changed(self) -> bool:
        """
        Return True if the discovered events have changed from the previously discovered events
        """
        previous_events_hash:int = hash(self.discovery_events.sort())
        latest_events_hash:int = hash(self.events.keys().sort())
        return previous_events_hash == latest_events_hash


    def _is_filtered(self, event:dict) -> bool:
        """
        Return True if this event should be filtered (omitted) from sending to the API.
        """
        filters:dict = get_by_path(self.events, [event.get('event', ''), 'filters'], None)
        if filters is None: return False

        for field, filter in filters.items():
            Debug.logger.info(f"Checking for match against {filter} in field {field} in event. Field value: {event.get(field, '')}. Match: {match(filter, event.get(field, ''))}")
            if not match(filter, event.get(field, "")): return True

        # All fields matched, don't filter out this event
        return False


    def _activities_worker(self) -> None:
        """
        Handle activities API. If there's updated activity, this worker triggers a call to the activities endpoint
        on a regular time period.
        """
        Debug.logger.debug("Starting Activities API Worker...")

        while True:
            # Need to check settings every time in case the user has changed them
            if not self.activities_enabled == CheckStates.STATE_ON \
                    or not ENDPOINT_ACTIVITIES in self.endpoints \
                    or not self.bgstally.request_manager.url_valid(self.url):
                self.activity = None

            if self.activity is not None:
                url:str = self.url + ENDPOINT_ACTIVITIES

                self.bgstally.request_manager.queue_request(url, RequestMethod.PUT, headers=self._get_headers(), payload=self.activity._as_dict())

                self.activity = None

            sleep(max(int(get_by_path(self.endpoints, [ENDPOINT_ACTIVITIES, 'min_period'], 0)), TIME_ACTIVITIES_WORKER_PERIOD_S))


    def _events_worker(self) -> None:
        """
        Handle events API. If there's queued events, this worker triggers a call to the events endpoint
        on a regular time period, sending the currently queued batch of events.
        """
        Debug.logger.debug("Starting Events API Worker...")

        while True:
            # Need to check settings every time in case the user has changed them
            if not self.events_enabled == CheckStates.STATE_ON \
                    or not ENDPOINT_EVENTS in self.endpoints \
                    or not self.bgstally.request_manager.url_valid(self.url):
                with self.events_queue.mutex:
                    self.events_queue.queue.clear()

            if self.events_queue.qsize() > 0:
                url:str = self.url + ENDPOINT_EVENTS

                # Grab all available events in the queue up to a maximum batch size
                batch_size:int = max(int(get_by_path(self.endpoints, [ENDPOINT_EVENTS, 'max_batch'], 0)), BATCH_EVENTS_MAX_SIZE)
                queued_events:list = [self.events_queue.get(block=False) for _ in range(min(batch_size, self.events_queue.qsize()))]
                self.bgstally.request_manager.queue_request(url, RequestMethod.POST, headers=self._get_headers(), payload=queued_events)

            sleep(max(int(get_by_path(self.endpoints, [ENDPOINT_EVENTS, 'min_period'], 0)), TIME_EVENTS_WORKER_PERIOD_S))
