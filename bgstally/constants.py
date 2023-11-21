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
    CMDR_INFORMATION = 1
    FLEETCARRIER_MATERIALS = 2
    FLEETCARRIER_OPERATIONS = 3
    THARGOIDWAR = 4


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
    PATCH = 'patch'
    DELETE = 'delete'
    HEAD = 'head'
    OPTIONS = 'options'


DATETIME_FORMAT_JOURNAL = "%Y-%m-%dT%H:%M:%SZ"
FILE_SUFFIX = ".json"
FOLDER_ASSETS = "assets"
FOLDER_DATA = "otherdata"
FOLDER_BACKUPS = "backups"
FOLDER_UPDATES = "updates"
FONT_HEADING_1:tuple = ("Helvetica", 13, "bold")
FONT_HEADING_2:tuple = ("Helvetica", 11, "bold")
FONT_TEXT:tuple = ("Helvetica", 11, "normal")
FONT_TEXT_BOLD:tuple = ("Helvetica", 11, "bold")
FONT_TEXT_UNDERLINE:tuple = ("Helvetica", 11, "underline")
FONT_TEXT_BOLD_UNDERLINE:tuple = ("Helvetica", 11, "bold underline")
FONT_SMALL:tuple = ("Helvetica", 9, "normal")
COLOUR_HEADING_1 = "#A300A3"
