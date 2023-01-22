from bgstally.activity import Activity
from bgstally.api import API


class APIManager:
    """
    Handles a list of API objects.
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.apis:list[API] = []

        # TODO: Just creating a single API instance for testing, need to extend to multiple
        self.apis.append(API(self.bgstally))


    def send_activity(self, activity:Activity):
        """
        Activity data has been updated. Send it to all APIs.
        """
        api_activity:dict = self._build_api_activity(activity)
        for api in self.apis:
            api.send_activity(api_activity)


    def send_event(self, event:dict):
        """
        Event has been received. Add it to the events queue.
        """
        api_event:dict = self._build_api_event(event)
        for api in self.apis:
            api.send_event(api_event)


    def _build_api_activity(self, activity:Activity):
        """
        Build an API-ready activity ready for sending. A dict matching the API spec is built from the Activity data
        """
        # TODO: Create dict meeting API spec instead of just turning the Activity into a dict
        return activity._as_dict()


    def _build_api_event(self, event:dict, activity:Activity):
        """
        Build an API-ready event ready for sending. This just involves enhancing the event with some
        additional data
        """

        if 'StarSystem' not in event: event['StarSystem'] = activity.systems.get(self.bgstally.state.current_system_id, "")
        if 'SystemAddress' not in event: event['SystemAddress'] = self.bgstally.state.current_system_id
        event['tickID'] = activity.tick_id

        return event
