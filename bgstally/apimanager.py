from queue import Queue
from threading import Thread
from time import sleep

from bgstally.activity import Activity
from bgstally.constants import CheckStates, RequestMethod
from bgstally.debug import Debug

HEADER_APIKEY = "apikey"
ENDPOINT_ACTIVITIES = "activities"
ENDPOINT_EVENTS = "events"
TIME_ACTIVITIES_WORKER_PERIOD_S = 60
TIME_EVENTS_WORKER_PERIOD_S = 5
BATCH_EVENTS_SIZE = 10


class APIManager:
    """
    Handles interaction with APIs.
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        # activity is used to store a single Activity object when it's been updated.
        self.activity:Activity = None

        # Events queue is used to batch up events API messages. All batched messages are sent when the worker works.
        self.events_queue:Queue = Queue()

        self.activities_thread: Thread = Thread(target=self._activities_worker, name="BGSTally Activities API Worker")
        self.activities_thread.daemon = True
        self.activities_thread.start()

        self.events_thread: Thread = Thread(target=self._events_worker, name="BGSTally Events API Worker")
        self.events_thread.daemon = True
        self.events_thread.start()


    def send_activity(self, activity:Activity):
        """
        Activity data has been updated. Store it ready for the next send via the worker
        """
        if not self.bgstally.state.APIActivitiesEnabled.get() == CheckStates.STATE_ON or not self.bgstally.request_manager.url_valid(self.bgstally.state.APIURL.get()):
            self.activity = None
            return

        self.activity = activity


    def send_event(self, event:dict):
        """
        Event has been received. Add it to the events queue.
        """
        Debug.logger.debug(f"Queuing Event: {self.bgstally.state.APIEventsEnabled}  {self.bgstally.state.APIURL.get()}")
        if not self.bgstally.state.APIEventsEnabled.get() == CheckStates.STATE_ON or not self.bgstally.request_manager.url_valid(self.bgstally.state.APIURL.get()):
            with self.events_queue.mutex:
                self.events_queue.queue.clear()
            return
        Debug.logger.debug("Putting in queue...")
        self.events_queue.put(event)


    def _activities_worker(self) -> None:
        """
        Handle activities API. If there's updated activity, this worker triggers a call to the activities endpoint
        on a regular time period.
        """
        Debug.logger.debug("Starting Activities API Worker...")

        while True:
            Debug.logger.debug("Activities worker WORK...")
            # Need to check settings every time in case the user has changed them
            if not self.bgstally.state.APIActivitiesEnabled.get() == CheckStates.STATE_ON or not self.bgstally.request_manager.url_valid(self.bgstally.state.APIURL.get()):
                self.activity = None

            if self.activity is not None:
                Debug.logger.debug("PUTing activity...")
                headers:dict = {}
                apikey:str = self.bgstally.state.APIKey.get()
                url:str = self.bgstally.state.APIURL.get().rstrip('/') + '/' + ENDPOINT_ACTIVITIES

                if apikey != "": headers = {HEADER_APIKEY: apikey}

                self.bgstally.request_manager.queue_request(url, RequestMethod.PUT, headers=headers, payload=self.activity._as_dict())

                self.activity = None

            sleep(TIME_ACTIVITIES_WORKER_PERIOD_S)


    def _events_worker(self) -> None:
        """
        Handle events API. If there's queued events, this worker triggers a call to the events endpoint
        on a regular time period, sending the currently queued batch of events.
        """
        Debug.logger.debug("Starting Events API Worker...")

        while True:
            Debug.logger.debug("Events worker WORK...")
            # Need to check settings every time in case the user has changed them
            if not self.bgstally.state.APIEventsEnabled.get() == CheckStates.STATE_ON or not self.bgstally.request_manager.url_valid(self.bgstally.state.APIURL.get()):
                with self.events_queue.mutex:
                    self.events_queue.queue.clear()

            if self.events_queue.qsize() > 0:
                Debug.logger.debug("POSTing events...")
                headers:dict = {}
                apikey:str = self.bgstally.state.APIKey.get()
                url:str = self.bgstally.state.APIURL.get().rstrip('/') + '/' + ENDPOINT_EVENTS

                if apikey != "": headers = {HEADER_APIKEY: apikey}

                # Grab all available events in the queue up to a maximum batch size
                queued_events:list = [self.events_queue.get(block=False) for _ in range(min(BATCH_EVENTS_SIZE, self.events_queue.qsize()))]
                Debug.logger.debug(queued_events)
                self.bgstally.request_manager.queue_request(url, RequestMethod.POST, headers=headers, payload=queued_events)

            sleep(TIME_EVENTS_WORKER_PERIOD_S)
