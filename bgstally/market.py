import json
from os.path import join
from typing import Dict, List

from bgstally.debug import Debug
from config import config

FILENAME_MARKET = "Market.json"

class Market:
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.name:str = None
        self.id:int = None
        self.commodities:Dict = {}


    def load(self):
        """
        Clear any existing data and load the latest market data
        """
        self.name = None
        self.id = None
        self.commodities = {}
        self._parse()


    def available(self, id:int) -> bool:
        """
        Return true if there is market data available matching the given market id
        """
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
                items:List = json_data['Items']

                for item in items:
                    item_name:str = item.get('Name', "")[1:-6] # Remove leading "$" and trailing "_name;"
                    if item_name == "": continue

                    self.commodities[item_name] = item

        except Exception as e:
            Debug.logger.info(f"Unable to load {FILENAME_MARKET} from the player journal folder")


    def get_commodity(self, name:str) -> Dict | None:
        """
        Get the data for a commodity by name. 'name' is the non-localised commodity name, but without
        any leading "$" and trailing "_name;". i.e. "palladium" not "$palladium_name;".
        """
        return self.commodities[name] | {}
