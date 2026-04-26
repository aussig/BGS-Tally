import json
from os.path import join
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bgstally.bgstally import BGSTally

from bgstally.debug import Debug
from config import config

FILENAME_MARKET = "Market.json"

class Market:
    def __init__(self, bgstally: 'BGSTally'):
        self.bgstally: BGSTally = bgstally
        self.name:str|None = None
        self.id:int|None = None
        self.commodities:dict = {}


    def load(self) -> None:
        """
        Clear any existing data and load the latest market data
        """
        self.name = None
        self.id = None
        self.commodities = {}
        self._parse()


    def available(self, id:int) -> bool:
        """Return true if there is market data available matching the given market id

        Args:
            id (int): The Market ID to check

        Returns:
            bool: True if data available
        """
        if self.id != id: self.load()
        return self.id == id


    def _parse(self):
        """
        Load and parse the 'Market.json' file from the player journal folder
        """
        journal_dir:str = config.get_str('journaldir') or config.default_journal_dir
        if not journal_dir: return

        try:
            with open(join(journal_dir, FILENAME_MARKET), 'rb') as file:
                data:bytes = file.read().strip()
                if not data: return

                json_data = json.loads(data)
                self.name = json_data['StationName']
                self.id = json_data['MarketID']
                items:list = json_data['Items']

                for item in items:
                    item_name:str = item.get('Name', "")[1:-6] # Remove leading "$" and trailing "_name;"
                    if item_name == "": continue

                    self.commodities[item_name] = item

        except Exception as e:
            Debug.logger.info(f"Unable to load {FILENAME_MARKET} from the player journal folder")


    def get_commodity(self, name:str) -> dict:
        """Get the data for a commodity by name.

        Args:
            name (str): The non-localised commodity name, but without any leading "$" and trailing "_name;". i.e. "palladium" not "$palladium_name;"

        Returns:
            dict: A dictionary of commodity data, or an empty dictionary if not found
        """
        return self.commodities.get(name, {})
