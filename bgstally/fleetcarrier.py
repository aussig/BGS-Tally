import csv
import json
from datetime import datetime
from os import path, remove

from bgstally.constants import DATETIME_FORMAT_JOURNAL, FOLDER_DATA, FOLDER_OTHER_DATA, DiscordChannel, FleetCarrierItemType
from bgstally.debug import Debug
from bgstally.discord import DATETIME_FORMAT
from bgstally.utils import _, __, get_by_path
from thirdparty.colors import *

FILENAME = "fleetcarrier.json"
COMMODITIES_CSV_FILENAME = "commodity.csv"
RARE_COMMODITIES_CSV_FILENAME = "rare_commodity.csv"


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
        self.commodities:dict = {}

        self._load_commodities()
        self.load()


    def load(self):
        """
        Load state from file
        """
        file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
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
        file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
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
        # https://github.com/EDCD/FDevIDs/blob/master/Frontier%20API/FrontierDevelopments-CAPI-endpoints.md#fleetcarrier

        # Store the whole data structure
        self.data = data

        # Name is encoded as hex string
        self.name = bytes.fromhex(get_by_path(self.data, ['name', 'vanityName'], "----")).decode('utf-8')
        self.callsign = get_by_path(self.data, ['name', 'callsign'], "----")

        # Sort microresource sell orders - a Dict of Dicts, or an empty list
        materials:dict|list = get_by_path(self.data, ['orders', 'onfootmicroresources', 'sales'], [])
        if materials is not None and type(materials) is dict and materials != {}:
            self.onfoot_mats_selling = list(materials.values())
        else:
            self.onfoot_mats_selling = []

        # Sort microresource buy orders - a List of Dicts
        materials = get_by_path(self.data, ['orders', 'onfootmicroresources', 'purchases'], [])
        if materials is not None and materials != []:
            self.onfoot_mats_buying = materials
        else:
            self.onfoot_mats_buying = []

        # Sort commodity sell orders - a List of Dicts
        commodities:list = get_by_path(self.data, ['orders', 'commodities', 'sales'], [])
        if commodities is not None and commodities != []:
            self.commodities_selling = commodities
        else:
            self.commodities_selling = []

        # Sort commodity buy orders - a List of Dicts
        commodities = get_by_path(self.data, ['orders', 'commodities', 'purchases'], [])
        if commodities is not None and commodities != []:
            self.commodities_buying = commodities
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

        title:str = __("Jump Scheduled for Carrier {carrier_name}", lang=self.bgstally.state.discord_lang).format(carrier_name=self.name) # LANG: Discord post title
        description:str = __("A carrier jump has been scheduled", lang=self.bgstally.state.discord_lang) # LANG: Discord text

        fields = []
        fields.append({'name': __("From System", lang=self.bgstally.state.discord_lang), 'value': self.data.get('currentStarSystem', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("To System", lang=self.bgstally.state.discord_lang), 'value': journal_entry.get('SystemName', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("To Body", lang=self.bgstally.state.discord_lang), 'value': journal_entry.get('Body', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("Departure Time", lang=self.bgstally.state.discord_lang), 'value': datetime.strptime(journal_entry.get('DepartureTime'), DATETIME_FORMAT_JOURNAL).strftime(DATETIME_FORMAT), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("Docking", lang=self.bgstally.state.discord_lang), 'value': self.human_format_dockingaccess(True), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("Notorious Access", lang=self.bgstally.state.discord_lang), 'value': self.human_format_notorious(True), 'inline': True}) # LANG: Discord heading

        self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_OPERATIONS, None)


    def jump_cancelled(self):
        """
        The user cancelled their carrier jump
        """
        title:str = __("Jump Cancelled for Carrier {carrier_name}", lang=self.bgstally.state.discord_lang).format(carrier_name=self.name) # LANG: Discord post title
        description:str = __("The scheduled carrier jump was cancelled", lang=self.bgstally.state.discord_lang) # LANG: Discord text

        fields = []
        fields.append({'name': __("Current System", lang=self.bgstally.state.discord_lang), 'value': self.data.get('currentStarSystem', "Unknown"), 'inline': True})
        fields.append({'name': __("Docking", lang=self.bgstally.state.discord_lang), 'value': self.human_format_dockingaccess(True), 'inline': True})
        fields.append({'name': __("Notorious Access", lang=self.bgstally.state.discord_lang), 'value': self.human_format_notorious(True), 'inline': True})

        self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_OPERATIONS, None)


    def trade_order(self, journal_entry: dict):
        """
        The user set a buy or sell order

        Args:
            journal_entry (dict): The journal entry data
        """

        # { "timestamp":"2024-02-17T16:33:10Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"imperialslaves", "Commodity_Localised":"Imperial Slaves", "SaleOrder":10, "Price":1749300 }
        # { "timestamp":"2024-02-17T16:33:51Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"unstabledatacore", "Commodity_Localised":"Unstable Data Core", "PurchaseOrder":5, "Price":4516 }
        # { "timestamp":"2024-02-17T16:35:57Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"unstabledatacore", "Commodity_Localised":"Unstable Data Core", "CancelTrade":true }

        item_name:str = journal_entry.get('Commodity', "").lower()

        if item_name in self.commodities:
            # The order is for a commodity. Note we pass the item_name as the display name because Commodity_Localised is not always present for commodities,
            # and anyway we don't get localised names in CAPI data so generally they are not present. So, we look display name up later for commodities.
            if journal_entry.get('SaleOrder') is not None:
                self._update_item(item_name, item_name, int(journal_entry.get('SaleOrder', 0)), int(journal_entry.get('Price', 0)), FleetCarrierItemType.COMMODITIES_SELLING)
                self._update_item(item_name, item_name, 0, 0, FleetCarrierItemType.COMMODITIES_BUYING)
            elif journal_entry.get('PurchaseOrder') is not None:
                self._update_item(item_name, item_name, 0, 0, FleetCarrierItemType.COMMODITIES_SELLING)
                self._update_item(item_name, item_name, int(journal_entry.get('PurchaseOrder', 0)), int(journal_entry.get('Price', 0)), FleetCarrierItemType.COMMODITIES_BUYING)
            elif journal_entry.get('CancelTrade') == True:
                self._update_item(item_name, item_name, 0, 0, FleetCarrierItemType.COMMODITIES_SELLING)
                self._update_item(item_name, item_name, 0, 0, FleetCarrierItemType.COMMODITIES_BUYING)
        else:
            # The order is for a material.
            item_display_name:str = journal_entry.get('Commodity_Localised', "")
            if journal_entry.get('SaleOrder') is not None:
                self._update_item(item_name, item_display_name, int(journal_entry.get('SaleOrder', 0)), int(journal_entry.get('Price', 0)), FleetCarrierItemType.MATERIALS_SELLING)
                self._update_item(item_name, item_display_name, 0, 0, FleetCarrierItemType.MATERIALS_BUYING)
            elif journal_entry.get('PurchaseOrder') is not None:
                self._update_item(item_name, item_display_name, 0, 0, FleetCarrierItemType.MATERIALS_SELLING)
                self._update_item(item_name, item_display_name, int(journal_entry.get('PurchaseOrder', 0)), int(journal_entry.get('Price', 0)), FleetCarrierItemType.MATERIALS_BUYING)
            elif journal_entry.get('CancelTrade') == True:
                self._update_item(item_name, item_display_name, 0, 0, FleetCarrierItemType.MATERIALS_SELLING)
                self._update_item(item_name, item_display_name, 0, 0, FleetCarrierItemType.MATERIALS_BUYING)


    def get_items_plaintext(self, category: FleetCarrierItemType|None = None) -> str:
        """Return a multiline text string containing all items of a given type

        Args:
            category (FleetCarrierItemType | None, optional): The item type to fetch. Defaults to None.

        Returns:
            str: _description_
        """
        result: str = ""
        items, name_key, display_name_key, quantity_key = self._get_items(category)

        if items is None: return ""
        items = sorted(items, key=lambda x: x[name_key])

        for item in items:
            if category == FleetCarrierItemType.COMMODITIES_BUYING or category == FleetCarrierItemType.COMMODITIES_SELLING:
                # Look up the display name because we don't have it in CAPI data
                display_name: str = self.commodities[item[name_key]]
            else:
                # Use the localised name from CAPI data
                display_name: str = item[display_name_key]

            if int(item[quantity_key]) > 0: result += f"{display_name} x {item[quantity_key]} @ {self._human_format_price(item['price'])}\n"

        return result


    def get_items_discord(self, category: FleetCarrierItemType = None) -> str:
        """
        Return a list of formatted items for posting to Discord
        """
        result:str = ""
        items, name_key, display_name_key, quantity_key = self._get_items(category)

        if items is None: return ""
        items = sorted(items, key=lambda x: x[name_key])

        for item in items:
            if category == FleetCarrierItemType.COMMODITIES_BUYING or category == FleetCarrierItemType.COMMODITIES_SELLING:
                # Look up the display name because we don't have it in CAPI data
                display_name:str = self.commodities[item[name_key]]
            else:
                # Use the localised name from CAPI data
                display_name:str = item[display_name_key]

            if int(item[quantity_key]) > 0: result += f"{cyan(display_name)} x {green(item[quantity_key])} @ {red(self._human_format_price(item['price']))}\n"

        return result



    def _update_item(self, name: str, display_name: str, quantity: int, price: int, category: FleetCarrierItemType):
        """
        Update the buy order or sell order for a commodity or material

        Args:
            name (str): The name of the item, this is the key used to look up the item
            quantity (int): The quantity of the order
            price (int): The price of the order
            category (FleetCarrierItemType): The type of item and order
        """
        items, name_key, display_name_key, quantity_key = self._get_items(category)
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
                    display_name_key: display_name,
                    quantity_key: quantity,
                    'price': price
                }
            )


    def human_format_dockingaccess(self, discord:bool) -> str:
        """
        Get the docking access in human-readable format
        """
        match (self.data.get('dockingAccess')):
            case "all":
                if discord: return __("All", lang=self.bgstally.state.discord_lang) # LANG: Discord carrier docking access
                else: return _("All") # LANG: Carrier docking access
            case "squadronfriends":
                if discord: return __("Squadron and Friends", lang=self.bgstally.state.discord_lang) # LANG: Discord carrier docking access
                else: return _("Squadron and Friends") # LANG: Carrier docking access
            case "friends":
                if discord: return __("Friends", lang=self.bgstally.state.discord_lang) # LANG: Discord carrier docking access
                else: return _("Friends") # LANG: Carrier docking access
            case _:
                if discord: return __("None", lang=self.bgstally.state.discord_lang) # LANG: Discord carrier docking access
                else: return _("None") # LANG: Carrier docking access


    def human_format_notorious(self, discord:bool) -> str:
        """
        Get the notorious access in human-readable format
        """
        if self.data.get('notoriousAccess', False):
            return __("Yes", lang=self.bgstally.state.discord_lang) if discord else _("Yes")
        else:
            return __("No", lang=self.bgstally.state.discord_lang) if discord else _("No")


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


    def _get_items(self, category: FleetCarrierItemType = None) -> tuple[list|None, str|None, str|None, str|None]:
        """Return the current items list, lookup name key, display name key and quantity key for the specified category

        Args:
            category (FleetCarrierItemType, optional): The type of item to fetch. Defaults to None.

        Returns:
            tuple[list|None, str|None, str|None, str|None]: Tuple containing the four items
        """
        match category:
            case FleetCarrierItemType.MATERIALS_SELLING:
                return self.onfoot_mats_selling, 'name', 'locName', 'stock'
            case FleetCarrierItemType.MATERIALS_BUYING:
                return self.onfoot_mats_buying, 'name', 'locName', 'outstanding'
            case FleetCarrierItemType.COMMODITIES_SELLING:
                # Lookup name and display name are the same for commodities as we are not passed localised name from CAPI. We
                # convert the display name later
                return self.commodities_selling, 'name', 'name', 'stock'
            case FleetCarrierItemType.COMMODITIES_BUYING:
                # Lookup name and display name are the same for commodities as we are not passed localised name from CAPI. We
                # convert the display name later
                return self.commodities_buying, 'name', 'name', 'outstanding'
            case _:
                return None, None, None, None


    def _load_commodities(self):
        """
        Load the CSV file containing full list of commodities. For our purposes, we build a dict where the key is the commodity
        internal name from the 'symbol' column in the CSV, lowercased, and the value is the localised name. As we are not passed
        localised names for commodities in the CAPI data, this allows us to show nice human-readable commodity names (always in English though).

        The CSV file is sourced from the EDCD FDevIDs project https://github.com/EDCD/FDevIDs and should be updated occasionally
        """
        filepath:str = path.join(self.bgstally.plugin_dir, FOLDER_DATA, COMMODITIES_CSV_FILENAME)
        self.commodities = {}

        try:
            with open(filepath, encoding = 'utf-8') as csv_file_handler:
                csv_reader = csv.DictReader(csv_file_handler)

                for rows in csv_reader:
                    self.commodities[rows.get('symbol', "").lower()] = rows.get('name', "")
        except Exception as e:
                Debug.logger.error(f"Unable to load {filepath}")
        
        rare_filepath:str = path.join(self.bgstally.plugin_dir, FOLDER_DATA, RARE_COMMODITIES_CSV_FILENAME)
        try:
            with open(rare_filepath, encoding = 'utf-8') as csv_file_handler:
                csv_reader = csv.DictReader(csv_file_handler)

                for rows in csv_reader:
                    self.commodities[rows.get('symbol', "").lower()] = rows.get('name', "")
        except Exception as e:
                Debug.logger.error(f"Unable to load {rare_filepath}")


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
