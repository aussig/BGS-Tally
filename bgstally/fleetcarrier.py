import json
from datetime import datetime
from os import path, remove

from bgstally.constants import DATETIME_FORMAT_JOURNAL, FOLDER_DATA, DiscordChannel, FleetCarrierItemType
from bgstally.debug import Debug
from bgstally.discord import DATETIME_FORMAT
from thirdparty.colors import *
from bgstally.utils import get_by_path

FILENAME = "fleetcarrier.json"


class FleetCarrier:
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.data:dict = {}
        self.name:str = None
        self.callsign:str = None
        self.onfoot_mats_selling:list = []
        self.onfoot_mats_buying:list = []
        self.commodities_selling:list = []
        self.commodities_buying:list = []

        self.load()


    def load(self):
        """
        Load state from file
        """
        file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)
        if path.exists(file):
            try:
                with open(file) as json_file:
                    self._from_dict(json.load(json_file))
            except Exception as e:
                Debug.logger.info(f"Unable to load {file}")


    def save(self):
        """
        Save state to file
        """
        file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self._as_dict(), outfile)


    def available(self):
        """
        Return true if there is data available on a Fleet Carrier
        """
        return self.name is not None and self.callsign is not None


    def update(self, data: dict):
        """
        Store the latest data
        """
        # Data directly from CAPI response. Structure documented here:
        # https://github.com/Athanasius/fd-api/blob/main/docs/FrontierDevelopments-CAPI-endpoints.md#fleetcarrier

        # Store the whole data structure
        self.data = data

        Debug.logger.info(f"CAPI Carrier Update: {data}")


        # Name is encoded as hex string
        self.name = bytes.fromhex(self.data.get('name', {}).get('vanityName', "----")).decode('utf-8')
        self.callsign = self.data.get('name', {}).get('callsign', "----")

        # Sort microresource sell orders - a Dict of Dicts, or an empty list
        materials:dict|list = get_by_path(self.data, ['orders', 'onfootmicroresources', 'sales'], [])
        if materials is not None and type(materials) is dict and materials != {}:
            self.onfoot_mats_selling = sorted(materials.values(), key=lambda x: x['locName'])
        else:
            self.onfoot_mats_selling = []

        # Sort microresource buy orders - a List of Dicts
        materials = get_by_path(self.data, ['orders', 'onfootmicroresources', 'purchases'], [])
        if materials is not None and materials != []:
            self.onfoot_mats_buying = sorted(materials, key=lambda x: x['locName'])
        else:
            self.onfoot_mats_buying = []

        # Sort commodity sell orders - a List of Dicts
        commodities:list = get_by_path(self.data, ['orders', 'commodities', 'sales'], [])
        Debug.logger.info(f"Commodity sales: {commodities}")
        if commodities is not None and commodities != []:
            self.commodities_selling = sorted(commodities, key=lambda x: x['name'])
        else:
            self.commodities_selling = []

        # Sort commodity buy orders - a List of Dicts
        commodities = get_by_path(self.data, ['orders', 'commodities', 'purchases'], [])
        Debug.logger.info(f"Commodity purchases: {commodities}")
        if commodities is not None and commodities != []:
            self.commodities_buying = sorted(commodities, key=lambda x: x['name'])
        else:
            self.commodities_buying = []


    def stats_received(self, journal_entry: dict):
        """
        The user entered the carrier management screen
        """
        if self.name is None:
            self.name = journal_entry.get("Name")
            self.callsign = journal_entry.get("Callsign")
            self.data['dockingAccess'] = journal_entry.get("DockingAccess")


    def jump_requested(self, journal_entry: dict):
        """
        The user scheduled a carrier jump
        """
        # {"timestamp": "2020-04-20T09:30:58Z", "event": "CarrierJumpRequest", "CarrierID": 3700005632, "SystemName": "Paesui Xena", "Body": "Paesui Xena A", "SystemAddress": 7269634680241, "BodyID": 1, "DepartureTime":"2020-04-20T09:45:00Z"}

        title:str = f"Jump Scheduled for Carrier {self.name}"

        fields = []
        fields.append({'name': "From System", 'value': self.data.get('currentStarSystem', "Unknown"), 'inline': True})
        fields.append({'name': "To System", 'value': journal_entry.get('SystemName', "Unknown"), 'inline': True})
        fields.append({'name': "To Body", 'value': journal_entry.get('Body', "Unknown"), 'inline': True})
        fields.append({'name': "Departure Time", 'value': datetime.strptime(journal_entry.get('DepartureTime'), DATETIME_FORMAT_JOURNAL).strftime(DATETIME_FORMAT), 'inline': True})
        fields.append({'name': "Docking", 'value': self.human_format_dockingaccess(), 'inline': True})
        fields.append({'name': "Notorious Access", 'value': self.human_format_notorious(), 'inline': True})

        self.bgstally.discord.post_embed(title, "A carrier jump has been scheduled", fields, None, DiscordChannel.FLEETCARRIER_OPERATIONS, None)


    def jump_cancelled(self):
        """
        The user cancelled their carrier jump
        """
        title:str = f"Jump Cancelled for Carrier {self.name}"

        fields = []
        fields.append({'name': "Current System", 'value': self.data.get('currentStarSystem', "Unknown"), 'inline': True})
        fields.append({'name': "Docking", 'value': self.human_format_dockingaccess(), 'inline': True})
        fields.append({'name': "Notorious Access", 'value': self.human_format_notorious(), 'inline': True})

        self.bgstally.discord.post_embed(title, "The scheduled carrier jump was cancelled", fields, None, DiscordChannel.FLEETCARRIER_OPERATIONS, None)


    def trade_order(self, journal_entry: dict):
        """
        The user set a buy or sell order

        Args:
            journal_entry (dict): The journal entry data
        """

        # { "timestamp":"2024-02-17T16:33:10Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"imperialslaves", "Commodity_Localised":"Imperial Slaves", "SaleOrder":10, "Price":1749300 }
        # { "timestamp":"2024-02-17T16:33:51Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"unstabledatacore", "Commodity_Localised":"Unstable Data Core", "PurchaseOrder":5, "Price":4516 }
        # { "timestamp":"2024-02-17T16:35:57Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"unstabledatacore", "Commodity_Localised":"Unstable Data Core", "CancelTrade":true }

        if journal_entry.get('SaleOrder') is not None:
            self._update_item(journal_entry.get('Commodity'), int(journal_entry.get('SaleOrder', 0)), int(journal_entry.get('Price', 0)), FleetCarrierItemType.COMMODITIES_SELLING)
            self._update_item(journal_entry.get('Commodity'), 0, 0, FleetCarrierItemType.COMMODITIES_BUYING)
        elif journal_entry.get('PurchaseOrder') is not None:
            self._update_item(journal_entry.get('Commodity'), 0, 0, FleetCarrierItemType.COMMODITIES_SELLING)
            self._update_item(journal_entry.get('Commodity'), int(journal_entry.get('PurchaseOrder', 0)), int(journal_entry.get('Price', 0)), FleetCarrierItemType.COMMODITIES_BUYING)
        elif journal_entry.get('CancelTrade') == True:
            self._update_item(journal_entry.get('Commodity'), 0, 0, FleetCarrierItemType.COMMODITIES_SELLING)
            self._update_item(journal_entry.get('Commodity'), 0, 0, FleetCarrierItemType.COMMODITIES_BUYING)


    def get_items_plaintext(self, category: FleetCarrierItemType = None):
        """
        Return a list of formatted materials for posting to Discord
        """
        result:str = ""
        items, name_key, quantity_key = self._get_items(category)

        if items is None: return ""

        for item in items:
            if int(item[quantity_key]) > 0: result += f"{item[name_key]} x {item[quantity_key]} @ {self._human_format_price(item['price'])}\n"

        return result


    def get_items_discord(self, category: FleetCarrierItemType = None) -> str:
        """
        Return a list of formatted materials for posting to Discord
        """
        result:str = ""
        items, name_key, quantity_key = self._get_items(category)

        if items is None: return ""

        for item in items:
            if int(item[quantity_key]) > 0: result += f"{cyan(item[name_key])} x {green(item[quantity_key])} @ {red(self._human_format_price(item['price']))}\n"

        return result


    def _update_item(self, name: str, quantity: int, price: int, category: FleetCarrierItemType):

        items, name_key, quantity_key = self._get_items(category)
        if items is None: return

        # items is returned as reference, so we are directly manipulating the appropriate list
        found:bool = False
        for item in items:
            if item[name_key] == name:
                item[quantity_key] = quantity
                item['price'] = price
                found = True
                break

        if not found:
            items.append(
                {
                    name_key: name,
                    quantity_key: quantity,
                    'price': price
                }
            )


    def human_format_dockingaccess(self) -> str:
        """
        Get the docking access in human-readable format
        """
        match (self.data.get('dockingAccess')):
            case "all": return "All"
            case "squadronfriends": return "Squadron and Friends"
            case "friends": return "Friends"
            case _: return "None"


    def human_format_notorious(self) -> str:
        """
        Get the notorious access in human-readable format
        """
        return 'Yes' if self.data.get('notoriousAccess', False) else 'No'


    def _human_format_price(self, num) -> str:
        """
        Format a BGS value into shortened human-readable text
        """
        num = float('{:.3g}'.format(float(num)))
        magnitude = 0
        while abs(num) >= 1000:
            magnitude += 1
            num /= 1000.0
        return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])


    def _get_items(self, category: FleetCarrierItemType = None) -> tuple[list|None, str|None, str|None]:
        """
        Return the items list, name key and quantity key for the specified category
        """
        match category:
            case FleetCarrierItemType.MATERIALS_SELLING:
                return self.onfoot_mats_selling, 'locName', 'stock'
            case FleetCarrierItemType.MATERIALS_BUYING:
                return self.onfoot_mats_buying, 'locName', 'outstanding'
            case FleetCarrierItemType.COMMODITIES_SELLING:
                return self.commodities_selling, 'name', 'stock'
            case FleetCarrierItemType.COMMODITIES_BUYING:
                return self.commodities_buying, 'name', 'outstanding'
            case _:
                return None, None, None


    def _as_dict(self):
        """
        Return a Dictionary representation of our data, suitable for serializing
        """
        return {
            'name': self.name,
            'callsign': self.callsign,
            'onfoot_mats_selling': self.onfoot_mats_selling,
            'onfoot_mats_buying': self.onfoot_mats_buying,
            'commodities_selling': self.commodities_selling,
            'commodities_buying': self.commodities_buying,
            'data': self.data}


    def _from_dict(self, dict: dict):
        """
        Populate our data from a Dictionary that has been deserialized
        """
        self.name = dict.get('name')
        self.callsign = dict.get('callsign')
        self.onfoot_mats_selling = dict.get('onfoot_mats_selling', [])
        self.onfoot_mats_buying = dict.get('onfoot_mats_buying', [])
        self.commodities_selling = dict.get('commodities_selling', [])
        self.commodities_buying = dict.get('commodities_buying', [])
        self.data = dict.get('data')
