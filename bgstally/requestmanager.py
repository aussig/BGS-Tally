from queue import Queue
from re import IGNORECASE, compile, match
from threading import Thread
from time import sleep

import requests
from requests import Response

from bgstally.constants import RequestMethod
from bgstally.debug import Debug
from config import config

TIME_WORKER_PERIOD_S = 1
TIMEOUT_S = 10


class BGSTallyRequest:
    """
    Encapsulates a request that can be queued and processed in a thread
    """
    def __init__(self, endpoint:str, method:RequestMethod, callback:callable, params:dict, headers:dict, stream:bool, payload:dict|None, data:dict|None, attempts:int):
        # The endpoint to call
        self.endpoint:str = endpoint
        # The type of request
        self.method:RequestMethod = method
        # A callback function to call when the response is received
        self.callback:callable = callback
        # Request parameters
        self.params:dict = params
        # Request headers
        self.headers:dict = headers
        # For requests with large content, True to stream in chunks
        self.stream:bool = stream
        # For requests that send data, a Dict containing the payload
        self.payload:dict|None = payload
        # Any additional data required to be passed to the callback function when the response is received
        self.data:dict|None = data
        # The number of attempts made to send this request
        self.attempts:int = attempts

    def __str__(self):
        """
        String representation of this object
        """
        return f"BGSTallyRequest: \n" \
                    f"  endpoint: {self.endpoint} \n" \
                    f"  method: {self.method} \n" \
                    f"  params: {self.params} \n" \
                    f"  headers: {self.headers} \n" \
                    f"  stream: {self.stream} \n" \
                    f"  payload: {self.payload} \n" \
                    f"  data: {self.data} \n" \
                    f"  attempts: {self.attempts} \n"


class RequestManager:
    """
    Handles the queuing and processing of requests
    """
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.re_url = compile(
            r'^(?:http|ftp)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
            r'localhost|' #localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', IGNORECASE)
        self.request_queue:Queue = Queue()

        self.request_thread: Thread = Thread(target=self._worker, name="BGSTally Request worker")
        self.request_thread.daemon = True
        self.request_thread.start()


    def queue_request(self, endpoint:str, method:RequestMethod, callback:callable = None, params:dict = {}, headers:dict = {}, stream:bool = False, payload:dict|None = None, data:dict|None = None, attempts:int = 0) -> None:
        """
        Add a request to the queue
        """
        if not self.url_valid(endpoint):
            Debug.logger.info(f"Attempted to call {endpoint} which is not a well-formed URL")
            return

        headers:dict = {'User-Agent': f"{self.bgstally.plugin_name}/{self.bgstally.version}"} | headers

        self.request_queue.put(BGSTallyRequest(endpoint, method, callback, params, headers, stream, payload, data, attempts))


    def url_valid(self, url:str) -> bool:
        """
        Check whether a URL is well-formed
        """
        if url is None: return False
        return match(self.re_url, url) is not None


    def _worker(self) -> None:
        """
        Handle request thread work
        """
        Debug.logger.debug("Starting Request Worker...")

        while True:
            if config.shutting_down:
                Debug.logger.debug("Shutting down RequestManager Worker...")
                return

            sleep(TIME_WORKER_PERIOD_S)

            # Fetch from the queue. Blocks indefinitely until an item is available.
            request:BGSTallyRequest = self.request_queue.get()

            if not isinstance(request, BGSTallyRequest):
                Debug.logger.error(f"Queued request was not an instance of BGSTallyRequest")
                continue

            Debug.logger.info(f"Processing {request.method} request {request.endpoint}")

            response:Response = None
            try:
                match request.method:
                    case RequestMethod.GET: response = requests.get(request.endpoint, params=request.params, headers=request.headers, stream=request.stream, timeout=TIMEOUT_S)
                    case RequestMethod.POST: response = requests.post(request.endpoint, params=request.params, headers=request.headers, stream=request.stream, json=request.payload, timeout=TIMEOUT_S)
                    case RequestMethod.PUT: response = requests.put(request.endpoint, params=request.params, headers=request.headers, stream=request.stream, json=request.payload, timeout=TIMEOUT_S)
                    case RequestMethod.PATCH: response = requests.patch(request.endpoint, params=request.params, headers=request.headers, stream=request.stream, json=request.payload, timeout=TIMEOUT_S)
                    case RequestMethod.DELETE: response = requests.delete(request.endpoint, params=request.params, headers=request.headers, stream=request.stream, timeout=TIMEOUT_S)
                    case RequestMethod.HEAD: response = requests.head(request.endpoint, params=request.params, headers=request.headers, stream=request.stream, timeout=TIMEOUT_S)
                    case RequestMethod.OPTIONS: response = requests.options(request.endpoint, params=request.params, headers=request.headers, stream=request.stream, timeout=TIMEOUT_S)
                    case _:
                        Debug.logger.warning(f"Invalid request method {request.type}")
                        if request.callback: request.callback(False, response, request)
                        continue

                response.raise_for_status()

            except requests.exceptions.RequestException as e:
                Debug.logger.info(f"Request failure {request.endpoint}: {str(e)}")
                if request.callback: request.callback(False, response, request)

            else:
                # Success
                Debug.logger.info(f"Request success {request.endpoint}")
                if request.callback: request.callback(True, response, request)
