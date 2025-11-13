import json
from datetime import UTC, datetime
import time
from os import path, remove
from copy import deepcopy

from bgstally.constants import DATETIME_FORMAT_JOURNAL, FOLDER_OTHER_DATA, KEY_CARRIER_TYPE, DiscordChannel, FleetCarrierItemType, FleetCarrierType
from bgstally.debug import Debug
from bgstally.discord import DATETIME_FORMAT
from bgstally.utils import _, __, get_by_path, catch_exceptions
from thirdparty.colors import *

FILENAME = "fleetcarrier.json"

class FleetCarrier:
    def __init__(self, bgstally):
        self.bgstally:BGSTally = bgstally # type: ignore

        # CAPI data is only received periodically and can be out of date so we take a copy of what we need and store it here.
        self.carrier_id:int = 0
        self.summary:dict = {}
        self.data:dict = {}
        self.locker:dict = {}
        self.cargo:dict = {}
        self.last_modified:int = 0

        self.readable:dict = {"all": "All", "squadronfriends": "Squadron and Friends", "friends" : "Friends",
                              "normalOperation": "Normal", "debtState": "Offline", "pendingDecommission": "Decommissioning",
                              "SearchAndRescue": "Search and Rescue", "Mining": "Miner", "Trader" : "Trader", "Explorer" : "Explorer",
                              "AntiXeno": "Xeno Hunter", "BountyHunter": "Bounty Hunter"
                             }

        self.load()


    def available(self) -> bool:
        """ Return true if there is data available on a Fleet Carrier """
        return self.summary.get('name', None) is not None and self.summary.get('callsign', None) is not None


    def get_summary(self) -> dict:
        """ Return the carrier summary """

        itinerary = get_by_path(self.data, ['itinerary', 'completed'], [])
        if len(itinerary) > 0:
            arrival = itinerary[-1].get('arrivalTime', "")

        Debug.logger.debug(f"Balance {get_by_path(self.data, ['finance', 'bankBalance'], 0)}")
        return {
            _('Name'): self.summary['name'],                                    # LANG: Carrier summary
            _('System'): self.summary['currentStarSystem'],                     # LANG: Carrier summary
            _('Docking'): self._readable(self.summary['dockingAccess'], False), # LANG: Carrier summary
            _('Operation'): self._readable(self.summary['state'], False),      # LANG: Carrier summary
            _('Fuel'): int(self.summary['fuel']),                              # LANG: Carrier summary

            _('Callsign'): self.summary['callsign'],                            # LANG: Carrier summary
            _('Arrival'): arrival,                              # LANG: Carrier summary
            _('Allow Notorious'): self.summary['notoriousAccess'], # LANG: Carrier summary
            _('Theme'): self._readable(self.summary['theme'], False),          # LANG: Carrier summary
            _('Space'): self.summary['freeSpace'], # LANG: Spare capacity

            _('Balance'): self.summary['bankBalance'],# LANG: Carrier summary
            _('Reserve'): self.summary['bankReservedBalance'],   # LANG: Carrier summary
            _('Maintenance'): self.summary['maintenance'],   # LANG: Carrier summary
            _('Jumps'): int(self.summary['numJumps']),   # LANG: Carrier summary
            _('Tax Level'): f"{self.summary['taxation']}%",   # LANG: Carrier debt limit
        }


    def get_services(self) -> dict:
        """ Return services as a dictionary """
        services:dict = {'summary': {}, 'crew': {}}
        services['summary'] = {
            _('Monthly Cost'): get_by_path(self.data, ["finance", "servicesCost"], 0),
            _('Month to date'): get_by_path(self.data, ["finance", "servicesCost"], 0),
        }
        for k, v in self.data.get('servicesCrew', {}).items():
            services['crew'][k] = deepcopy(v)
            services['crew'][k]['taxation'] = get_by_path(self.data, ['finance', 'service_taxation', k], 0)

        return services


    def get_cargo(self, type:str='all') -> dict:
        """ Return cargo as a dictionary """


        summ:dict = {
            _("Total Space") : 0,
            _("For Sale") : self.cargo['summary'].get('cargoForSale', 0),
            _("Not For Sale") : self.cargo['summary'].get('cargoNotForSale', 0),
            _("Reserved") : self.cargo['summary'].get('cargoSpaceReserved', 0),
        }
        summ[_("Total Space")] = sum(summ.values())

        comm:dict = {}
        for t, ent in self.cargo.items():
            if t == 'summary': continue
            if type == 'all' or t == type:
                for name, deets in ent.items():

                    deets['mission'] = (t == 'mission')
                    deets['stolen'] = (t == 'stolen')
                    comm[name] = deets

        comm = dict(sorted(comm.items(), key=lambda item: item[1]['category']+','+item[1]['locName']))
        return {'summary': summ, 'commodities': comm}


    def get_locker(self) -> dict:
        """ Return locker as a dictionary """
        self.locker = self._update_locker(self.data) # Temporary

        summ:dict = {}
        if get_by_path(self.data, ["finance", "bartender"], None ) != None:
            summ = {
                _('Total Value') : get_by_path(self.data, ["finance", "bartender", "microresourcesTotalValue"], 0),
                _('For Sale') : get_by_path(self.data, ["finance", "bartender", "microresourcesForSale"], 0),
                _('Orders') : get_by_path(self.data, ["finance", "bartender", "microresourcesPurchaseOrders"], 0),
                _('Profit') : get_by_path(self.data, ["finance", "bartender", "allTimeProfit"], 0),
            }

        res:dict = {}
        for t, ent in self.locker.items():
            for mat, deets in ent.items():
                deets['mission'] = (t == 'mission')
                res[mat] = deets
        res = dict(sorted(res.items(), key=lambda item: item[1]['category']+','+item[1]['locName']))

        return {'summary': summ, 'resources': res}


    def get_itinerary(self) -> dict:
        """ Return the carrier itinerary """

        sched:str = get_by_path(self.data, ["itinerary", "currentJump"], "None") if get_by_path(self.data, ["itinerary", "currentJump"], "None") != "null" else _("None") # LANG: Scheduled jump
        summ:dict = {
            _('Scheduled Jump'): sched,
            _("Total Distance"): f"{get_by_path(self.data, ['itinerary', 'totalDistanceJumpedLY'], 0)} Ly"
        }
        res:dict = deepcopy(get_by_path(self.data, ['itinerary', 'completed'], {}))
        comp:list = sorted(res, key=lambda item: datetime.strptime(item['arrivalTime'], '%Y-%m-%d %H:%M:%S'), reverse=True)

        return {'summary': summ, 'completed': comp}


    def _update_space(self, market:int = 0, cargo:int = 0, order:int = 0) -> None:
        """ Update the free space on the carrier as events occur"""
        self.summary['freeSpace'] += market
        self.summary['freeSpace'] += cargo

        self.cargo['summary']['cargoSpaceReserved'] += market
        self.cargo['summary']['cargoSpaceReserved'] += order



    def _update_cargo(self, data: dict) -> dict:
        """ Update cargo data from CAPI data structure """
        # @TODO: Add blackmarket sales
        cargo:dict = {'summary': {}, 'stolen': {}, 'mission': {}, 'normal': {}}
        cargo['summary']['cargoForSale'] = get_by_path(data, ['capacity', 'cargoForSale'], 'None')
        cargo['summary']['cargoNotForSale'] = get_by_path(data, ['capacity', 'cargoNotForSale'], 'None')
        cargo['summary']['cargoSpaceReserved'] = get_by_path(data, ['capacity', 'cargoSpaceReserved'], 'None')

        comms:dict = {}
        try:
            comms = self.bgstally.ui.commodities
        except Exception as e:
            Debug.logger.error(f"Error getting commodity details")

        for c in get_by_path(data, ['cargo'], []):
            cname:str = c.get('commodity', "").lower()
            stolen:bool = c.get('stolen', False)
            mission:bool = c.get('mission', False)
            for type in ['stolen', 'mission']:
                if (stolen and type == 'stolen') or (mission and type == 'mission'):
                    stock = c.get('qty', 0)
                    if cargo[type].get('name', "") == cname:
                        stock += cargo[type][cname]['stock']
                    cargo[type][cname] = {'stock': stock}
                continue

            # all the ways a commodity may be listed in CAPI data
            sale:dict = next((item for item in get_by_path(data, ['orders', 'commodities', 'sales'], []) if item.get('name', "").lower() == cname), {})
            purchase:dict = next((item for item in get_by_path(data, ['orders', 'commodities', 'purchases'], []) if item.get('name', "").lower() == cname), {})
            market:dict = next((item for item in get_by_path(data, ['market', 'commodities'], []) if item.get('name', "").lower() == cname), {})

            # Figure out the stock using the various sources
            stock:int = max(int(sale.get('stock', 0)), int(market.get('stock', 0)))

            if stock == 0: # No sales or market so cargo. There may be multiple of these so we need to do addition
                stock = c.get('qty', 0)
                if cname in cargo['normal']:
                    stock += cargo['normal'][cname]['stock']

            if stock > 0 or purchase.get('outstanding', 0):
                cargo['normal'][cname] = {'locName': comms.get(cname, {}).get('Name', c.get('locName', cname).lower()),
                                        'category': comms.get(cname, {}).get('Category', c.get('categoryname', 'Unknown')),
                                        'stock': stock,
                                        'buyTotal': purchase.get('total', 0),
                                        'outstanding': purchase.get('outstanding', 0),
                                        'price': max(int(sale.get('price', 0)), int(purchase.get('price', 0)),
                                                        int(market.get('sellPrice', 0)), int(market.get('buyPrice', 0)))
                                        }

        return cargo


    def _update_locker(self, data: dict) -> dict:
        """ Update locker data from CAPI data structure """

        locker:dict = {'mission' : {}, 'normal' : {}}
        for cat, v in get_by_path(data, ['carrierLocker'], {}).items():
            for m in v:
                name = m.get('name', "").lower()
                # all the ways a commodity may be listed in CAPI data
                sale:dict = next((item for item in list(get_by_path(data, ['orders', 'onfootmicroresources', 'sales'], {}).values()) if item.get('name', "").lower() == name), {})
                purchase:dict = next((item for item in get_by_path(data, ['orders', 'onfootmicroresources', 'purchases'], []) if item.get('name', "").lower() == name), {})
                type = 'mission' if m.get('mission', False) == True else 'normal'
                if name not in locker[type] and m.get('quantity', 0) > 0 or purchase.get('outstanding', 0) > 0:
                    locker[type][name] = {'locName': m.get('locName', name),
                                          'category': cat.title(),
                                          'quantity': m.get('quantity', 0),
                                          'buyTotal': purchase.get('total', 0),
                                          'outstanding': purchase.get('outstanding', 0),
                                          'price': max(m.get('price', 0), sale.get('price', 0), purchase.get('price', 0))
                                         }
        return locker


    @catch_exceptions
    def update(self, data: dict) -> None:
        """ Store the latest data from CAPI response """
        # Data directly from CAPI response. This is only received for personal carriers. Structure documented here:
        # https://github.com/EDCD/FDevIDs/blob/master/Frontier%20API/FrontierDevelopments-CAPI-endpoints.md#fleetcarrier

        # Store the whole data structure
        Debug.logger.debug(f"Updating carrier data (CAPI?)")
        self.data = data
        self.carrier_id = get_by_path(self.data, ['market', 'id'], 0)

        # we can update all the local vars with this loop.
        updates:dict = {'name': [self.summary, ['name', 'vanityName'], "----"],
                        'currentStarSystem': [self.summary, ['currentStarSystem'], ''],
                        'dockingAccess': [self.summary, ['dockingAccess'], 'None'],
                        'state': [self.summary, ['state'], ''],
                        'carrier_id': [self.summary, ['market', 'id'], 0],
                        'freeSpace': [self.summary, ['capacity', 'freeSpace'], 0],
                        'callsign': [self.summary, ['name', 'callsign'], ''],
                        'notoriousAccess': [self.summary, ['notoriousAccess'], False],
                        'theme': [self.summary, ['theme'], ''],
                        'bankBalance': [self.summary, ['finance', 'bankBalance'], 0],
                        'bankReservedBalance': [self.summary, ['finance', 'bankReservedBalance'], 0],
                        'maintenance': [self.summary, ['finance', 'maintenance'], 0],
                        'numJumps': [self.summary, ['finance', 'numJumps'], 0],
                        'taxation':  [self.summary, ['finance', 'taxation'], 0],
                        }
        for k, v in updates.items():
            v[0][k] = get_by_path(self.data, v[1], v[2])

        # Now deal with the exceptions.
        if self.summary['name'] != updates['name'][2]:         # Name is encoded as hex string
            self.summary['name'] = bytes.fromhex(self.summary['name']).decode('utf-8')
        self.summary['fuel'] = int(self.data.get('fuel', 0))

        self.locker = self._update_locker(self.data)

        # Only use the CAPI data if we haven't docked in the last 15 minutes
        if self.last_modified > int(time.time()) - 900:
            Debug.logger.debug("Ignoring CAPI update")
            return

        self.cargo = self._update_cargo(self.data)


    @catch_exceptions
    def stats_received(self, entry: dict) -> None:
        """ The user entered the carrier management screen """
        if entry.get(KEY_CARRIER_TYPE) == FleetCarrierType.PERSONAL:
            # Note we always re-populate here, in case the user has bought a new carrier. We should get a subsequent CAPI update to populate the rest.

            self.summary['name'] = entry.get('Name', "")
            self.summary['callsign'] = entry.get('Callsign', "")
            self.summary['carrier_id'] = entry.get('CarrierID', "")
            self.summary['dockingAccess'] = entry.get('DockingAccess', "")


    @catch_exceptions
    def jump_requested(self, entry: dict[str, str]) -> None:
        """ The user scheduled a carrier jump """
        # {"timestamp": "2020-04-20T09:30:58Z", "event": "CarrierJumpRequest", "CarrierID": 3700005632, "SystemName": "Paesui Xena", "Body": "Paesui Xena A", "SystemAddress": 7269634680241, "BodyID": 1, "DepartureTime":"2020-04-20T09:45:00Z"}

        if entry.get("CarrierID") != self.summary.get('carrier_id', ''): return

        title:str = __("Jump Scheduled for Carrier {carrier_name}", lang=self.bgstally.state.discord_lang).format(carrier_name=self.summary['name']) # LANG: Discord post title
        description:str = __("A carrier jump has been scheduled", lang=self.bgstally.state.discord_lang) # LANG: Discord text

        departure_datetime: datetime|None = datetime.strptime(entry.get('DepartureTime', ""), DATETIME_FORMAT_JOURNAL)
        departure_datetime = departure_datetime.replace(tzinfo=UTC)

        fields = []
        fields.append({'name': __("From System", lang=self.bgstally.state.discord_lang), 'value': self.data.get('currentStarSystem', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("To System", lang=self.bgstally.state.discord_lang), 'value': entry.get('SystemName', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("To Body", lang=self.bgstally.state.discord_lang), 'value': entry.get('Body', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("Departure Time", lang=self.bgstally.state.discord_lang), 'value': f"<t:{round(departure_datetime.timestamp())}:R>"}) # LANG: Discord heading
        fields.append({'name': __("Docking", lang=self.bgstally.state.discord_lang), 'value': self._readable(self.data.get('dockingAccess', ''), True), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("Notorious Access", lang=self.bgstally.state.discord_lang), 'value': self._readable(self.data.get('notoriousAccess', False), False), 'inline': True}) # LANG: Discord heading
        self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_OPERATIONS, None)


    @catch_exceptions
    def jump_cancelled(self, entry: dict[str, str]) -> None:
        """ The user cancelled their carrier jump """
        if entry.get("CarrierID") != self.summary.get('carrier_id', ''): return

        title:str = __("Jump Cancelled for Carrier {carrier_name}", lang=self.bgstally.state.discord_lang).format(carrier_name=self.summary['name']) # LANG: Discord post title
        description:str = __("The scheduled carrier jump was cancelled", lang=self.bgstally.state.discord_lang) # LANG: Discord text

        fields = []
        fields.append({'name': __("Current System", lang=self.bgstally.state.discord_lang), 'value': self.data.get('currentStarSystem', "Unknown"), 'inline': True})
        fields.append({'name': __("Docking", lang=self.bgstally.state.discord_lang), 'value': self._readable(self.data.get('dockingAccess', ''), True), 'inline': True})
        fields.append({'name': __("Notorious Access", lang=self.bgstally.state.discord_lang), 'value': self._readable(self.data.get('notoriousAccess', False), True), 'inline': True})
        self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_OPERATIONS, None)


    @catch_exceptions
    def trade_order(self, entry:dict) -> None:
        """ The user set a buy or sell order on their carrier """
        # { "timestamp":"2024-02-17T16:33:10Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"imperialslaves", "Commodity_Localised":"Imperial Slaves", "SaleOrder":10, "Price":1749300 }
        # { "timestamp":"2024-02-17T16:33:51Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"unstabledatacore", "Commodity_Localised":"Unstable Data Core", "PurchaseOrder":5, "Price":4516 }
        # { "timestamp":"2024-02-17T16:35:57Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"unstabledatacore", "Commodity_Localised":"Unstable Data Core", "CancelTrade":true }

        if entry.get("CarrierID") != self.summary.get('carrier_id', ''): return
        self.last_modified = int(time.time())

        comm:str = entry.get('Commodity', "").lower()
        if comm not in self.bgstally.ui.commodities:
            # The order is for a material.
            mat:str = entry.get('Commodity', "")
            if mat not in self.locker['normal']:
                self.locker['normal'][mat] = {'locName': entry.get('Commodity_Localised', mat), 'category': '', 'price': 0, 'quantity': 0}
                self.locker['normal'][mat]['price'] = int(entry.get('Price', 0))
                self.locker['normal'][mat]['buyTotal'] = 0

                if entry.get('SaleOrder') is not None:
                    self.locker['normal'][mat]['quantity'] = int(entry.get('SaleOrder', 0))

                if entry.get('PurchaseOrder') is not None:
                    self.locker['normal'][mat]['buyTotal'] = int(entry.get('PurchaseOrder', 0))
            return

        if comm not in self.cargo['normal']:
            self.cargo['normal'][comm] = {'locName': self.bgstally.ui.commodities[comm].get('Name', entry.get('Commodity_Localised')),
                                            'category': self.bgstally.ui.commodities[comm].get('Category', 'Unknown'),
                                            'stock': 0,
                                            'buyTotal': 0,
                                            'outstanding': 0,
                                            'price': entry.get('Price', 0)
                                            }

        if entry.get('SaleOrder') is not None:
            self._update_space(-(entry.get('SaleOrder', 0) - self.cargo['normal'][comm]['stock']))
            self.cargo['normal'][comm]['stock'] = entry.get('SaleOrder', 0)

        if entry.get('PurchaseOrder') is not None:
            # Reduce the space by the difference between previous and new order
            self._update_space(-(entry.get('PurchaseOrder', 0) - self.cargo['normal'][comm]['buyTotal']))
            self.cargo['normal'][comm]['buyTotal'] = entry.get('PurchaseOrder', 0)
            self.cargo['normal'][comm]['outstanding'] = entry.get('PurchaseOrder', 0)

        if entry.get('CancelTrade') == True:
            # @TODO: Adjust space
            self.cargo['normal'][comm]['buyTotal'] = 0
            self.cargo['normal'][comm]['outstanding'] = 0

        Debug.logger.debug(f"Updated cargo: {self.cargo['normal'][comm]}")


    @catch_exceptions
    def market(self, entry: dict) -> None:
        """ Market event. If it's for our carrier we update the cargo amounts using BGS-Tally's copy of the market data"""
        if entry.get("MarketID") != self.summary.get('carrier_id', ''): return
        self.last_modified = int(time.time())

        Debug.logger.debug(f"Market event")

        if not self.bgstally.market.available(entry.get("MarketID")):
            Debug.logger.debug(f"No market data available for CarrierID {entry.get('MarketID')}")
            return

        for comm, item in self.bgstally.market.commodities.items():
            if comm not in self.cargo['normal']:
                self.cargo['normal'][comm] = {'locName': self.bgstally.ui.commodities[comm].get('Name', item.get('Commodity_Localised')),
                                        'category': self.bgstally.ui.commodities[comm].get('Category', item.get('Category_Localised')),
                                        'stock': 0,
                                        'buyTotal': 0,
                                        'outstanding': 0,
                                        'price': 0
                                        }
            # Buying
            if item.get('Consumer', False) == True:
                demand:int = int(item.get('Demand', 0))
                outstanding:int = int(self.cargo['normal'][comm]['outstanding'])

                # Someone else must have sold to us, so increase stock based on demand changes
                if demand < outstanding:
                    self._update_space(-(outstanding - demand))
                    self.cargo['normal'][comm]['stock'] += (outstanding - demand)

                self.cargo['normal'][comm]['outstanding'] = demand
                self.cargo['normal'][comm]['price'] = int(item.get('SellPrice', 0)) # Price player sells at

            # Stock is only useful if it's selling not when it's buying
            if item.get('Producer', False) == True:
                self._update_space(-(self.cargo['normal'][comm]['stock'] - int(item.get('Stock', 0))))
                self.cargo['normal'][comm]['price'] = int(item.get('BuyPrice', 0)) # Price player buys at
                self.cargo['normal'][comm]['stock'] = int(item.get('Stock', 0))

            #Debug.logger.debug(f"Updated cargo: {self.cargo['normal'][comm]}")


    @catch_exceptions
    def cargo_transfer(self, entry:dict) -> None:
        """ The user transferred cargo to or from the carrier """
        # { "timestamp":"2025-03-22T15:15:21Z", "event":"CargoTransfer", "Transfers":[ { "Type":"steel", "Count":728, "Direction":"toship" }, { "Type":"titanium", "Count":56, "Direction":"toship" } ] }
        self.last_modified = int(time.time())

        for i in entry.get('Transfers', []):
            comm:str = i.get('Type', "").lower()
            if comm not in self.cargo['normal']:
                self.cargo['normal'][comm] = {'locName': self.bgstally.ui.commodities[comm].get('Name', comm),
                                            'category': self.bgstally.ui.commodities[comm].get('Category', 'Unknown'),
                                            'stock': 0,
                                            'buyTotal': 0,
                                            'outstanding': 0,
                                            'price': 0
                                            }

            if i.get('Direction') == 'tocarrier':
                self._update_space(cargo=-int(i.get('Count', 0)))
                self.cargo['normal'][comm]['stock'] += int(i.get('Count', 0))
                continue

            self._update_space(cargo=int(i.get('Count', 0)))
            self.cargo['normal'][comm]['stock'] -= min(int(i.get('Count', 0)), self.cargo['normal'][comm]['stock'])
            Debug.logger.debug(f"Updated cargo: {self.cargo['normal'][comm]}")


    @catch_exceptions
    def market_activity(self, entry:dict) -> None:
        ''' We bought or sold to/from our carrier '''
        if entry.get('MarketID') != self.summary.get('carrier_id', ''): return
        self.last_modified = int(time.time())

        #{ "timestamp":"2025-09-18T23:39:55Z", "event":"MarketBuy", "MarketID":3709409280, "Type":"fruitandvegetables", "Type_Localised":"Fruit and Vegetables", "Count":195, "BuyPrice":483, "TotalCost":94185 }
        comm:str = entry.get('Type', "").lower()
        if comm not in self.cargo['normal']:
            self.cargo['normal'][comm] = {'locName': self.bgstally.ui.commodities[comm].get('Name', entry.get('Type_Localised', comm)),
                                        'category': self.bgstally.ui.commodities[comm].get('Category', 'Unknown'),
                                        'stock': 0,
                                        'buyTotal': 0,
                                        'outstanding': 0,
                                        'price': 0
                                        }

        if entry.get('event') == "MarketBuy":
            self._update_space(int(entry.get('Count', 0)))
            self.cargo['normal'][comm]['stock'] -= min(entry.get('Count', 0), self.cargo['normal'][comm]['stock'])
            self.cargo['normal'][comm]['price'] = entry.get('BuyPrice', self.cargo['normal'][comm]['price'])

        # Sell
        if entry.get('event') == "MarketSell":
            self._update_space(-int(entry.get('Count', 0)))
            self.cargo['normal'][comm]['stock'] += entry.get('Count', 0)
            self.cargo['normal'][comm]['outstanding'] -= min(entry.get('Count', 0), self.cargo['normal'][comm]['outstanding'])
            self.cargo['normal'][comm]['price'] = entry.get('SellPrice', self.cargo['normal'][comm]['price'])

        Debug.logger.debug(f"Updated cargo: {self.cargo['normal'][comm]}")


    @catch_exceptions
    def get_items_plaintext(self, category:FleetCarrierItemType|None = None) -> str:
        """ Return a multiline text string containing all items of a given type (category) """
        return ""
        items, name_key, display_name_key, quantity_key = self._get_items(category)
        if items is None: return ""

        result: str = ""
        cargo:dict = {}
        if category == FleetCarrierItemType.CARGO:
            # Cargo is a special case because it can have multiple items with the same name so we have to sum them together
            for name in sorted(items.keys()):
                # No longer prioritise the display name from CAPI data, as now that we have localised commodity names, we do a lookup first.
                # This allows us to translate to the EDMC language rather than the (limited set of) game languages.
                if name.lower() in self.bgstally.ui.commodities:
                    display_name:str = self.bgstally.ui.commodities[name.lower()]['Name']
                elif display_name_key in items[name]:
                    # No translation, fall back to display name from CAPI data
                    display_name:str = items[name][display_name_key]
                else:
                    # No CAPI display name, fall back to the item name (which may not have spaces)
                    display_name:str = name

                if display_name in cargo:
                    cargo[display_name] += int(items[name][quantity_key])
                else:
                    cargo[display_name] = int(items[name][quantity_key])
            for key, value in cargo.items():
                result += f"{key} x {value}\n"
            return result

        if category == FleetCarrierItemType.LOCKER:
            # Locker is a special case because it's sub-divided into types
            for type in items:
                result += f"{type.title()}:\n"
                items[type] = sorted(items[type], key=lambda x: x[display_name_key])
                for item in items[type]:
                    if int(item[quantity_key]) > 0: # This one includes zero quantities for some reason
                        result += f"    {item[display_name_key]} x {item[quantity_key]}\n"
            return result

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

            #if int(item[quantity_key]) > 0:
                #result += f"{display_name} x {item[quantity_key]} @ {self._format(item['price'])}\n"
        return result


    @catch_exceptions
    def _readable(self, field:str, discord:bool = False) -> str:
        """ Return a human-readable format of various attributes """
        val = self.readable.get(field, "") if self.readable.get(field, None) != None else str(field)
        return __(val, lang=self.bgstally.state.discord_lang) if discord else _(val)


    def _get_items(self, category: FleetCarrierItemType = None) -> tuple[list|dict|None, str|None, str|None, str|None]:
        """Return the current items list, lookup name key, display name key and quantity key for the specified category

        Args:
            category (FleetCarrierItemType, optional): The type of item to fetch. Defaults to None.

        Returns:
            tuple[list|None, str|None, str|None, str|None]: Tuple containing the four items
        """

        Debug.logger.debug(f"Getting items for category {category}")
        match category:
            case FleetCarrierItemType.MATERIALS_SELLING:
                return self.locker, 'name', 'locName', 'quantity'
            case FleetCarrierItemType.MATERIALS_BUYING:
                return self.locker, 'name', 'locName', 'outstanding'
            case FleetCarrierItemType.COMMODITIES_SELLING:
                # Lookup name and display name are the same for commodities as we are not passed localised name from CAPI. We
                # convert the display name later
                return self.cargo['normal'], 'name', 'locName', 'stock'
            case FleetCarrierItemType.COMMODITIES_BUYING:
                # Lookup name and display name are the same for commodities as we are not passed localised name from CAPI. We
                # convert the display name later
                return self.cargo['normal'], 'name', 'locName', 'outstanding'
            case FleetCarrierItemType.CARGO:
                # Return cargo items
                return self.cargo['normal'], 'commodity', 'locName', 'stock'
            case FleetCarrierItemType.LOCKER:
                # Return locker items
                return self.locker, 'name', 'locName', 'quantity'
            case _:
                return None, None, None, None


    def _as_dict(self) -> dict:
        """ Return a Dictionary representation of our data, suitable for serializing """
        return {
            'summary': self.summary,
            'cargo': self.cargo,
            'locker': self.locker,
            'data': self.data
            }


    def _from_dict(self, dict: dict) -> None:
        """ Populate our data from a Dictionary that has been deserialized """
        Debug.logger.debug(f"Loading _from_dict")
        self.summary = dict.get('summary', {})
        self.cargo = dict.get('cargo', {})
        if 'normal' not in self.cargo: self.cargo = {'summary': {}, 'stolen': {}, 'mission': {}, 'normal': {}} # For migration from old to new format
        self.locker = dict.get('locker', {})
        if 'normal' not in self.locker: self.locker = {'summary': {}, 'mission': {}, 'normal': {}} # For migration from old to new format
        if isinstance(self.locker, list): self.locker = {} # For migration from old to new format
        self.data = dict.get('data', {})


    @catch_exceptions
    def load(self) -> None:
        """ Load state from file """

        file:str = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        if path.exists(file):
            with open(file) as json_file:
                self._from_dict(json.load(json_file))
                if self.data is None or self.data.get('name') is None:
                    # There is no CAPI data, so clear our name and callsign as we have no personal carrier. This is to clear up
                    # the problem where a squadron carrier was accidentally stored as a personal one, when the user doesn't
                    # have a personal carrier.
                    self.summary = {}
                elif self.summary.get('callsign', None) != get_by_path(self.data, ['name', 'callsign']):
                    # The CAPI callsign doesn't match our stored callsign, so re-parse the CAPI data. This is to clear up
                    # the problem where a squadron carrier was accidentally stored as a personal one, overwriting the user's
                    # actual personal carrier data.
                    self.update(self.data)


    @catch_exceptions
    def save(self) -> None:
        """ Save state to file """
        file:str = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self._as_dict(), outfile, indent=4)


# Bunch of translation strings
trans = [_("All"), # LANG: Carrier all access
    _("Squadron and Friends"), # LANG: Carrier docking permission
    _("Friends"), # LANG: Carrier docking permission
    _("None"), # LANG: Carrier docking permission
    _("Normal"), # LANG: Carrier operation
    _("Offline"), # LANG: Carrier operation
    _("Decommissioning"), # LANG: Carrier operation
    _("Search and Rescue"), # LANG: Carrier theme
    _("Mining"), # LANG: Carrier theme
    _("Trader"), # LANG: Carrier theme
    _("Exploerer"), # LANG: Carrier theme
    _("Anti-Xeno"), # LANG: Carrier theme
    _("Bounty Hunter"), # LANG: Carrier theme
    ]