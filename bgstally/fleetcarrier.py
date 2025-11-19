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
    """
    Used to store, track and return fleetcarrier data.
    Data is received from the FDev CAPI and from carrierstats events.
    Activity is also tracked through sell, buy, market & order events since the CAPI is queried infrequently and
    can be unhelpfully out of date.
    """
    def __init__(self, bgstally):
        self.bgstally:BGSTally = bgstally # type: ignore

        # CAPI data is only received periodically and can be out of date so we take a copy of what we need and store it here.
        self.carrier_id:int = 0
        self.overview:dict = {}
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

    @catch_exceptions
    def available(self) -> bool:
        """ Return true if there is data available on a Fleet Carrier """
        return self.overview.get('name', None) is not None and self.overview.get('callsign', None) is not None


    @catch_exceptions
    def get_overview(self) -> dict:
        """ Return the carrier overview """

        itinerary = get_by_path(self.data, ['itinerary', 'completed'], [])
        if len(itinerary) > 0:
            arrival = itinerary[-1].get('arrivalTime', "")

        return {
            _('Name'): self.overview.get('name', ''),                                    # LANG: Carrier overview
            _('Callsign'): self.overview.get('callsign', ''),                            # LANG: Carrier overview
            _('Location'): self.overview.get('currentStarSystem', ''),                   # LANG: Carrier overview

            _('Arrival'): (arrival, 'datetime', 'Unknown'),                              # LANG: Carrier overview
            _('Docking'): (self._readable(self.overview.get('dockingAccess', '')), 'str', 'Unknown'), # LANG: Carrier overview
            _('Allow Notorious'): (self.overview.get('notoriousAccess', ''), 'str', 'Unknown'), # LANG: Carrier overview

            _('Fuel'): (self.overview.get('fuel', 0), 'num', 0, 't'),                    # LANG: Carrier overview
            _('Space'): (int(self.overview.get('freeSpace', 0) * 100 / self.overview.get('totalCapacity', 25000)), 'num', 'None', '%'),         # LANG: Spare capacity
            _('Tax Level'): (self.overview.get('taxation', 0), 'num', '0%', '%'),        # LANG: Carrier debt limit
        }

    @catch_exceptions
    def get_summary(self) -> dict:
        """ Return summary information as a dictionary """
        summary:dict = {'finances': [], 'costs': [], 'capacity': []}

        summary['finances'] = {
            _('Bank Balance'): self.overview.get('bankBalance', 0),    # LANG: Carrier overview
            _('Bank Reserve'): self.overview.get('bankReservedBalance', 0),   # LANG: Carrier overview
            _('Available Balance'): self.overview.get('bankBalance', 0)-self.overview.get('bankReservedBalance', 0),
            _('Reserve Percentage'): (round((self.overview.get('bankReservedBalance', 0) * 100) / self.overview.get('bankBalance', 1)), 'num', 0, '%')
        }
        summary['costs'] = {
            _('Total'): self.overview.get('maintenance', 0),                                # LANG: Carrier overview
            _('Core Cost'): self.overview.get('coreCost', 0),                                     # LANG: Carrier overview
            _('Services Cost'): self.overview.get('servicesCost', 0),                             # LANG: Carrier overview
            _('Jump Cost'): (get_by_path(self.data, ["finance", "numJumps"], 0) * 100000, 'num', 0),   # LANG: Carrier overview
        }

        summary['capacity'] = {
            _('Total Capacity'): (self.overview.get('totalCapacity', 25000), 'num', 'Unknown', 't'),   # LANG: Carrier overview
            _('Total Used'): (self.overview.get('totalCapacity', 25000) - self.overview.get('freeSpace'), 'num', '0t', 't'),              # LANG: Carrier overview
            _('Free Space'): (self.overview.get('freeSpace'), 'num', '0t', 't'),                             # LANG: Carrier overview
            _('Ship Packs'): (self.overview.get('shipPacks', 0), 'num', '0t', 't'),                          # LANG: Carrier overview
            _('Module Packs'): (self.overview.get('modulePacks', 0), 'num', '0t', 't'),                      # LANG: Carrier overview

            _('Cargo For Sale'): (self.cargo['overview'].get('cargoForSale', 0), 'num', '0t', 't'),           # LANG: Carrier overview
            _('Cargo Not For Sale'): (self.cargo['overview'].get('cargoNotForSale', 0), 'num', '0t', 't'),     # LANG: Carrier overview
            _('Cargo Reserved Space'): (self.cargo['overview'].get('cargoSpaceReserved', 0), 'num', '0t', 't'),  # LANG: Carrier overview
            _('Crew') : (self.overview.get('crew', 0), 'num', 'Unknown', 't'),                                   # LANG: Carrier overview
        }
        return summary


    @catch_exceptions
    def get_services(self) -> dict:
        """ Return services as a dictionary """
        services:dict = {'overview': {}, 'crew': {}}
        services['overview'] = {
            _('Weekly Cost'): get_by_path(self.data, ["finance", "servicesCost"], 0),
            _('Cost to date'): get_by_path(self.data, ["finance", "servicesCostToDate"], 0),
            _('Crew Capacity'): get_by_path(self.data, ["capacity", "crew"], 0),
        }
        crew:dict = get_by_path(self.data, ['servicesCrew'], {})
        for k, v in get_by_path(self.data, ["market", "services"], {}).items():

            services['crew'][k] = deepcopy(crew.get(k, {}).get('crewMember', {}))
            services['crew'][k]['enabled'] = (services['crew'].get(k, {}).get('enabled', ''), 'str', 'No')

            services['crew'][k]['status'] = v
            services['crew'][k]['taxation'] = (get_by_path(self.data, ['finance', 'service_taxation', k], 0), 'num', '0%', '%')
        return services


    @catch_exceptions
    def get_cargo(self, type:str='all') -> dict:
        """ Return cargo as a dictionary """

        comm:dict = {}
        selling:int = 0
        nosale:int = 0
        stored:int = 0
        reserved:int = 0
        for t, ent in self.cargo.items():
            if t == 'overview': continue
            if type == 'all' or t == type:
                for name, deets in ent.items():
                    deets['locName'] = self.bgstally.ui.commodities.get(name, {}).get('Name', name)
                    deets['category'] = self.bgstally.ui.commodities.get(name, {}).get('Category', '') if isinstance(self.bgstally.ui.commodities.get(name, {}).get('Category', ''), str) else 'Unknown'
                    deets['mission'] = (t == 'mission')
                    deets['stolen'] = (t == 'stolen')
                    stored += deets['stock']
                    if deets['stock'] > 0:
                        if deets['price'] > 0 and deets['buyTotal'] == 0 and t == 'normal':
                            selling += deets['stock']
                        else:
                            nosale += deets['stock']
                    if deets['outstanding'] > 0: reserved += deets['outstanding']
                    comm[name] = deets
        comm = dict(sorted(comm.items(), key=lambda item: item[1]['category']+','+item[1]['locName']))

        summ:dict = {
            _("Capacity") : (self.overview.get('freeSpace', 0) + stored + reserved, 'num', 'Unknown', 't'),
            _("Used") : (stored+reserved, 'num', '0t', 't'),
            _("Stored") : (stored, 'num', '0t', 't'),
            _("Reserved") : (reserved, 'num', '0t', 't'),
            _("Selling") : (selling, 'num', '0t', 't'),
            _("Buying") : (reserved, 'num', '0t', 't'),
            _('Total Value') : get_by_path(self.data, ["marketFinances", "cargoTotalValue"], 0),
            _('Profit') : get_by_path(self.data, ["marketFinances", "allTimeProfit"], 'None'),
        }
        return {'overview': summ, 'inventory': comm}


    @catch_exceptions
    def get_locker(self) -> dict:
        """ Return locker as a dictionary """
        self.locker = self._update_locker(self.data) # Temporary

        res:dict = {}
        buying:int = 0
        selling:int = 0
        stored:int = 0
        for t, ent in self.locker.items():
            for mat, deets in ent.items():
                deets['mission'] = (t == 'mission')
                buying += deets['outstanding']
                if deets['outstanding'] == 0 and deets['price'] > 0 and (t == 'normal'):
                    selling += deets['stock']
                stored += deets['stock']
                res[mat] = deets
        res = dict(sorted(res.items(), key=lambda item: item[1]['category']+','+item[1]['locName']))

        summ:dict = {}
        if get_by_path(self.data, ["finance", "bartender"], None ) != None:
            summ = {
                _('Capacity') : get_by_path(self.data, ["capacity", "microresourceCapacityTotal"], 0),
                _('Used') : get_by_path(self.data, ["capacity", "microresourceCapacityUsed"], 0),
                _('Stored') : stored,
                _('Reserved') : get_by_path(self.data, ["capacity", "microresourceCapacityReserved"], 0),
                _('Selling') : selling,
                _('Buying') : buying,
                _('Total Value') : get_by_path(self.data, ["finance", "bartender", "microresourcesTotalValue"], 0),
                _('Profit') : get_by_path(self.data, ["finance", "bartender", "allTimeProfit"], 'None'),
            }
        return {'overview': summ, 'inventory': res}


    def get_itinerary(self) -> dict:
        """ Return the carrier itinerary """

        Debug.logger.debug(f"{get_by_path(self.data, ['itinerary', 'currentJump'], '???')}")
        sched:str = get_by_path(self.data, ["itinerary", "currentJump"], "None") if get_by_path(self.data, ["itinerary", "currentJump"], "None") != "null" else _("None") # LANG: Scheduled jump
        if self.overview.get('jumpDestination', None) != None and self.overview.get('jumpDestination', '') not in self.overview.get('currentSystem', ''):
            sched = self.overview.get('jumpDestination', '')
        summ:dict = {
            _('Scheduled Jump'): sched,
            _('Fuel'): (self.overview.get('fuel', 0), 'num', '0t', 't'),
            _('Tritium'): (get_by_path(self.cargo, ['normal', 'tritium', 'stock'], 0), 'num', '0t', 't'),
        }
        res:dict = deepcopy(get_by_path(self.data, ['itinerary', 'completed'], {}))
        comp:list = []
        for j in sorted(res, key=lambda item: datetime.strptime(item['arrivalTime'], '%Y-%m-%d %H:%M:%S'), reverse=True):
            comp.append({
                'departureTime': (j.get('departureTime', ''), 'datetime', ''),
                'arrivalTime': (j.get('arrivalTime', ''), 'datetime', 'Unknown'),
                'state': (j.get('state',''), 'str', 'Unknown'),
                'visitDurationSeconds': (j.get('visitDurationSeconds', 0), 'interval', 'Unknown'),
                'starSystem': (j.get('starsystem', ''), 'str', 'Unknown')
            })
        return {'overview': summ, 'completed': comp}


    def _update_cargo(self, data: dict) -> dict:
        """ Update cargo data from CAPI data structure """
        # @TODO: Add blackmarket sales
        cargo:dict = {'overview': {}, 'stolen': {}, 'mission': {}, 'normal': {}}
        cargo['overview']['cargoForSale'] = get_by_path(data, ['capacity', 'cargoForSale'], 'None')
        cargo['overview']['cargoNotForSale'] = get_by_path(data, ['capacity', 'cargoNotForSale'], 'None')
        cargo['overview']['cargoSpaceReserved'] = get_by_path(data, ['capacity', 'cargoSpaceReserved'], 'None')

        comms:dict = {}
        try:
            comms = self.bgstally.ui.commodities
        except Exception as e:
            Debug.logger.error(f"Error getting commodity details {e}")

        for c in get_by_path(data, ['cargo'], []):
            cname:str = c.get('commodity', "").lower()
            stolen:bool = c.get('stolen', False)
            mission:bool = c.get('mission', False)

            # Deal with stolen and mission cargo first
            if stolen or mission:
                for type in ['stolen', 'mission']:
                    if (stolen and type == 'stolen') or (mission and type == 'mission'):
                        if cargo[type].get(cname, None) == None:
                            cargo[type][cname] = {'stock': 0}
                        cargo[type][cname]['stock'] += c.get('qty', 0)
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
                cargo['normal'][cname] = {
                    'locName': comms.get(cname, {}).get('Name', c.get('locName', cname).lower()),
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
                name:str = m.get('name', "").lower()
                # all the ways a commodity may be listed in CAPI data
                sale:dict = next((item for item in list(get_by_path(data, ['orders', 'onfootmicroresources', 'sales'], {}).values()) if item.get('name', "").lower() == name), {})
                purchase:dict = next((item for item in get_by_path(data, ['orders', 'onfootmicroresources', 'purchases'], []) if item.get('name', "").lower() == name), {})
                type:str = 'mission' if m.get('mission', False) == True else 'normal'
                if name not in locker[type] and m.get('quantity', 0) > 0 or purchase.get('outstanding', 0) > 0:
                    locker[type][name] = {'locName': m.get('locName', name),
                                          'category': cat.title(),
                                          'stock': m.get('quantity', 0),
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

        self.data = data
        self.carrier_id = get_by_path(self.data, ['market', 'id'], 0)
        Debug.logger.debug(f"Updating carrier data CAPI {self.carrier_id}")

        # we can update all the local vars with this loop.
        updates:dict = {'name': [self.overview, ['name', 'vanityName'], "----"],
                        'currentStarSystem': [self.overview, ['currentStarSystem'], ''],
                        'dockingAccess': [self.overview, ['dockingAccess'], 'None'],
                        'state': [self.overview, ['state'], ''],
                        'carrier_id': [self.overview, ['market', 'id'], 0],
                        'shipPacks': [self.overview, ['capacity', 'shipPacks'], 0],
                        'modulePacks': [self.overview, ['capacity', 'modulePacks'], 0],
                        'crew': [self.overview, ['capacity', 'crew'], 0],
                        'callsign': [self.overview, ['name', 'callsign'], ''],
                        'notoriousAccess': [self.overview, ['notoriousAccess'], False],
                        'theme': [self.overview, ['theme'], ''],
                        'bankBalance': [self.overview, ['finance', 'bankBalance'], 0],
                        'bankReservedBalance': [self.overview, ['finance', 'bankReservedBalance'], 0],
                        'coreCost': [self.overview, ['finance', 'coreCost'], 0],
                        'servicesCost': [self.overview, ['finance', 'servicesCost'], 0],
                        'maintenance': [self.overview, ['finance', 'maintenance'], 0],
                        'jumpsCost': [self.overview, ['finance', 'jumpsCost'], 0],
                        'numJumps': [self.overview, ['finance', 'numJumps'], 0],
                        'taxation':  [self.overview, ['finance', 'taxation'], 0],
                        }
        for k, v in updates.items():
            v[0][k] = get_by_path(self.data, v[1], v[2])

        # Now deal with the exceptions.
        if self.overview.get('name', '') != updates['name'][2]:         # Name is encoded as hex string
            self.overview['name'] = bytes.fromhex(self.overview['name']).decode('utf-8')
        self.overview['fuel'] = int(self.data.get('fuel', 0))
        # Destination has the body as well so use that if we're in the same system.
        if self.overview.get('currentStarSystem', 'Unknown') in self.overview.get('jumpDestination', ''):
            self.overview['currentStarSystem'] = self.overview['jumpDestination']

        self.locker = self._update_locker(self.data)

        # Only use the CAPI data if we haven't docked in the last 15 minutes
        if self.last_modified > int(time.time()) - 900:
            Debug.logger.debug("Ignoring CAPI update")
            return

        # Do this here because we manage these locally and don't want to update them if the CAPI data may be out of date.
        for item in ['freeSpace', 'cargoForSale', 'cargoNotForSale', 'cargoSpaceReserved']:
            self.overview[item] = get_by_path(self.data, ['capacity', item], self.overview[item])

        self.cargo = self._update_cargo(self.data)


    @catch_exceptions
    def stats_received(self, entry: dict) -> None:
        """ The user entered the carrier management screen """
        if entry.get(KEY_CARRIER_TYPE) != FleetCarrierType.PERSONAL:
            return
        # Note we always re-populate here, in case the user has bought a new carrier. We should get a subsequent CAPI update to populate the rest.
        self.carrier_id = entry.get('CarrierID', 0)
        updates:dict = {'name': [self.overview, ['Name'], "----"],
                        'dockingAccess': [self.overview, ['DockingAccess'], 'None'],
                        'carrier_id': [self.overview, ['CarrierID'], 0],
                        'callsign': [self.overview, ['Callsign'], ''],
                        'notoriousAccess': [self.overview, ['AllowNotorious'], False],
                        'totalCapacity':  [self.overview, ['SpaceUsage', 'TotalCapacity'], 25000],
                        'shipPacks': [self.overview, ['SpaceUsage', 'ShipPacks'], 0],
                        'modulePacks': [self.overview, ['SpaceUsage', 'ModulePacks'], 0],
                        'crew': [self.overview, ['SpaceUsage', 'Crew'], 0],
                        'cargoSpaceReserved': [self.cargo['overview'], ['SpaceUsage', 'CargoSpaceReserved'], 0],
                        'freeSpace': [self.overview, ['SpaceUsage', 'FreeSpace'], 0],
                        'bankBalance': [self.overview, ['Finance', 'CarrierBalance'], 0],
                        'bankReservedBalance': [self.overview, ['Finance', 'ReserveBalance'], 0],
                        }
        for k, v in updates.items():
#            Debug.logger.debug(f"{v[0][k]} {v[1]} {v[2]} {get_by_path(entry, v[1], v[2])}")
            v[0][k] = get_by_path(entry, v[1], v[2])


    @catch_exceptions
    def jump_requested(self, entry: dict[str, str]) -> None:
        """ The user scheduled a carrier jump """
        # {"timestamp": "2020-04-20T09:30:58Z", "event": "CarrierJumpRequest", "CarrierID": 3700005632, "SystemName": "Paesui Xena", "Body": "Paesui Xena A", "SystemAddress": 7269634680241, "BodyID": 1, "DepartureTime":"2020-04-20T09:45:00Z"}

        if entry.get("CarrierID") != self.overview.get('carrier_id', ''): return
        l:str = self.bgstally.state.discord_lang
        title:str = __("Jump Scheduled for Carrier {carrier_name}", lang=l).format(carrier_name=self.overview.get('name', 0)) # LANG: Discord post title
        description:str = __("A carrier jump has been scheduled", lang=l) # LANG: Discord text

        departure_datetime: datetime|None = datetime.strptime(entry.get('DepartureTime', ""), DATETIME_FORMAT_JOURNAL)
        departure_datetime = departure_datetime.replace(tzinfo=UTC)

        fields:list = []
        fields.append({'name': __("From System", lang=l), 'value': self.data.get('currentStarSystem', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("To System", lang=l), 'value': entry.get('SystemName', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("To Body", lang=l), 'value': entry.get('Body', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("Departure Time", lang=l), 'value': f"<t:{round(departure_datetime.timestamp())}:R>"}) # LANG: Discord heading
        fields.append({'name': __("Docking", lang=l), 'value': self._readable(self.data.get('dockingAccess', ''), True), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("Notorious Access", lang=l), 'value': self._readable(self.data.get('notoriousAccess', False), False), 'inline': True}) # LANG: Discord heading
        self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_OPERATIONS, None)

        self.overview['departureScheduled'] = entry.get('DepartureTime', "")
        self.overview['jumpDestination'] = entry.get('Body', '') if entry.get('Body', '') != '' else entry.get('SystemName', '')


    @catch_exceptions
    def jump_cancelled(self, entry: dict[str, str]) -> None:
        """ The user cancelled their carrier jump """
        if entry.get("CarrierID") != self.overview.get('carrier_id', ''): return
        l:str = self.bgstally.state.discord_lang
        title:str = __("Jump Cancelled for Carrier {carrier_name}", lang=l).format(carrier_name=self.overview.get('name', 0)) # LANG: Discord post title
        description:str = __("The scheduled carrier jump was cancelled", lang=l) # LANG: Discord text

        self.overview['jumpDestination'] = None
        self.overview['departureScheduled'] = None

        fields:list = []
        fields.append({'name': __("Current System", lang=l), 'value': self.data.get('currentStarSystem', "Unknown"), 'inline': True})
        fields.append({'name': __("Docking", lang=l), 'value': self._readable(self.data.get('dockingAccess', ''), True), 'inline': True})
        fields.append({'name': __("Notorious Access", lang=l), 'value': self._readable(self.data.get('notoriousAccess', False), True), 'inline': True})
        self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_OPERATIONS, None)


    @catch_exceptions
    def trade_order(self, entry:dict) -> None:
        """ The user set a buy or sell order on their carrier """
        # { "timestamp":"2024-02-17T16:33:10Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"imperialslaves", "Commodity_Localised":"Imperial Slaves", "SaleOrder":10, "Price":1749300 }
        # { "timestamp":"2024-02-17T16:33:51Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"unstabledatacore", "Commodity_Localised":"Unstable Data Core", "PurchaseOrder":5, "Price":4516 }
        # { "timestamp":"2024-02-17T16:35:57Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"unstabledatacore", "Commodity_Localised":"Unstable Data Core", "CancelTrade":true }

        Debug.logger.debug(f"event: {entry}")
        if entry.get("CarrierID") != self.overview.get('carrier_id', ''): return
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

        if entry.get('SaleOrder') is not None and \
            self.cargo['normal'][comm]['stock'] != entry.get('SaleOrder', 0) : # Makes no difference to the amount of free space bu we may need to update the cargo qty if it's out of date.
            self.overview['freeSpace'] += (self.cargo['normal'][comm]['stock'] - entry.get('SaleOrder', 0))
            self.cargo['normal'][comm]['stock'] = entry.get('SaleOrder', 0)

        if entry.get('PurchaseOrder') is not None:
            # Reduce the space by the difference between previous and new order
            diff:int = self.cargo['normal'][comm]['buyTotal'] - entry.get('PurchaseOrder', 0)
            if self.cargo['overview'].get('cargoSpaceReserved', None) == None:
                self.cargo['overview']['cargoSpaceReserved'] = 0
            self.cargo['overview']['cargoSpaceReserved'] += diff
            self.overview['freeSpace'] -= diff
            self.cargo['normal'][comm]['buyTotal'] = entry.get('PurchaseOrder', 0)
            self.cargo['normal'][comm]['outstanding'] = entry.get('PurchaseOrder', 0)

        if entry.get('CancelTrade') == True:
            if self.cargo['overview'].get('cargoSpaceReserved', None) == None:
                self.cargo['overview']['cargoSpaceReserved'] = 0
            self.cargo['overview']['cargoSpaceReserved'] -= min(self.cargo['normal'][comm]['outstanding'], self.overview['cargoSpaceReserved'])
            self.overview['freeSpace'] += min(self.cargo['normal'][comm]['outstanding'], self.overview['cargoSpaceReserved'])
            self.cargo['normal'][comm]['buyTotal'] = 0
            self.cargo['normal'][comm]['outstanding'] = 0
            self.cargo['normal'][comm]['price'] = 0

        Debug.logger.debug(f"Updated cargo: {self.cargo['normal'][comm]}")
        # I don't like this, I don't know another way to notify progress that the orders have changed.
        if self.bgstally.ui.window_progress: self.bgstally.ui.window_progress.update_display()


    @catch_exceptions
    def market(self, entry: dict) -> None:
        """ Market event. If it's for our carrier we update the cargo amounts using BGS-Tally's copy of the market data"""
        if entry.get("MarketID") != self.overview.get('carrier_id', ''): return
        self.last_modified = int(time.time())

        Debug.logger.debug(f"Market event {entry}")

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

            # Buying and someone else must have sold to us, so increase stock based on demand changes
            if item.get('Consumer', False) == True and int(item.get('Demand', 0)) != int(self.cargo['normal'][comm]['outstanding']):
                diff:int = int(item.get('Demand', 0)) - int(self.cargo['normal'][comm]['outstanding'])
                self.overview['cargoSpaceReserved'] += diff
                self.cargo['normal'][comm]['stock'] -= min(diff, self.cargo['normal'][comm]['stock'])
                self.cargo['normal'][comm]['outstanding'] = int(item.get('Demand', 0))
                self.cargo['normal'][comm]['price'] = int(item.get('SellPrice', 0)) # Price player sells at

            # We get stock so we can update with this.
            if item.get('Producer', False) == True:
                diff:int = self.cargo['normal'][comm]['stock'] - int(item.get('Stock', 0))
                self.overview['freeSpace'] -= diff
                self.cargo['normal'][comm]['stock'] = int(item.get('Stock', 0))
                self.cargo['normal'][comm]['price'] = int(item.get('BuyPrice', 0)) # Price player buys at

        if self.bgstally.market.available(entry.get("MarketID")) == False:
            return

        for comm, deets in self.cargo['normal'].items():
            if deets['outstanding'] > 0 and comm not in self.bgstally.market.commodities.keys():
                Debug.logger.debug(f"Buy order completed or removed for {comm} {self.bgstally.market.commodities.items()}")
                deets['outstanding'] = 0
                deets['price'] = 0

            if deets['price'] > 0 and deets['stock'] > 0 and comm not in self.bgstally.market.commodities.keys():
                Debug.logger.debug(f"It's all been bought for {comm} {self.bgstally.market.commodities.items()}")
                self.overview['freeSpace'] += deets['stock']
                deets['stock'] = 0
                deets['price'] = 0
        Debug.logger.debug(f"Market updated")


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
                self.overview['freeSpace'] -= min(int(i.get('Count', 0)), self.overview['freeSpace'])
                if self.cargo['normal'][comm]['price'] != 0:
                    if self.cargo['normal'][comm]['outstanding'] == 0: # Selling?
                        self.cargo['overview']['cargoForSale'] += int(entry.get('Count', 0))
                    else:
                        self.cargo['overview']['cargoNotForSale'] += min(int(entry.get('Count', 0)), self.cargo['overview']['cargoNotForSale'])
                self.cargo['normal'][comm]['stock'] += int(i.get('Count', 0))

            if i.get('Direction') == 'toship':
                self.overview['freeSpace'] += int(i.get('Count', 0))
                if self.cargo['normal'][comm]['price'] != 0:
                    if self.cargo['normal'][comm]['outstanding'] == 0: # Selling?
                        self.cargo['overview']['cargoForSale'] -= int(entry.get('Count', 0))
                    else:
                        self.cargo['overview']['cargoNotForSale'] -= min(int(entry.get('Count', 0)), self.cargo['overview']['cargoNotForSale'])
                self.cargo['normal'][comm]['stock'] -= min(int(i.get('Count', 0)), self.cargo['normal'][comm]['stock'])
            Debug.logger.debug(f"Updated cargo: {self.cargo['normal'][comm]}")


    @catch_exceptions
    def market_activity(self, entry:dict) -> None:
        ''' We bought or sold to/from our carrier '''
        if entry.get('MarketID') != self.overview.get('carrier_id', ''): return
        self.last_modified = int(time.time())

        #{ "timestamp":"2025-09-18T23:39:55Z", "event":"MarketBuy", "MarketID":3709409280, "Type":"fruitandvegetables", "Type_Localised":"Fruit and Vegetables", "Count":195, "BuyPrice":483, "TotalCost":94185 }
        comm:str = entry.get('Type', "").lower()
        if comm not in self.cargo['normal']:
            self.cargo['normal'][comm] = {
                'locName': self.bgstally.ui.commodities.get(comm, {}).get('Name', entry.get('Type_Localised', comm)),
                'category': self.bgstally.ui.commoditiesget(comm, {}).get('Category', 'Unknown'),
                'stock': 0,
                'buyTotal': 0,
                'outstanding': 0,
                'price': 0}

        if entry.get('event') == "MarketBuy": # Someone bought from us, we sold to them
            Debug.logger.debug(f"Market buy: changed free space by {int(entry.get('Count', 0))} stock by -{min(entry.get('Count', 0), self.cargo['normal'][comm]['stock'])} set price to {entry.get('SellPrice', self.cargo['normal'][comm]['price'])}")
            self.overview['freeSpace'] += int(entry.get('Count', 0))
            self.cargo['overview']['cargoForSale'] -= int(entry.get('Count', 0))
            self.cargo['normal'][comm]['stock'] -= min(entry.get('Count', 0), self.cargo['normal'][comm]['stock'])
            self.cargo['normal'][comm]['price'] = entry.get('BuyPrice', self.cargo['normal'][comm]['price'])

        if entry.get('event') == "MarketSell": # We bought from someone
            Debug.logger.debug(f"Market sell: changed outstanding by -{min(entry.get('Count', 0), self.cargo['normal'][comm]['outstanding'])} stock by {entry.get('Count', 0)} set price to {entry.get('SellPrice', self.cargo['normal'][comm]['price'])}")
            self.cargo['overview']['cargoSpaceReserved'] -= min(entry.get('Count', 0), self.cargo['normal'][comm]['outstanding'])
            self.cargo['overview']['cargoNotForSale'] += min(entry.get('Count', 0), self.cargo['normal'][comm]['outstanding'])
            self.cargo['normal'][comm]['outstanding'] -= min(entry.get('Count', 0), self.cargo['normal'][comm]['outstanding'])
            self.cargo['normal'][comm]['stock'] += entry.get('Count', 0)
            self.cargo['normal'][comm]['price'] = entry.get('SellPrice', self.cargo['normal'][comm]['price'])

        Debug.logger.debug(f"Updated cargo ({entry.get('event')}): {self.cargo['normal'][comm]}")


    @catch_exceptions
    def _readable(self, field:str, discord:bool = False) -> str:
        """ Return a human-readable format of various attributes """
        val:str = self.readable.get(field, "") if self.readable.get(field, None) != None else str(field)
        return __(val, lang=self.bgstally.state.discord_lang) if discord else _(val)


    def _get_items(self, category:FleetCarrierItemType|None = None) -> tuple[list|dict|None, str|None, str|None, str|None]:
        """Return the current items list, lookup name key, display name key and quantity key for the specified category

        Args:
            category (FleetCarrierItemType, optional): The type of item to fetch. Defaults to None.

        Returns:
            tuple[list|None, str|None, str|None, str|None]: Tuple containing the four items
        """

        Debug.logger.debug(f"Getting items for category {category}")
        match category:
            case FleetCarrierItemType.MATERIALS_SELLING:
                return self.locker, 'name', 'locName', 'stock'
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
                return self.locker, 'name', 'locName', 'stock'
            case _:
                return None, None, None, None


    def _as_dict(self) -> dict:
        """ Return a Dictionary representation of our data, suitable for serializing """
        return {
            'carrier_id': self.carrier_id,
            'overview': self.overview,
            'cargo': self.cargo,
            'locker': self.locker,
            'data': self.data
            }


    def _from_dict(self, dict: dict) -> None:
        """ Populate our data from a Dictionary that has been deserialized """
        Debug.logger.debug(f"Loading _from_dict")
        self.carrier_id = dict.get('carrier_id', 0)
        self.overview = dict.get('overview', {})
        self.cargo = dict.get('cargo', {})
        if 'normal' not in self.cargo: self.cargo = {'overview': {}, 'stolen': {}, 'mission': {}, 'normal': {}} # For migration from old to new format
        self.locker = dict.get('locker', {})
        if 'normal' not in self.locker: self.locker = {'overview': {}, 'mission': {}, 'normal': {}} # For migration from old to new format
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
                    self.overview = {}
                elif self.overview.get('callsign', None) != get_by_path(self.data, ['name', 'callsign']):
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
trans:list[str] = [
    _("All"), # LANG: Carrier all access
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