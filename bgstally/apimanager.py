from requests import Response

from bgstally.activity import Activity
from bgstally.constants import RequestMethod
from bgstally.debug import Debug
from bgstally.requestmanager import BGSTallyRequest

HEADER_APIKEY = "apikey"


class APIManager:
    """
    Handles interaction with APIs.
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally


    def activity_update(self, activity:Activity):
        """
        Current activity has been updated
        """
        headers:dict|None = None
        apikey:str = self.bgstally.state.APIActivitiesKey.get()

        if apikey != "": headers = {HEADER_APIKEY: apikey}

        self.bgstally.request_manager.queue_request(self.bgstally.state.APIActivitiesURL.get(), RequestMethod.PUT, self.version_info_received, headers=headers, payload=activity._as_dict())


    def version_info_received(self, success:bool, response:Response, request:BGSTallyRequest):
        """
        The API call completed
        """
