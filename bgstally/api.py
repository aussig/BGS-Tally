
from json import JSONDecodeError
from queue import Queue
from re import match
from threading import Thread
from time import sleep

import semantic_version
from requests import Response

from bgstally.constants import RequestMethod
from bgstally.debug import Debug
from bgstally.requestmanager import BGSTallyRequest
from bgstally.utils import get_by_path

API_VERSION = "1.5.0"

ENDPOINT_ACTIVITIES = "activities" # Used as both the dict key and default path
ENDPOINT_DISCOVERY = "discovery"   # Used as the path
ENDPOINT_EVENTS = "events"         # Used as both the dict key and default path

NAME_DEFAULT = "This server has not supplied a name."
VERSION_DEFAULT = API_VERSION
DESCRIPTION_DEFAULT = "This server has not supplied a description."
ENDPOINTS_DEFAULT = {ENDPOINT_ACTIVITIES: {'path': ENDPOINT_ACTIVITIES}, ENDPOINT_EVENTS: {'path': ENDPOINT_EVENTS}}
EVENTS_FILTER_DEFAULTS = {'ApproachSettlement': {}, 'CarrierJump': {}, 'CommitCrime': {}, 'Died': {}, 'Docked': {}, 'FactionKillBond': {},
    'FSDJump': {}, 'Location': {}, 'MarketBuy': {}, 'MarketSell': {}, 'MissionAbandoned': {}, 'MissionAccepted': {}, 'MissionCompleted': {},
    'MissionFailed': {}, 'MultiSellExplorationData': {}, 'RedeemVoucher': {}, 'SellExplorationData': {}, 'StartUp': {}}

HEADER_APIKEY = "apikey"
HEADER_APIVERSION = "apiversion"
TIME_ACTIVITIES_WORKER_PERIOD_S = 60
TIME_EVENTS_WORKER_PERIOD_S = 5
BATCH_EVENTS_MAX_SIZE = 10


