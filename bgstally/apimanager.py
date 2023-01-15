from bgstally.activity import Activity
from bgstally.api import API


class APIManager:
    """
    Handles a list of API objects.
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.apis:list = []

        # TODO: Just creating a single API instance for testing, need to extend to multiple
        self.apis.append(API(self.bgstally))


    def send_activity(self, activity:Activity):
        """
        Activity data has been updated. Send it to all APIs.
        """
        for api in self.apis:
            api.send_activity(activity)


    def send_event(self, event:dict):
        """
        Event has been received. Add it to the events queue.
        """
        for api in self.apis:
            api.send_event(event)
