from bgstally.activity import Activity
from bgstally.constants import CheckStates, RequestMethod
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
        if not self.bgstally.state.APIActivitiesEnabled == CheckStates.STATE_ON or not self.bgstally.request_manager.url_valid(self.bgstally.state.APIURL.get()):
            return

        headers:dict = {}
        apikey:str = self.bgstally.state.APIKey.get()

        if apikey != "": headers = {HEADER_APIKEY: apikey}

        self.bgstally.request_manager.queue_request(self.bgstally.state.APIURL.get(), RequestMethod.PUT, headers=headers, payload=activity._as_dict())