class API:
    """
    Handles data for an API.
    """

    def __init__(self, bgstally, data:list = None):
        """
        Instantiate
        """
        self.bgstally = bgstally

        # Populate API user and discovery settings
        if data is not None:
            self.from_dict(data)
        else:
            # Default user state
            self.url:str = ""
            self.key:str = ""
            self.activities_enabled:bool = True
            self.events_enabled:bool = True
            self.user_approved:bool = False

            # Default API discovery state. Overridden by response from /discovery endpoint if it exists
            self._revert_discovery_to_defaults()

        # Used to store a single dict containing BGS activity when it's been updated.
        self.activity:dict = None

        # Events queue is used to batch up events API messages. All batched messages are sent when the worker works.
        self.events_queue:Queue = Queue()

        self.activities_thread: Thread = Thread(target=self._activities_worker, name=f"BGSTally Activities API Worker ({self.url})")
        self.activities_thread.daemon = True
        self.activities_thread.start()

        self.events_thread: Thread = Thread(target=self._events_worker, name=f"BGSTally Events API Worker ({self.url})")
        self.events_thread.daemon = True
        self.events_thread.start()

        self.discover(self.discovery_received)


    def as_dict(self) -> dict:
        """
        Return a dict containing our user and discovery state
        """
        return {
            # User state
            'url': self.url,
            'key': self.key,
            'activities_enabled': self.activities_enabled,
            'events_enabled': self.events_enabled,
            'user_approved': self.user_approved,

            # Discovery state
            'name': self.name,
            'version': str(self.version),
            'description': self.description,
            'endpoints': self.endpoints,
            'events': self.events
        }


    def from_dict(self, data:dict):
        """
        Populate our user and discovery state from a dict
        """
        # User state
        self.url:str = data['url']
        self.key:str = data['key']
        self.activities_enabled:bool = data['activities_enabled']
        self.events_enabled:bool = data['events_enabled']
        self.user_approved:bool = data['user_approved']

        # Discovery state
        self.name:str = data['name']
        self.version:semantic_version = semantic_version.Version.coerce(data['version'])
        self.description:str = data['description']
        self.endpoints:dict = data['endpoints']
        self.events:dict = data['events']


    def discover(self, callback:callable):
        """
        Call the discovery endpoint
        """
        self.bgstally.request_manager.queue_request(self.url + ENDPOINT_DISCOVERY, RequestMethod.GET, headers=self._get_headers(), callback=callback)


    def discovery_received(self, success:bool, response:Response, request:BGSTallyRequest):
        """
        Discovery API information received from the server
        """
        if not success:
            Debug.logger.info(f"Unable to discover API capabilities, falling back to defaults")
            self._revert_discovery_to_defaults()
            return

        discovery_data:dict = None

        try:
            discovery_data = response.json()
        except JSONDecodeError:
            Debug.logger.warning(f"Event discovery data is invalid, falling back to defaults")
            self._revert_discovery_to_defaults()
            return

        if not isinstance(discovery_data, dict):
            Debug.logger.warning(f"Event discovery data is invalid, falling back to defaults")
            self._revert_discovery_to_defaults()
            return

        self.name = discovery_data.get('name', NAME_DEFAULT)
        self.description = discovery_data.get('description', DESCRIPTION_DEFAULT)
        self.endpoints = discovery_data.get('endpoints', ENDPOINTS_DEFAULT)

        if self._discovery_events_changed(discovery_data.get('events', EVENTS_FILTER_DEFAULTS)):
            self.user_approved = False
            # Put Message in BGS-Tally message field (with link to API settings? Possibly not when we have multiple APIs)
            self.bgstally.api_manager.api_updated = True
            if self.bgstally.ui.frame: self.bgstally.ui.frame.after(1000, self.bgstally.ui.update_plugin_frame())

        self.events = discovery_data.get('events', EVENTS_FILTER_DEFAULTS)


    def send_activity(self, activity:dict):
        """
        Activity data has been updated. Store it ready for the next send via the worker.
        """
        if not self.user_approved \
                or not self.activities_enabled \
                or not ENDPOINT_ACTIVITIES in self.endpoints \
                or not self.bgstally.request_manager.url_valid(self.url):
            self.activity = None
            return

        self.activity = activity


    def send_event(self, event:dict):
        """
        Event has been received. Add it to the events queue.
        """
        if not self.user_approved \
                or not self.events_enabled \
                or not ENDPOINT_EVENTS in self.endpoints \
                or not self.bgstally.request_manager.url_valid(self.url):
            with self.events_queue.mutex:
                self.events_queue.queue.clear()
            return

        if event.get('event', '') not in self.events or self._is_filtered(event):
            return

        self.events_queue.put(event)


    def _revert_discovery_to_defaults(self):
        """
        Revert all API information to default values
        """
        self.name:str = NAME_DEFAULT
        self.version:semantic_version = semantic_version.Version.coerce(VERSION_DEFAULT)
        self.description:str = DESCRIPTION_DEFAULT
        self.endpoints:dict = ENDPOINTS_DEFAULT
        self.events:dict = EVENTS_FILTER_DEFAULTS


    def _discovery_events_changed(self, discovery_events:dict) -> bool:
        """
        Return True if the discovered events have changed from the previously discovered events
        """
        previous_events:list = [*self.events.keys()]
        latest_events:list = [*discovery_events.keys()]
        previous_events.sort()
        latest_events.sort()

        return hash(tuple(previous_events)) != hash(tuple(latest_events))


    def _is_filtered(self, event:dict) -> bool:
        """
        Return True if this event should be filtered (omitted from sending to the API).
        """
        filters:dict = get_by_path(self.events, [event.get('event', ''), 'filters'], None)
        if filters is None: return False

        for field, filter in filters.items():
            filter_str:str = str(filter)
            value_str:str = str(event.get(field, ""))
            if not match(filter_str, value_str): return True

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
            if not self.user_approved \
                    or not self.activities_enabled \
                    or not ENDPOINT_ACTIVITIES in self.endpoints \
                    or not self.bgstally.request_manager.url_valid(self.url):
                self.activity = None

            if self.activity is not None:
                url:str = self.url + get_by_path(self.endpoints, [ENDPOINT_ACTIVITIES, 'path'], ENDPOINT_ACTIVITIES)

                self.bgstally.request_manager.queue_request(url, RequestMethod.PUT, headers=self._get_headers(), payload=self.activity)

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
            if not self.user_approved \
                    or not self.events_enabled \
                    or not ENDPOINT_EVENTS in self.endpoints \
                    or not self.bgstally.request_manager.url_valid(self.url):
                with self.events_queue.mutex:
                    self.events_queue.queue.clear()

            if self.events_queue.qsize() > 0:
                url:str = self.url + get_by_path(self.endpoints, [ENDPOINT_EVENTS, 'path'], ENDPOINT_EVENTS)

                # Grab all available events in the queue up to a maximum batch size
                batch_size:int = max(int(get_by_path(self.endpoints, [ENDPOINT_EVENTS, 'max_batch'], 0)), BATCH_EVENTS_MAX_SIZE)
                queued_events:list = [self.events_queue.get(block=False) for _ in range(min(batch_size, self.events_queue.qsize()))]
                self.bgstally.request_manager.queue_request(url, RequestMethod.POST, headers=self._get_headers(), payload=queued_events)

            sleep(max(int(get_by_path(self.endpoints, [ENDPOINT_EVENTS, 'min_period'], 0)), TIME_EVENTS_WORKER_PERIOD_S))


    def _get_headers(self) -> dict:
        """
        Get the API headers
        """
        headers:dict = {}
        headers[HEADER_APIVERSION] = API_VERSION
        if self.key is not None and self.key != "": headers[HEADER_APIKEY] = self.key
        return headers
