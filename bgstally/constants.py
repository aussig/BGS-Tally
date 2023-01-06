from enum import Enum


# Conflict Zones
class CZs(Enum):
    SPACE_HIGH = 0
    SPACE_MED = 1
    SPACE_LOW = 2
    GROUND_HIGH = 3
    GROUND_MED = 4
    GROUND_LOW = 5


# Checkbox states
# Subclassing from str as well as Enum means json.load and json.dump work seamlessly
class CheckStates(str, Enum):
    STATE_OFF = 'No'
    STATE_ON = 'Yes'
    STATE_PARTIAL = 'Partial'
    STATE_PENDING = 'Pending'


class Ticks(Enum):
    TICK_CURRENT = 0
    TICK_PREVIOUS = 1


class UpdateUIPolicy(Enum):
    NEVER = 0
    IMMEDIATE = 1
    LATER = 2


class DiscordChannel(Enum):
    BGS = 0
    FLEETCARRIER = 1
    THARGOIDWAR = 2


class MaterialsCategory(Enum):
    SELLING = 0
    BUYING = 1


class DiscordPostStyle(str, Enum):
    TEXT = 'Text'
    EMBED = 'Embed'


class DiscordActivity(str, Enum):
    BGS = 'BGS'
    THARGOIDWAR = 'TW'
    BOTH = 'Both'


class RequestMethod(Enum):
    GET = 'get'
    POST = 'post'
    PUT = 'put'
    DELETE = 'delete'
    HEAD = 'head'
    OPTIONS = 'options'


DATETIME_FORMAT_JOURNAL = "%Y-%m-%dT%H:%M:%SZ"
FOLDER_ASSETS = "assets"
FOLDER_DATA = "otherdata"
FOLDER_BACKUPS = "backups"
FOLDER_UPDATES = "updates"