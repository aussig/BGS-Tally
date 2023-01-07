from bgstally.activity import Activity
from bgstally.constants import RequestMethod
from bgstally.debug import Debug

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
        headers:dict = {}
        apikey:str = self.bgstally.state.APIActivitiesKey.get()

        if apikey != "": headers = {HEADER_APIKEY: apikey}

        self.bgstally.request_manager.queue_request(self.bgstally.state.APIActivitiesURL.get(), RequestMethod.PUT, headers=headers, payload=activity._as_dict())
