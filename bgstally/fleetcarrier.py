import json
from datetime import UTC, datetime
from os import path, remove

from bgstally.constants import DATETIME_FORMAT_JOURNAL, FOLDER_OTHER_DATA, DiscordChannel, FleetCarrierItemType
from bgstally.debug import Debug
from bgstally.discord import DATETIME_FORMAT
from bgstally.utils import _, __, get_by_path
from thirdparty.colors import *

FILENAME = "fleetcarrier.json"


class FleetCarrier:
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.carrier_id:int = None
        self.data:dict = {}
        self.name:str = None
        self.callsign:str = None
        self.onfoot_mats_selling:list = []
        self.onfoot_mats_buying:list = []
        self.commodities_selling:list = []
        self.commodities_buying:list = []
        self.cargo:list = []
        self.locker:dict = {}

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
        self.carrier_id = get_by_path(self.data, ['market', 'id'], "")

        # Sort microresource sell orders - a Dict of Dicts, or an empty list
        materials:dict|list = get_by_path(self.data, ['orders', 'onfootmicroresources', 'sales'], [])
        if materials is not None and type(materials) is dict and materials != {}:
            self.onfoot_mats_selling = list(materials.values())
        else:
            self.onfoot_mats_selling = []

        # Sort microresource buy orders - a List of Dicts
        materials:dict|list = get_by_path(self.data, ['orders', 'onfootmicroresources', 'purchases'], [])
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
        commodities:list = get_by_path(self.data, ['orders', 'commodities', 'purchases'], [])
        if commodities is not None and commodities != []:
            self.commodities_buying = commodities
        else:
            self.commodities_buying = []

        # Sort cargo commodities - a List of Dicts
        cargo:list = get_by_path(self.data, ['cargo'], [])
        if cargo is not None and cargo != []:
            self.cargo = cargo
        else:
            self.cargo = []

        # Sort locker materials
        locker:dict|list = get_by_path(self.data, ['carrierLocker'], [])
        if locker is not None and locker != []:
            self.locker = locker
        else:
            self.locker = []


    def stats_received(self, journal_entry: dict):
        """
        The user entered the carrier management screen
        """
        if self.name is None:
            self.name = journal_entry.get('Name', "")
            self.callsign = journal_entry.get('Callsign', "")
            self.carrier_id = journal_entry.get('CarrierID', "")
            self.data['dockingAccess'] = journal_entry.get('DockingAccess', "")


    def jump_requested(self, journal_entry: dict[str, str]):
        """
        The user scheduled a carrier jump
        """
        # {"timestamp": "2020-04-20T09:30:58Z", "event": "CarrierJumpRequest", "CarrierID": 3700005632, "SystemName": "Paesui Xena", "Body": "Paesui Xena A", "SystemAddress": 7269634680241, "BodyID": 1, "DepartureTime":"2020-04-20T09:45:00Z"}

        title:str = __("Jump Scheduled for Carrier {carrier_name}", lang=self.bgstally.state.discord_lang).format(carrier_name=self.name) # LANG: Discord post title
        description:str = __("A carrier jump has been scheduled", lang=self.bgstally.state.discord_lang) # LANG: Discord text

        departure_datetime: datetime|None = datetime.strptime(journal_entry.get('DepartureTime', ""), DATETIME_FORMAT_JOURNAL)
        departure_datetime = departure_datetime.replace(tzinfo=UTC)

        fields = []
        fields.append({'name': __("From System", lang=self.bgstally.state.discord_lang), 'value': self.data.get('currentStarSystem', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("To System", lang=self.bgstally.state.discord_lang), 'value': journal_entry.get('SystemName', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("To Body", lang=self.bgstally.state.discord_lang), 'value': journal_entry.get('Body', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("Departure Time", lang=self.bgstally.state.discord_lang), 'value': f"<t:{round(departure_datetime.timestamp())}:R>"}) # LANG: Discord heading
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


    def cargo_transfer(self, journal_entry: dict):
        """
        The user transferred cargo to or from the carrier

        Args:
            journal_entry (dict): The journal entry data
        """
        # { "timestamp":"2025-03-22T15:15:21Z", "event":"CargoTransfer", "Transfers":[ { "Type":"steel", "Count":728, "Direction":"toship" }, { "Type":"titanium", "Count":56, "Direction":"toship" } ] }

        # Unfortunately we don't get the localized name for transfers so we'll do without.
        cargo, name_key, display_name_key, quantity_key = self._get_items(FleetCarrierItemType.CARGO)
        for i in journal_entry.get('Transfers', []):
            type:str = i.get('Type', "").lower()
            display_type:str = i.get('Type_Localised', "")
            if display_type == "" and type in self.bgstally.ui.commodities:
                display_type = self.bgstally.ui.commodities[type]['Name']

            count:int = i.get('Count', 0)
            direction:str = i.get('Direction', "")

            found = False
            for c in cargo:
                # For some reason the event is lower case but the cargo is mixed case
                if count > 0 and c[name_key].lower() == type:
                    found = True
                    if direction == "toship":
                        if c[quantity_key] > count: # May have to do this in multiple bits.
                            c[quantity_key] -= count
                            count = 0
                            break
                        else:
                            count -= c[quantity_key]
                            cargo.remove(c)

                    else:
                        c[quantity_key] += count
                        count = 0
                        break

            if not found:
                cargo.append({name_key: type, display_name_key: display_type, quantity_key: count})


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
        self.carrier_id = journal_entry.get('CarrierID')
        if item_name in self.bgstally.ui.commodities:
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


    def cargo_transfer(self, journal_entry: dict):
        """
        The user transferred cargo to or from the carrier.

        We shouldn't do this. If the EDMC CAPI cooldown worked properly we'd just query the CAPI and get the accurate data!

        Args:
            journal_entry (dict): The journal entry data
        """
        # { "timestamp":"2025-03-22T15:15:21Z", "event":"CargoTransfer", "Transfers":[ { "Type":"steel", "Count":728, "Direction":"toship" }, { "Type":"titanium", "Count":56, "Direction":"toship" } ] }

        # Unfortunately we don't get the localized name for transfers so we'll do without.
        cargo, name_key, display_name_key, quantity_key = self._get_items(FleetCarrierItemType.CARGO)
        for i in journal_entry.get('Transfers', []):
            type:str = i.get('Type', "")
            display_type:str = i.get('Type_Localised', "")
            if display_type == "" and type in self.commodities:
                display_type = self.commodities[type]

            count:int = i.get('Count', 0)
            direction:str = i.get('Direction', "")

            found = False
            for c in cargo:
                # For some reason the event is lower case but the cargo is mixed case
                if count > 0 and c[name_key].lower() == type:
                    found = True
                    if direction == "toship":
                        if c[quantity_key] > count: # May have to do this in multiple bits.
                            c[quantity_key] -= count
                            count = 0
                            break
                        else:
                            count -= c[quantity_key]
                            cargo.remove(c)

                    else:
                        c[quantity_key] += count
                        count = 0
                        break

            if not found:
                cargo.append({name_key: type, display_name_key: display_type, quantity_key: count})


   def market_activity(self, journal_entry:dict):
        '''
        We bought or sold to/from our carrier
        '''
        if journal_entry.get('MarketID') != self.carrier_id: # Not buying from us.
            return

        cargo, name_key, display_name_key, quantity_key = self._get_items(FleetCarrierItemType.CARGO)
        type:str = journal_entry.get('Type', "")
        count:int = journal_entry.get('Count', 0)

        for c in cargo:
            # For some reason the event is lower case but the cargo is mixed case
            if c[name_key].lower() == type:
                found = True
                if journal_entry.get('event') == "MarketBuy":
                    if c[quantity_key] > count: # May have to do this in multiple bits.
                        c[quantity_key] -= count
                        count = 0
                        break
                    else:
                        count -= c[quantity_key]
                        cargo.remove(c)

                else:
                    c[quantity_key] += count
                    count = 0
                    break

        if not found:
            cargo.append({name_key: type, display_name_key: self.bgstally.ui.commodities[type]['Name'], quantity_key: count})


    def get_items_plaintext(self, category: FleetCarrierItemType|None = None) -> str:
        """Return a multiline text string containing all items of a given type

        Args:
            category (FleetCarrierItemType | None, optional): The item type to fetch. Defaults to None.

        Returns:
            str: _description_
        """

        items, name_key, display_name_key, quantity_key = self._get_items(category)
        if items is None: return ""

        result: str = ""

        if category == FleetCarrierItemType.CARGO:
            # Cargo is a special case because it can have multiple items with the same name so we have to sum them together
            cargo = dict()
            items = sorted(items, key=lambda x: x[name_key])

            for item in items:
                # No longer prioritise the display name from CAPI data, as now that we have localised commodity names, we do a lookup first.
                # This allows us to translate to the EDMC language rather than the (limited set of) game languages.
                if item[name_key].lower() in self.bgstally.ui.commodities:
                    display_name:str = self.bgstally.ui.commodities[item[name_key].lower()]['Name']
                elif display_name_key in item:
                    # No translation, fall back to display name from CAPI data
                    display_name:str = item[display_name_key]
                else:
                    # No CAPI display name, fall back to the item name (which may not have spaces)
                    display_name:str = item[name_key]

                if display_name in cargo:
                    cargo[display_name] += int(item[quantity_key])
                else:
                    cargo[display_name] = int(item[quantity_key])
            for key, value in cargo.items():
                result += f"{key} x {value}\n"

        elif category == FleetCarrierItemType.LOCKER:
            # Locker is a special case because it's sub-divided into types
            for type in items:
                result += f"{type.title()}:\n"
                items[type] = sorted(items[type], key=lambda x: x[display_name_key])
                for item in items[type]:
                    if int(item[quantity_key]) > 0: # This one includes zero quantities for some reason
                        result += f"    {item[display_name_key]} x {item[quantity_key]}\n"

        else:
            items = sorted(items, key=lambda x: x[name_key])
            for item in items:
                # No longer prioritise the display name from CAPI data, as now that we have localised commodity names, we do a lookup first.
                # This allows us to translate to the EDMC language rather than the (limited set of) game languages.
                if item[name_key].lower() in self.bgstally.ui.commodities:
                    display_name:str = self.bgstally.ui.commodities[item[name_key].lower()]['Name']
                elif display_name_key in item:
                    # No translation, fall back to display name from CAPI data
                    display_name:str = item[display_name_key]
                else:
                    # No CAPI display name, fall back to the item name (which may not have spaces)
                    display_name:str = item[name_key]

                if int(item[quantity_key]) > 0:
                    result += f"{display_name} x {item[quantity_key]} @ {self._human_format_price(item['price'])}\n"

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


    def _get_items(self, category: FleetCarrierItemType = None) -> tuple[list|dict|None, str|None, str|None, str|None]:
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
                return self.commodities_selling, 'name', 'locName', 'stock'
            case FleetCarrierItemType.COMMODITIES_BUYING:
                # Lookup name and display name are the same for commodities as we are not passed localised name from CAPI. We
                # convert the display name later
                return self.commodities_buying, 'name', 'locName', 'outstanding'
            case FleetCarrierItemType.CARGO:
                # Return cargo items
                return self.cargo, 'commodity', 'locName', 'qty'
            case FleetCarrierItemType.LOCKER:
                # Return locker items
                return self.locker, 'name', 'locName', 'quantity'
            case _:
                return None, None, None, None


    def _as_dict(self):
        """
        Return a Dictionary representation of our data, suitable for serializing
        """
        return {
            'name': self.name,
            'callsign': self.callsign,
            'carrier_id': self.carrier_id,
            'onfoot_mats_selling': self.onfoot_mats_selling,
            'onfoot_mats_buying': self.onfoot_mats_buying,
            'commodities_selling': self.commodities_selling,
            'commodities_buying': self.commodities_buying,
            'cargo': self.cargo,
            'locker': self.locker,
            'data': self.data}


    def _from_dict(self, dict: dict):
        """
        Populate our data from a Dictionary that has been deserialized
        """
        self.name = dict.get('name')
        self.callsign = dict.get('callsign')
        self.carrier_id = dict.get('carrier_id')
        self.onfoot_mats_selling = dict.get('onfoot_mats_selling', [])
        self.onfoot_mats_buying = dict.get('onfoot_mats_buying', [])
        self.commodities_selling = dict.get('commodities_selling', [])
        self.commodities_buying = dict.get('commodities_buying', [])
        self.cargo = dict.get('cargo', [])
        self.locker = dict.get('locker', [])
        self.data = dict.get('data')
