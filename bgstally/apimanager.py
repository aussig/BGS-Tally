from bgstally.api import API
from bgstally.windows.api import WindowAPI

HEADER_APIKEY = "apikey"

# {
#     "name": "Name of the website or application",
#     "description": "Description of the application, how your data is used, etc...",
#     "url": "https://website.com/more-information", # URL to more information about the application, or the application home page
#     "version": "1.0.0",
#     "endpoints": { # If not present, defaults to all endpoints enabled. If present, only data for listed endpoints should be sent
#         "activities":
#         {
#             "min_period": 60 # Minimum number of seconds between requests. There will also be a hard minimum applied client-side (so values lower than that will be ignored). If omitted, use client default.
#         },
#         "events":
#         {
#             "min_period": 15, # Minimum number of seconds between requests. There will also be a hard minimum applied client-side (so values lower than that will be ignored). If omitted, use client default.
#             "max_batch": 10 # Maximum number of events to include in a single request. Any remaining events will be sent in the next request. If omitted, use client default.
#         }
#     },
#     "events": # If not present, accept default set of events. If present, only listed events should be sent to API (with optional further filtering).
#     {
#         "MissionAccepted":
#         {
#             "filters":
#             {
#                 "Name": "^Mission_TW"
#             }
#         },
#         "MissionCompleted":
#         {
#             "filters":
#             {
#                 "Name": "^Mission_TW"
#             }
#         },
#         "ApproachSettlement":
#         {
#             # Can be an empty object, in which case all occurrences of this event are sent
#         },
#         "Died":
#         {
#             "filters":
#             {
#                 "KillerShip": "scout_hq|scout_nq|scout_q|scout|thargonswarm|thargon"
#             }
#         },
#         "FactionKillBond":
#         {
#             "filters":
#             {
#                 "AwardingFaction": "^\\$faction_PilotsFederation;$",
#                 "VictimFaction": "^\\$faction_Thargoid;$"
#             }
#         },
#         "CollectCargo":
#         {
#             "filters":
#             {
#                 "Type": "$UnknownArtifact2_name;"
#             }
#         }
#     }
# }


class APIManager:
    """
    Handles a list of API objects.
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.apis:list = []

        # TODO: Just creating a single API instance for testing, need to extend to multiple
        self.apis.append(API(self.bgstally, self))


    def get_headers(self, apikey:str) -> dict:
        """
        Get the API headers
        """
        headers:dict = {}
        if apikey is not None and apikey != "": headers = {HEADER_APIKEY: apikey}
        return headers
