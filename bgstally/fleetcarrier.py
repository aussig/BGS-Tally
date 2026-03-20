import json
from datetime import UTC, datetime, timedelta
import time
import requests
from os import path
from copy import deepcopy

#from bgstally.bgstally import BGSTally
from bgstally.constants import DATETIME_FORMAT_JOURNAL, DATETIME_FORMAT_JSON, FOLDER_OTHER_DATA, DiscordChannel, FleetCarrierType
from bgstally.debug import Debug
from bgstally.utils import _, __, get_by_path, catch_exceptions
from thirdparty.colors import *

FILENAME = "fleetcarrier.json"
FC_MAX_SHIPS = 40
FC_MAX_JUMPS_TRACKED = 100
FDEV_SLACKING_TIME = 1800 # How long behind CAPI may be in seconds
SPANSH_ROUTE = "https://spansh.co.uk/api/fleetcarrier/route"
class FleetCarrier:
    """
    Used to store, track and return fleetcarrier data.
    Data is received from the FDev CAPI and from carrierstats events.
    Activity is also tracked through sell, buy, market, order, carrier jump and shipyard events
    since the CAPI is queried infrequently and can be unhelpfully out of date.
    Some data is managed and updated locally to work around the CAPI data being out of date.
    """
    def __init__(self, bgstally) -> None:
        self.bgstally:BGSTally = bgstally # type: ignore

        self.carrier_id:int = 0
        self.overview:dict = {} # Top level data
        self.locker:dict = {} # Local copy of locker data
        self.cargo:dict = {} # Local copy of cargo data
        self.itinerary:list = [] # Local copy of jump data
        self.route:list = [] # Planned route
        self.shipyard:dict = {} # Local copy of shipyard data
        self.last_modified:int = 0 # Record of when we last modified our local data. Used to avoid overwriting with out of date CAPI data.
        self.data:dict = {}  # Raw CAPI data
        self.load()


    @catch_exceptions
    def available(self) -> bool:
        """ Return true if there is data available on a Fleet Carrier """
        return self.overview.get('name', None) is not None and self.overview.get('callsign', None) is not None


    # UI get methods
    @catch_exceptions
    def get_overview(self) -> dict:
        """ Return the carrier overview as key value pairs """

        itinerary:list = self.itinerary
        arrival:str = itinerary[-1].get('arrivalTime', "") if len(itinerary) > 0 else ''

        return {
            _('Name'): self.overview.get('name', ''),                                    # LANG: Carrier overview
            _('Callsign'): self.overview.get('callsign', ''),                            # LANG: Carrier overview
            _('Location'): self.overview.get('currentBody', self.overview.get('currentStarSystem', '')), # LANG: Carrier overview

            _('Arrival'): (arrival, 'datetime', 'Unknown'),                              # LANG: Carrier overview
            _('Docking'): (self._readable(self.overview.get('dockingAccess', '')), 'str', 'Unknown'), # LANG: Carrier overview
            _('Allow Notorious'): (self.overview.get('notoriousAccess', ''), 'str', 'Unknown'), # LANG: Carrier overview

            _('Fuel'): (self.overview.get('fuel', 0), 'num', 0, 't'),                    # LANG: Carrier overview
            _('Space'): (f"{self._get_freespace():,}t ({int(self._get_freespace() * 100 / self.overview.get('totalCapacity', 25000))}%)", 'fixed'), # LANG: Carrier overview
            _('Tax Level'): (self.overview.get('taxation', 0), 'num', '0%', '%'),        # LANG: Carrier overview
        }


    @catch_exceptions
    def get_summary(self) -> dict:
        """
        Return summary information as a dictionary. The summary is different to other tabs in that it's just a group of
        key value pairs, there's no table of detailed listings
        """
        summary:dict = {'finances': [], 'costs': [], 'capacity': []}

        summary['finances'] = {
            _('Bank Balance'): self.overview.get('bankBalance', 0),           # LANG: Carrier summary
            _('Bank Reserve'): self.overview.get('bankReservedBalance', 0),   # LANG: Carrier summary
            _('Available Balance'): self.overview.get('bankBalance', 0)-self.overview.get('bankReservedBalance', 0), # LANG: Carrier summary
            _('Reserve Percentage'): (round((self.overview.get('bankReservedBalance', 0) * 100) / self.overview.get('bankBalance', 1)), 'num', 0, '%')# LANG: Carrier summary
        }

        summary['costs'] = {
            _('Total'): self.overview.get('maintenance', 0),                   # LANG: Carrier summary
            _('Core Cost'): self.overview.get('coreCost', 0),                  # LANG: Carrier summary
            _('Services Cost'): self.overview.get('servicesCost', 0),          # LANG: Carrier summary
            _('Jump Cost'): (get_by_path(self.data, ["finance", "numJumps"], 0) * 100000, 'num', 0),   # LANG: Carrier summary
        }

        summary['capacity'] = {
            _('Total Capacity'): (self.overview.get('totalCapacity', 25000), 'num', 'Unknown', 't'),   # LANG: Carrier summary
            _('Total Used'): (self._get_usedspace(), 'num', '0t', 't'), # LANG: Carrier summary
            _('Free Space'): (self._get_freespace(), 'num', '0t', 't'), # LANG: Carrier summary

            _('Cargo For Sale'): (self._get_forsale(), 'num', '0t', 't'), # LANG: Carrier summary
            _('Cargo Not For Sale'): (self._get_notforsale(), 'num', '0t', 't'), # LANG: Carrier summary
            _('Cargo Reserved Space'): (self._get_reserved(), 'num', '0t', 't'), # LANG: Carrier summary

            _('Crew') : (self.overview.get('crew', 0), 'num', 'Unknown', 't'), # LANG: Carrier summary
            _('Ship Packs'): (self.overview.get('shipPacks', 0), 'num', '0t', 't'), # LANG: Carrier summary
            _('Module Packs'): (self.overview.get('modulePacks', 0), 'num', '0t', 't'), # LANG: Carrier summary
        }
        return summary


    @catch_exceptions
    def get_services(self) -> dict:
        """
        Return services as a dictionary. The overview is a set of key value pairs and
        the crew is a list of crew members with their details to be displayed in a treeviewplus table.
        """
        services:dict = {'overview': {}, 'crew': {}}
        services['overview'] = {
            _('Weekly Cost'): get_by_path(self.data, ["finance", "servicesCost"], 0), # LANG: Carrier services
            _('Cost to date'): get_by_path(self.data, ["finance", "servicesCostToDate"], 0),# LANG: Carrier services
            _('Crew Capacity'): get_by_path(self.data, ["capacity", "crew"], 0), # LANG: Carrier services
        }
        crew:dict = get_by_path(self.data, ['servicesCrew'], {}) # Detailed crew information
        for k, v in get_by_path(self.data, ["market", "services"], {}).items(): # List of all services and their status

            services['crew'][k] = deepcopy(crew.get(k, {}).get('crewMember', {}))
            services['crew'][k]['enabled'] = (services['crew'].get(k, {}).get('enabled', 'No').title(), 'str', 'No')

            services['crew'][k]['status'] = v
            services['crew'][k]['taxation'] = (get_by_path(self.data, ['finance', 'service_taxation', k], 0), 'num', '0%', '%')
        return services


    @catch_exceptions
    def get_cargo(self, type:str='all') -> dict:
        """
        Return cargo as a dictionary. Overview is a set of key value pairs and
        inventory is a list of commodities with details to be displayed in a treeviewplus table.
        """

        comm:dict = {}
        selling:int = 0
        nosale:int = 0
        stored:int = 0
        reserved:int = 0
        for t, ent in self.cargo.items():
            if t == 'overview' or (type != 'all' and type != t): continue
            for name, deets in ent.items():
                deets['locName'] = self.bgstally.ui.commodities.get(name, {}).get('Name', name)
                deets['category'] = self.bgstally.ui.commodities.get(name, {}).get('Category', '') if isinstance(self.bgstally.ui.commodities.get(name, {}).get('Category', ''), str) else 'Unknown'
                deets['mission'] = (t == 'mission')
                deets['stolen'] = (t == 'stolen')
                comm[name] = deets
        comm = dict(sorted(comm.items(), key=lambda item: item[1]['category']+','+item[1]['locName']))

        summ:dict = {
            _("Space") : (self._get_freespace() + self._get_marketused() + self._get_reserved(), 'num', 'Unknown', 't'), # LANG: Carrier cargo
            _("Used") : (self._get_marketused() + self._get_reserved(), 'num', '0t', 't'),                   # LANG: Carrier cargo
            _("Stored") : (self._get_marketused(), 'num', '0t', 't'),                          # LANG: Carrier cargo
            _("Reserved") : (self._get_reserved(), 'num', '0t', 't'),                      # LANG: Carrier cargo
            _("Selling") : (self._get_forsale(), 'num', '0t', 't'),                        # LANG: Carrier cargo
            _("Buying") : (self._get_reserved(), 'num', '0t', 't'),                        # LANG: Carrier cargo
            _('Total Value') : get_by_path(self.data, ["marketFinances", "cargoTotalValue"], 0), # LANG: Carrier cargo
            _('Profit') : get_by_path(self.data, ["marketFinances", "allTimeProfit"], 'None'), # LANG: Carrier cargo
        }
        return {'overview': summ, 'inventory': comm}


    @catch_exceptions
    def get_locker(self) -> dict:
        """
        Return locker as a dictionary. overview is a set of key value pairs and
        inventory is a list of microresources with details to be displayed in a treeviewplus table.
        """
        res:dict = {}
        buying:int = 0
        selling:int = 0
        stored:int = 0
        for t, ent in self.locker.items():
            for mat, deets in ent.items():
                deets['mission'] = (t == 'mission')
                buying += deets.get('outstanding', 0)
                if deets['outstanding'] == 0 and deets['price'] > 0 and (t == 'normal'):
                    selling += deets.get('stock', 0)
                stored += deets.get('stock', 0)
                res[mat] = deets
        res = dict(sorted(res.items(), key=lambda item: item[1]['category']+','+item[1]['locName']))

        summ:dict = {}
        if get_by_path(self.data, ["finance", "bartender"], None ) != None:
            summ = {
                _('Space') : get_by_path(self.data, ["capacity", "microresourceCapacityTotal"], 0), # LANG: Carrier locker
                _('Used') : get_by_path(self.data, ["capacity", "microresourceCapacityUsed"], 0), # LANG: Carrier locker
                _('Stored') : stored,                                          # LANG: Carrier locker
                _('Reserved') : get_by_path(self.data, ["capacity", "microresourceCapacityReserved"], 0), # LANG: Carrier locker
                _('Selling') : selling,                                        # LANG: Carrier locker
                _('Buying') : buying,                                          # LANG: Carrier locker
                _('Total Value') : get_by_path(self.data, ["finance", "bartender", "microresourcesTotalValue"], 0), # LANG: Carrier locker
                _('Profit') : get_by_path(self.data, ["finance", "bartender", "allTimeProfit"], 'None'), # LANG: Carrier locker
            }
        return {'overview': summ, 'inventory': res}


    @catch_exceptions
    def get_itinerary(self) -> dict:
        """
        Return the carrier itinerary. Overview is key value pairs,
        completed and route are lists of jumps (completed and planned) to be displayed in treeviewplus tables.
        """

        route:list = []
        tot:int = 0
        depot:int = int(self.overview.get('fuel', 0))
        trit:int = int(get_by_path(self.cargo, ['normal', 'tritium', 'stock'], 0))
        deposit:bool = False
        for j in self.route:
            tot += int(j.get('fuel_used'))
            if depot < int(j.get('fuel_used')):
                trit -= (1000 - depot)
                depot = 1000
                deposit = True
            depot -= int(j.get('fuel_used'))

            route.append({
                'distance': (int(j.get('distance',0)), 'num'),
                'distance_to_destination': (int(j.get('distance_to_destination',0)), 'num'),
                'fuel_used': (int(j.get('fuel_used')), 'num'),
                'fuel_in_depot': (depot, 'num'),
                'deposit': (deposit, 'boolean'),
                'tritium': (trit, 'num'),
                'refuel': (trit < 0, 'boolean'),
                'state': 'planned',
                'starsystem': (j.get('name'), 'str')
            })
            deposit = False

        jumps:list = []
        for j in self.itinerary:
            # Seems body can sometimes end up as null
            body:str = j.get('body', '') or ''

            jumps.append({
                'arrivalTime': (self._lt(j.get('arrivalTime', '')), 'datetime', 'Unknown'),
                'departureTime': (self._lt(j.get('departureTime', '')), 'datetime', ''),
                'state': (j.get('state',''), 'str', 'Unknown'),
                'visitDurationSeconds': (j.get('visitDurationSeconds', 0), 'interval', ''),
                'starsystem': (j.get('starsystem', ''), 'str', 'Unknown'),
                'body': body.replace(j.get('starsystem', ''), '')
            })

        summ:dict = {}

        if route != []: # Only show route summary if there is a route planned
            summ[_("Route Destination")] = route[-1].get('starsystem',"") # LANG: Carrier itinerary
            summ[_("Departure")] = ("", 'str', "Unscheduled")                   # LANG: Carrier itinerary
            summ[_("Distance")] = (int(self.route[0].get('distance_to_destination', 0)+self.route[0].get('distance', 0)), 'num', 'Unknown', 'Ly')   # LANG: Carrier itinerary
            summ[_("Fuel Required")] = (tot, 'num', 'Unknown', 't')                             # LANG: Carrier itinerary

        summ[_('Scheduled Jump')] = (self.overview.get('jumpDestinationBody', self.overview.get('jumpDestination', 'None')), 'str', 'None') # LANG: Carrier itinerary
        summ[_('Departure Time')] = (self._lt(self.overview.get('departureScheduled', '')), 'datetime', 'None') # LANG: Carrier itinerary
        summ[_('Fuel')] = (self.overview.get('fuel', 0), 'num', '0t', 't')       # LANG: Carrier itinerary
        summ[_('Tritium')] = (get_by_path(self.cargo, ['normal', 'tritium', 'stock'], 0), 'num', '0t', 't') # LANG: Carrier itinerary

        return {'overview': summ, 'route': route, 'completed': jumps}


    @catch_exceptions
    def get_shipyard(self) -> dict:
        """
        Return the carrier shipyard. Overview is a set of key value pairs and
        ships is a list of ships with details to be displayed in a treeviewplus table.
        """
        summ:dict = {
            _('Maximum Ships'): FC_MAX_SHIPS,                                  # LANG: Carrier shipyard
            _('Stored Ships'): self.shipyard.get('overview', {}).get('shipCount', 'None'), # LANG: Carrier shipyard
            _('Total Value'): self.shipyard.get('overview', {}).get('totalValue', 'None') # LANG: Carrier shipyard
        }
        ships:list = []
        for id, s in self.shipyard.get('ships', {}).items():
            ships.append({
                'name': (s.get('name', ''), 'name', 'None'),
                'type': (s.get('type', ''), 'name', 'Unknown'),
                'location': (s.get('location', ''), 'name', 'Unknown'),
                'value': (s.get('value', 0), 'num', 0),
                'transferTime': (s.get('transferTime', 0), 'interval'),
                'transferPrice': (s.get('transferPrice', 0), 'num'),
                'hot': (s.get('hot', False), 'bool'),
            })
        return {'overview': summ, 'ships': ships}


    # UI Operations
    @catch_exceptions
    def spansh_route(self, dest:str) -> None:
        """ Create and store a Spansh fleetcarrier route """
        # Request:
        #   source=Bleae+Thua+NI-B+b27-5&
        #   destinations=Apurui&
        #   capacity=25000&
        #   mass=25000&
        #   capacity_used=17579&
        #   calculate_starting_fuel=1
        # Response:
        #   {"job":"3B517F04-CDB2-11F0-A808-D8E8969359E6","status":"queued"}
        #
        # GET https://spansh.co.uk/api/results/3B517F04-CDB2-11F0-A808-D8E8969359E6
        # Response:
        #   {"job":"3B517F04-CDB2-11F0-A808-D8E8969359E6",
        # "parameters":{"calculate_starting_fuel":1,"capacity":25000,"capacity_used":17579,"current_fuel":0,"destination_systems":["Apurui"],"mass":25000,"refuel_destinations":[],"source_system":"Bleae Thua NI-B b27-5","tritium_amount":0},
        # "state":"started","status":"queued"}
        #
        # {"job":"3B517F04-CDB2-11F0-A808-D8E8969359E6",
        # "parameters":{"calculate_starting_fuel":1,"capacity":25000,"capacity_used":17579,"current_fuel":0,"destination_systems":["Apurui"],"mass":25000,"refuel_destinations":[],"source_system":"Bleae Thua NI-B b27-5","tritium_amount":0},
        # "result":{"calculate_starting_fuel":true,"capacity":25000,"capacity_used":17579,"destinations":["Apurui"],"fuel_loaded":0,
        # "jumps":[{"distance":0,"distance_to_destination":2025.11992724544,"fuel_in_tank":468,"fuel_used":0,"has_icy_ring":false,"id64":11663386487017,"is_desired_destination":1,"is_system_pristine":false,"must_restock":1,"name":"Bleae Thua NI-B b27-5","restock_amount":468,"tritium_in_market":0,"x":-200.25,"y":20.6875,"z":2082.4375},{"distance":499.052589718446,"distance_to_destination":1526.54724595756,"fuel_in_tank":356,"fuel_used":112,"has_icy_ring":true,"id64":83651204114,"is_desired_destination":0,"is_system_pristine":true,"must_restock":0,"name":"Bleae Thua MN-W c1-0","restock_amount":0,"tritium_in_market":0,"x":-111.15625,"y":6.96875,"z":1591.59375},{"distance":499.97798193708,"distance_to_destination":1026.98374443227,"fuel_in_tank":244,"fuel_used":112,"has_icy_ring":false,"id64":22953915731648,"is_desired_destination":0,"is_system_pristine":false,"must_restock":0,"name":"M7 Sector RP-V a32-1","restock_amount":0,"tritium_in_market":0,"x":-53.5625,"y":-33.09375,"z":1096.5625},{"distance":499.887685627669,"distance_to_destination":527.979466819319,"fuel_in_tank":132,"fuel_used":112,"has_icy_ring":false,"id64":58147951365432,"is_desired_destination":0,"is_system_pristine":false,"must_restock":0,"name":"Col 359 Sector SJ-Y a45-3","restock_amount":0,"tritium_in_market":0,"x":37.59375,"y":-43,"z":605.15625},{"distance":499.33503829468,"distance_to_destination":68.911947043401,"fuel_in_tank":20,"fuel_used":112,"has_icy_ring":true,"id64":5070611162585,"is_desired_destination":0,"is_system_pristine":false,"must_restock":0,"name":"Garoju","restock_amount":0,"tritium_in_market":0,"x":122.03125,"y":-126.1875,"z":120.09375},{"distance":68.911947043401,"distance_to_destination":0,"fuel_in_tank":0,"fuel_used":20,"has_icy_ring":true,"id64":7505757278946,"is_desired_destination":1,"is_system_pristine":false,"must_restock":0,"name":"Apurui","restock_amount":0,"tritium_in_market":0,"x":96.21875,"y":-75.3125,"z":81.4375}],"mass":25000,"refuel_destinations":[],"source":"Bleae Thua NI-B b27-5","tritium_stored":0},
        # "state":"completed","status":"ok"}
        params:dict = {
            "source": self.overview.get('currentStarSystem'),
            "destinations": dest,
            "capacity": self.overview.get('totalCapacity', 25000),
            "mass": self.overview.get('totalCapacity', 25000),
            "capacity_used": self._get_usedspace(), # Maybe this shouldn't include reserved?
            "calculate_starting_fuel": 0,
            "fuel_loaded": self.overview.get('fuel', 1000),
            "tritium_stored" : get_by_path(self.cargo, ['normal', 'tritium', 'stock'], 0)
            }
        res:requests.Response = requests.post(SPANSH_ROUTE, params=params, headers={'User-Agent': f"BGSTally/{self.bgstally.version}"})
        if res.status_code != 202:
            Debug.logger.info(f"Spansh error: {res}")
            return

        # We get back a jobid
        content:dict = json.loads(res.content)
        job:str = content.get('job', '')

        # Then we wait for the job to finish.
        tries:int = 0
        while(tries < 20):
            jobresp:requests.Response = requests.get(f"https://spansh.co.uk/api/results/{job}", timeout=5)
            if jobresp.status_code != 202:
                break
            tries += 1
            time.sleep(1)

        if jobresp.status_code != 200:
            Debug.logger.debug(f"{jobresp} {params}")
            return

        # Store the route, drop the first entry as that's our current location
        route:list = get_by_path(json.loads(jobresp.content), ['result', 'jumps'], {})
        self.route = route[1:]


    def clear_route(self) -> None:
        """ Remove the current route """
        self.route = []
        self.bgstally.ui.window_fc.update_display()


    def _update_route(self, dest:str) -> None:
        """ Remove any route entries that we aren't at.
        If we remove all of them that's ok because the route is invalid. """

        # This shouldn't happen unless we've made some jumps without ED:MC running
        used:int = 0
        while self.route != [] and self.route[0]['name'] != dest:
            used += self.route[0]['fuel_used']
            self.route = self.route[1:]
        # If we're there take it out.
        if self.route != [] and self.route[0]['name'] == dest:
            self.overview['fuel'] -= used + self.route[0]['fuel_used']
            self.route = self.route[1:]

        # And put the next stop in the clipboard
        if self.route != []:
            Debug.logger.debug(f"Copying {self.route[0]['name']} to clipboard")
            self.bgstally.ui.frame.clipboard_clear()
            self.bgstally.ui.frame.clipboard_append(self.route[0]['name'])
            self.bgstally.ui.frame.update()
        self.bgstally.ui.window_fc.update_display()


    def _update_cargo(self, data:dict) -> dict:
        """ Update cargo data from CAPI data structure """

        # @TODO: Add blackmarket sales
        cargo:dict = {'overview': {}, 'stolen': {}, 'mission': {}, 'normal': {}}

        # Sometimes we have timing issues getting commodity details from the UI so we need to catch exceptions here.
        comms:dict = {}
        try:
            comms = self.bgstally.ui.commodities
        except Exception as e:
            Debug.logger.error(f"Error getting commodity details {e}")

        for c in get_by_path(data, ['cargo'], []):
            cname:str = c.get('commodity', "").lower()
            stolen:bool = c.get('stolen', False)
            mission:bool = c.get('mission', False)

            #Debug.logger.debug(f"Initial cargo: {self.cargo['normal'].get(cname, {})}")
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
            if cargo['normal'][cname]['stock'] < 0:
                Debug.logger.error(f"Negative stock {cargo['normal'][cname]}")
            #else:
                #Debug.logger.debug(f"Final cargo: {cargo['normal'][cname]}")

        return cargo


    def _update_itinerary(self, data: dict) -> list:
        """ Update our local itinerary data from CAPI data structure """

        Debug.logger.debug(f"Updating itinerary")
        jumplist:list = self.itinerary

        for jump in deepcopy(get_by_path(data, ['itinerary', 'completed'], [])):
            elem:int = next((index for (index, d) in enumerate(self.itinerary) if d['arrivalTime'] == jump.get('arrivalTime', '')), -1)

            if elem > 0: # Found it, and it's an "old" one. Update departure time and duration just in case
                jumplist[elem]['departureTime'] = jump.get('departureTime', jumplist[elem].get('departureTime', None))
                jumplist[elem]['visitDurationSeconds'] = jump.get('visitDurationSeconds', jumplist[elem].get('visitDurationSeconds', 0))
                continue

            if elem == 0:
                if jump.get('departureTime', None) != None:
                    jumplist[elem]['departureTime'] = jump.get('departureTime', jumplist[elem].get('departureTime', None))
                    jumplist[elem]['visitDurationSeconds'] = jump.get('visitDurationSeconds', 0)
                    continue

                if self.overview.get('departureScheduled', None) != None:
                    jumplist[elem]['departureTime'] = self.overview['departureScheduled']
                    # @TODO: Calculate duration?
                    continue

                if jumplist[elem]['starsystem'] == self.overview.get('currentStarSystem', '') and self.overview.get('currentBody', '') != '':
                    jumplist[elem]['body'] = self.overview['currentBody']
                continue

            # Not found

            # Already completed, and nothing scheduled so just add it with its details
            if jump.get('departureTime', None) != None:
                jumplist.insert(0, jump)
                continue

            if self.overview.get('departureScheduled', None) == None:
                if jump['starsystem'] == self.overview.get('currentStarSystem', '') and self.overview.get('currentBody', '') != '':
                    jump['body'] = self.overview.get('currentBody', None)
                jumplist.insert(0, jump)
                continue

            # Check if the jump time has passed. If not nothing to do
            if self._time_passed(self.overview['departureScheduled']) == False:
                continue

            if jump['starsystem'] == self.overview.get('jumpDestination', ''):
                jump['body'] = self.overview.get('jumpDestinationBody', None)

            jumplist.insert(0, jump)

            self.overview['jumpDestination'] = None
            self.overview['jumpDestinationBody'] = None
            self.overview['departureScheduled'] = None

        jumplist = sorted(jumplist, key=lambda item: datetime.strptime(item['arrivalTime'], DATETIME_FORMAT_JSON), reverse=True)

        return jumplist[0:FC_MAX_JUMPS_TRACKED]


    def _update_locker(self, data: dict) -> dict:
        """ Update locker data from CAPI data structure """

        locker:dict = {'mission' : {}, 'normal' : {}}
        for cat, v in get_by_path(data, ['carrierLocker'], {}).items():
            for m in v:
                name:str = m.get('name', "").lower()
                # all the ways a commodity may be listed in CAPI data

                # Sale seems to switch from list to dict.
                sale:dict = {}
                if isinstance(get_by_path(data, ['orders', 'onfootmicroresources', 'sales'], {}), dict):
                    tmp:dict = get_by_path(data, ['orders', 'onfootmicroresources', 'sales'], {})
                    sale = next((item for id, item in tmp.items() if item.get('name', "").lower() == name), {})
                else:
                    sale = next((item for item in get_by_path(data, ['orders', 'onfootmicroresources', 'sales'], []) if item.get('name', "").lower() == name), {})

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


    # Journal event and CAPI data update methods
    @catch_exceptions
    def update(self, data: dict) -> None:
        """ Store the latest data from CAPI, called when new data is received """

        # Data directly from CAPI response. This is only received for personal carriers. Structure documented here:
        # https://github.com/EDCD/FDevIDs/blob/master/Frontier%20API/FrontierDevelopments-CAPI-endpoints.md#fleetcarrier

        # Store the whole data structure for later use
        self.data = data
        self.carrier_id = get_by_path(self.data, ['market', 'id'], 0)
        Debug.logger.debug(f"Received CAPI data {self.carrier_id}")

        # we can update most of the local vars with this loop.
        updates:dict = {'name': [self.overview, ['name', 'vanityName'], "----"],
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

        # If we don't know where we are trust the CAPI.
        if self.overview.get('currentStarSystem', None) == None:
            self.overview['currentStarSystem'] = get_by_path(self.data, ['currentStarSystem'], '')
            del self.overview['currentBody']

        # If we have a body but it doesn't match the system, clear it.
        if self.overview.get('currentBody', None) != None and self.overview.get('currentStarSystem', '') not in self.overview.get('currentBody', None):
            Debug.logger.debug(f"System and body mismatch {self.overview.get('currentStarSystem', '')} vs {self.overview.get('currentBody', None)}, clearing body")
            del self.overview['currentBody']

        self.locker = self._update_locker(self.data)
        self.itinerary = self._update_itinerary(self.data)

        # All the following are time sensitive or updated locally
        # so only use the CAPI data for them if we haven't docked in the last N seconds
        if self.last_modified > int(time.time()) - FDEV_SLACKING_TIME:
            Debug.logger.debug("Ignoring CAPI cargo update")
            self.bgstally.ui.window_fc.update_display()
            return

        Debug.logger.debug(f"CAPI cargo update now: {int(time.time())} last mod: {self.last_modified} diff: {int(time.time()) - FDEV_SLACKING_TIME}")
        self.cargo = self._update_cargo(self.data)
        self.bgstally.ui.window_fc.update_display()


    @catch_exceptions
    def stats_received(self, entry: dict) -> None:
        """ The user entered the carrier management screen generating a CarrierStats event """

        if entry.get('CarrierType') != FleetCarrierType.PERSONAL: return

        # Note we always re-populate here, in case the user has bought a new carrier.
        # We should get a subsequent CAPI update to populate the rest.
        self.carrier_id = entry.get('CarrierID', 0)

        # A list of local values to update from the event
        updates:dict = {'name': [self.overview, ['Name'], "----"],
                        'dockingAccess': [self.overview, ['DockingAccess'], 'None'],
                        'carrier_id': [self.overview, ['CarrierID'], 0],
                        'callsign': [self.overview, ['Callsign'], ''],
                        'notoriousAccess': [self.overview, ['AllowNotorious'], False],
                        'totalCapacity':  [self.overview, ['SpaceUsage', 'TotalCapacity'], 25000],
                        'shipPacks': [self.overview, ['SpaceUsage', 'ShipPacks'], 0],
                        'modulePacks': [self.overview, ['SpaceUsage', 'ModulePacks'], 0],
                        'crew': [self.overview, ['SpaceUsage', 'Crew'], 0],
                        'bankBalance': [self.overview, ['Finance', 'CarrierBalance'], 0],
                        'bankReservedBalance': [self.overview, ['Finance', 'ReserveBalance'], 0],
                        }
        for k, v in updates.items():
            v[0][k] = get_by_path(entry, v[1], v[2])

        # Not sure if we want to do this here but the sanity check should help keep it honest
        #self.last_modified = int(time.time())

        # Sanity check
        if get_by_path(entry, ['SpaceUsage', 'FreeSpace'], 0) != self._get_freespace() or \
            get_by_path(entry, ['SpaceUsage', 'CargoSpaceReserved']) != self._get_reserved():
            Debug.logger.error(f"Carrier space mismatch, clearing modification time")
            self.last_modified = 0

        #self.itinerary = self._update_itinerary(self.data)
        if self.bgstally.dev_mode == True: self.save()
        self.bgstally.ui.window_fc.update_display()


    @catch_exceptions
    def jump_requested(self, entry:dict[str, str]) -> None:
        """ The user scheduled a carrier jump generating a CarrierJumpRequest event """
        # @TODO: Add posting to https://fleetcarrier.space/?
        # All that's required is a POST to https://fleetcarrier.space/my_carrier with
        # {
        #        "cmdr": ,
        #        "system": ,
        #        "station": ,
        #        "data": ,
        #        "is_beta": ,
        #        "user": ,
        #        "key": ,
        #    }
        # {"timestamp": "2020-04-20T09:30:58Z", "event": "CarrierJumpRequest", "CarrierID": 3700005632, "SystemName": "Paesui Xena", "Body": "Paesui Xena A", "SystemAddress": 7269634680241, "BodyID": 1, "DepartureTime":"2020-04-20T09:45:00Z"}

        Debug.logger.info(f"Carrier: {self.overview.get('carrier_id', '')} {entry.get('CarrierID')}")
        if entry.get("CarrierID") != self.overview.get('carrier_id', ''): return

        departure_datetime: datetime|None = datetime.strptime(entry.get('DepartureTime', ""), DATETIME_FORMAT_JOURNAL)
        departure_datetime = departure_datetime.replace(tzinfo=UTC)
        self.overview['jumpDestination'] = entry.get('SystemName', '')
        self.overview['jumpDestinationBody'] = entry.get('Body', None)
        self.overview['departureScheduled'] = departure_datetime.strftime("%Y-%m-%d %H:%M:00") # Seconds zeroed out
        if self.itinerary[0].get('departureTime', None) == None:
            self.itinerary[0]['starsystem'] = self.overview.get('currentStarSystem', '')
            self.itinerary[0]['body'] = self.overview.get('currentBody', None)
            self.itinerary[0]['departureTime'] = departure_datetime.strftime("%Y-%m-%d %H:%M:00")

        # Automatically post to whichever discord webhooks are set for carrier operations
        # the discord class handles where and whether to post
        l:str|None = self.bgstally.state.discord_lang
        title:str = __("Jump Scheduled for Carrier {carrier_name}", lang=l).format(carrier_name=self.overview.get('name', 0)) # LANG: Discord post title
        description:str = __("A carrier jump has been scheduled", lang=l) # LANG: Discord text

        fields:list = []
        fields.append({'name': __("From System", lang=l), 'value': self.data.get('currentStarSystem', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("To System", lang=l), 'value': entry.get('SystemName', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("To Body", lang=l), 'value': entry.get('Body', "Unknown"), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("Departure Time", lang=l), 'value': f"<t:{round(departure_datetime.timestamp())}:R>"}) # LANG: Discord heading
        fields.append({'name': __("Docking", lang=l), 'value': self._readable(self.data.get('dockingAccess', ''), True), 'inline': True}) # LANG: Discord heading
        fields.append({'name': __("Notorious Access", lang=l), 'value': self._readable(self.data.get('notoriousAccess', False), False), 'inline': True}) # LANG: Discord heading
        self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_OPERATIONS, None)

        if self.bgstally.dev_mode == True: self.save()
        self.bgstally.ui.window_fc.update_display()


    @catch_exceptions
    def jump_cancelled(self, entry: dict[str, str]) -> None:
        """ The user cancelled their carrier jump producing a CarrierJumpCancelled journal event """
        if entry.get("CarrierID") != self.overview.get('carrier_id', ''): return


        if self.itinerary[0]['departureTime'] == self.overview['departureScheduled']:
            self.itinerary[0]['departureTime'] = None

        self.overview['jumpDestination'] = None
        self.overview['jumpDestinationBody'] = None
        self.overview['departureScheduled'] = None

        if self.bgstally.dev_mode == True: self.save()

        # Automatically post to whichever discord webhooks are set for carrier operations
        # the discord class handles where and whether to post
        l:str|None = self.bgstally.state.discord_lang
        title:str = __("Jump Cancelled for Carrier {carrier_name}", lang=l).format(carrier_name=self.overview.get('name', 0)) # LANG: Discord post title
        description:str = __("The scheduled carrier jump was cancelled", lang=l) # LANG: Discord text

        fields:list = []
        fields.append({'name': __("Current System", lang=l), 'value': self.data.get('currentStarSystem', "Unknown"), 'inline': True}) # LANG: Fleet Carrier Discord heading
        fields.append({'name': __("Docking", lang=l), 'value': self._readable(self.data.get('dockingAccess', ''), True), 'inline': True}) # LANG: Fleet Carrier Discord heading
        fields.append({'name': __("Notorious Access", lang=l), 'value': self._readable(self.data.get('notoriousAccess', False), True), 'inline': True}) # LANG: Fleet Carrier Discord heading
        self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_OPERATIONS, None)
        self.bgstally.ui.window_fc.update_display()


    @catch_exceptions
    def carrier_location(self, entry:dict) -> None:
        """ Update the current carrier location after a jump. If we logged out we may not get this event """
        if entry.get("CarrierID") != self.overview.get('carrier_id', ''): return

        # Check if the jump time is now or has passed.
        if self._time_passed(self.overview.get('departureScheduled', "")) == False:
            return

        dest:str = self.overview.get('jumpDestination', '')

        # We've already got this new jump
        if self.itinerary[1].get('departureTime', None) == self.overview['departureScheduled']:
            self.itinerary[1]['starsystem'] = dest
            self.itinerary[1]['body'] = self.overview.get('jumpDestinationBody', None)

        if self.itinerary[0].get('departureTime', None) == None: # If we haven't received a new itinerary update the current one
            dept:datetime = datetime.strptime(self.overview['departureScheduled'], DATETIME_FORMAT_JSON)
            arr:datetime = datetime.strptime(self.itinerary[0]['arrivalTime'], DATETIME_FORMAT_JSON)
            diff:timedelta = dept - arr
            self.itinerary[0]['starsystem'] = self.overview.get('currentStarSystem', '')
            self.itinerary[0]['body'] = self.overview.get('currentBody', None)
            self.itinerary[0]['departureTime'] = self.overview['departureScheduled']
            self.itinerary[0]['visitDurationSeconds'] = int(diff.total_seconds())

        if self.itinerary[0]['starsystem'] != dest:
            self.itinerary.insert(0, {
                                      'departureTime': None,
                                      'arrivalTime': self.overview['departureScheduled'],
                                      'state': "success",
                                      'visitDurationSeconds': 0,
                                      'starsystem': self.overview.get('jumpDestination', ''),
                                      'body': self.overview.get('jumpDestinationBody', None)
                                      })

        self._update_route(dest)

        # Update our location and clear the jump
        self.overview['currentStarSystem'] = self.overview.get('jumpDestination', '')
        self.overview['currentBody'] = self.overview.get('jumpDestinationBody', None)
        self.overview['jumpDestination'] = None
        self.overview['jumpDestinationBody'] = None
        self.overview['departureScheduled'] = None

        self.bgstally.ui.window_fc.update_display()
        if self.bgstally.dev_mode == True: self.save()


    @catch_exceptions
    def deposit_fuel(self, entry:dict) -> None:
        """ Update our fuel tank, there has been a deposit """
        if entry.get("CarrierID") != self.overview.get('carrier_id', ''): return
        self.overview['fuel'] = entry.get('Total', 1000)
        self.bgstally.ui.window_fc.update_display()


    @catch_exceptions
    def trade_order(self, entry:dict) -> None:
        """ The user set a buy or sell order on their carrier """
        # { "timestamp":"2024-02-17T16:33:10Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"imperialslaves", "Commodity_Localised":"Imperial Slaves", "SaleOrder":10, "Price":1749300 }
        # { "timestamp":"2024-02-17T16:33:51Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"unstabledatacore", "Commodity_Localised":"Unstable Data Core", "PurchaseOrder":5, "Price":4516 }
        # { "timestamp":"2024-02-17T16:35:57Z", "event":"CarrierTradeOrder", "CarrierID":3703308032, "BlackMarket":false, "Commodity":"unstabledatacore", "Commodity_Localised":"Unstable Data Core", "CancelTrade":true }

        if entry.get("CarrierID") != self.overview.get('carrier_id', ''): return
        # @NOTE: Not sure if we need this update to last_modified.
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
                # If we were selling we need to clear any existing buy order and free up reserved space
                self.locker['normal'][mat]['outstanding'] = 0
                self.locker['normal'][mat]['buyTotal'] = 0

                self.locker['normal'][mat]['stock'] = entry.get('SaleOrder', 0)
                self.locker['normal'][mat]['price'] = entry.get('Price', 0)

            if entry.get('PurchaseOrder') is not None:
                # Set price and stock
                self.locker['normal'][mat]['buyTotal'] = int(entry.get('PurchaseOrder', 0))
                self.locker['normal'][mat]['outstanding'] = int(entry.get('PurchaseOrder', 0))
                self.locker['normal'][mat]['price'] = int(entry.get('Price', 0))

            if entry.get('CancelTrade') == True:
                self.locker['normal'][mat]['buyTotal'] = 0
                self.locker['normal'][mat]['outstanding'] = 0
                self.locker['normal'][mat]['price'] = 0

            self.bgstally.ui.window_fc.update_display()
            if self.bgstally.dev_mode == True: self.save()
            return

        # A new commodity order
        if comm not in self.cargo['normal']:
            self.cargo['normal'][comm] = self._init_cargo_item(comm, entry.get('Commodity_Localised', comm))
            self.cargo['normal'][comm]['price'] = entry.get('Price', 0)

        if entry.get('SaleOrder') is not None:
            # If we were selling we need to clear any existing buy order and free up reserved space
            self.cargo['normal'][comm]['outstanding'] = 0
            self.cargo['normal'][comm]['buyTotal'] = 0

            # Set price and stock
            self.cargo['normal'][comm]['stock'] = entry.get('SaleOrder', 0)
            self.cargo['normal'][comm]['price'] = entry.get('Price', 0)

        if entry.get('PurchaseOrder') is not None:
            self.cargo['normal'][comm]['buyTotal'] = entry.get('PurchaseOrder', 0)
            self.cargo['normal'][comm]['outstanding'] = entry.get('PurchaseOrder', 0)
            self.cargo['normal'][comm]['price'] = entry.get('Price', 0)

        if entry.get('CancelTrade') == True:
            self.cargo['normal'][comm]['outstanding'] = 0
            self.cargo['normal'][comm]['buyTotal'] = 0
            self.cargo['normal'][comm]['price'] = 0

        if self.cargo['normal'][comm]['stock'] < 0:
            Debug.logger.error(f"Negative stock {self.cargo['normal'][comm]}")
            self.cargo['normal'][comm]['stock'] = 0
            self.last_modified = 0

        self.bgstally.ui.window_fc.update_display()
        if self.bgstally.dev_mode == True: self.save()


    @catch_exceptions
    def market(self, entry: dict) -> None:
        """ Market event. If it's for our carrier we update the cargo amounts using BGS-Tally's copy of the market data"""
        if entry.get("MarketID") != self.overview.get('carrier_id', ''): return
        self.last_modified = int(time.time())

        if not self.bgstally.market.available(entry.get("MarketID", 0)):
            Debug.logger.debug(f"No market data available for CarrierID {entry.get('MarketID')}")
            return

        for comm, item in self.bgstally.market.commodities.items():
            if comm not in self.cargo['normal']:
                self.cargo['normal'][comm] = self._init_cargo_item(comm)

            # Buying and the demand has changed
            if item.get('Consumer', False) == True and int(item.get('Demand', 0)) != int(self.cargo['normal'][comm]['outstanding']):
                Debug.logger.debug(f"Adjusting due to change in demand {self.cargo['normal'][comm]['outstanding']} {item.get('Demand', 0)}")
                diff:int = int(self.cargo['normal'][comm]['outstanding']) - int(item.get('Demand', 0))
                self.cargo['normal'][comm]['stock'] += diff
                if self.cargo['normal'][comm]['stock'] < 0: self.cargo['normal'][comm]['stock'] = 0
                self.cargo['normal'][comm]['outstanding'] = int(item.get('Demand', 0))
                self.cargo['normal'][comm]['price'] = int(item.get('SellPrice', 0)) # Price player sells at

            # Selling and our stock has changed
            if item.get('Producer', False) == True and \
                (int(item.get('Stock', 0)) != self.cargo['normal'][comm]['stock'] or int(item.get('BuyPrice', 0)) != self.cargo['normal'][comm]['price']):
                Debug.logger.debug(f"Adjusting due to change in stock {self.cargo['normal'][comm]['stock']} {item.get('Stock', 0)}")
                self.cargo['normal'][comm]['stock'] = int(item.get('Stock', 0))
                self.cargo['normal'][comm]['price'] = int(item.get('BuyPrice', 0)) # Price player buys at

            if self.cargo['normal'][comm]['stock'] < 0:
                Debug.logger.error(f"Negative stock {self.cargo['normal'][comm]}")
                self.cargo['normal'][comm]['stock'] = 0
                self.last_modified = 0

        # Now check for completed orders by going through all the cargo and find any commodities
        # for sale or purchase that are no longer in the market data.
        # For buys that means the buy order completed because we'd have had a trade order event otherwise.
        # For sells it means we sold all our stock because we'd have had a trade order event otherwise.
        for comm, deets in self.cargo['normal'].items():
            # If we're still buying or selling this or we never were then nothing to do here.
            if comm in self.bgstally.market.commodities.keys() or deets['price'] == 0: continue

            if deets['outstanding'] > 0: # We were buying but someone must have completed the buy order
                deets['outstanding'] = 0
                deets['buyTotal'] = 0
                deets['price'] = 0
            elif deets['stock'] > 0: # We were selling, someone must have bought all our stock
                deets['stock'] = 0
                deets['price'] = 0

        self.bgstally.ui.window_fc.update_display()
        if self.bgstally.dev_mode == True: self.save()


    @catch_exceptions
    def cargo_transfer(self, entry:dict) -> None:
        """ The user transferred cargo to or from the carrier generating a CargoTransfer event """
        # { "timestamp":"2025-03-22T15:15:21Z", "event":"CargoTransfer", "Transfers":[ { "Type":"steel", "Count":728, "Direction":"toship" }, { "Type":"titanium", "Count":56, "Direction":"toship" } ] }
        self.last_modified = int(time.time())

        for i in entry.get('Transfers', []):
            comm:str = i.get('Type', "").lower()
            if comm not in self.cargo['normal']:
                self.cargo['normal'][comm] = self._init_cargo_item(comm)

            # Transfer amount is positive if to carrier, negative if from carrier
            amt:int = i.get('Count', 0) if i.get('Direction') == 'tocarrier' else -i.get('Count', 0)
            self.cargo['normal'][comm]['stock'] += amt

            if self.cargo['normal'][comm]['stock'] < 0:
                Debug.logger.error(f"Negative stock {self.cargo['normal'][comm]}")
                self.cargo['normal'][comm]['stock'] = 0
                self.last_modified = 0

        self.bgstally.ui.window_fc.update_display()
        if self.bgstally.dev_mode == True: self.save()


    @catch_exceptions
    def market_activity(self, entry:dict) -> None:
        ''' We bought or sold to/from our carrier '''
        if entry.get('MarketID') != self.overview.get('carrier_id', ''): return
        self.last_modified = int(time.time())

        #{ "timestamp":"2025-09-18T23:39:55Z", "event":"MarketBuy", "MarketID":3709409280, "Type":"fruitandvegetables", "Type_Localised":"Fruit and Vegetables", "Count":195, "BuyPrice":483, "TotalCost":94185 }
        comm:str = entry.get('Type', "").lower()
        if comm not in self.cargo['normal']:
            self.cargo['normal'][comm] = self._init_cargo_item(comm, entry.get('Type_Localised', comm))

        # Sale amount is positive if to carrier, negative if from carrier (MarketSell to carrier, MarketBuy from carrier)
        amt:int = entry.get('Count', 0) if entry.get('event') == 'MarketSell' else -entry.get('Count', 0)

        if self.cargo['normal'][comm]['outstanding'] > 0: # Buying
            self.cargo['normal'][comm]['outstanding'] -= amt
            # Finished.
            if self.cargo['normal'][comm]['outstanding'] == 0:
                self.cargo['normal'][comm]['price'] = 0
                self.cargo['normal'][comm]['buyTotal'] = 0
        elif self.cargo['normal'][comm]['stock'] + amt == 0: # Selling & all sold
            self.cargo['normal'][comm]['price'] = 0

        self.cargo['normal'][comm]['stock'] += amt

        if self.cargo['normal'][comm]['stock'] < 0:
            Debug.logger.error(f"Negative stock {self.cargo['normal'][comm]}")
            self.cargo['normal'][comm]['stock'] = 0

        self.bgstally.ui.window_fc.update_display()
        if self.bgstally.dev_mode == True: self.save()


    @catch_exceptions
    def shipyard_event(self, entry:dict) -> None:
        """
        The user viewed the carrier shipyard
        StoredShips event happens before the ship is actually stored.
        The subsequent ShipyardSwap doesn't include all the ship details so we have to keep a record of all ships.
        """

        match entry.get('event', ''):
            case 'Shipyard':
                self.shipyard['overview']['current'] = 'Carrier' if entry.get('MarketID') == self.overview.get('carrier_id', '') else entry.get('StarSystem', 'Unknown')

            case 'ShipyardSwap' if self.shipyard.get('ships', {}).get('ShipID', None) != None:
                self.shipyard['ships'][entry.get('ShipID', 0)]['location'] = self.shipyard['overview']['current']

            case 'ShipyardTransfer':
                self.shipyard['ships'][str(entry.get('ShipID', ""))]['location'] = _('In Transit')  # LANG: Fleet carrier, ship in transit

            case 'StoredShips':
                carrier_count:int = 0
                total_value:int = 0
                for ship in entry.get('ShipsHere', []) + entry.get('ShipsRemote', []):
                    self.shipyard['ships'][str(ship.get('ShipID', ""))] = {
                        'name': ship.get('Name', ''),
                        'type': ship.get('ShipType_Localised', ship.get('ShipType', '')),
                        'location': 'Carrier' if ship.get('ShipMarketID', entry.get('MarketID', 0)) == self.carrier_id else ship.get('StarSystem', entry.get('StarSystem', self.shipyard.get('overview', {}).get('current', _('Unknown')))), # LANG: Fleet carrier, unknown location
                        'value': ship.get('Value', 0),
                        'transferPrice': ship.get('TransferPrice', 0),
                        'transferTime': ship.get('TransferTime', 0),
                        'hot': ship.get('Hot', False)
                    }
                    if ship.get('ShipMarketID', entry.get('MarketID', 0)) == self.carrier_id: carrier_count += 1
                    total_value += ship.get('Value', 0)
                self.shipyard['overview']['shipCount'] = carrier_count
                self.shipyard['overview']['totalValue'] = total_value

        self.bgstally.ui.window_fc.update_display()
        if self.bgstally.dev_mode == True: self.save()


    def _time_passed(self, tstr:str|None) -> bool:
        if tstr == None or tstr == "": return False
        then:datetime = datetime.strptime(tstr, DATETIME_FORMAT_JSON)
        then = then.replace(tzinfo=UTC).astimezone(None)
        now:datetime = datetime.now()
        now = now.astimezone(None)
        return now >= then


    def _lt(self, tstr:str|None, fmt:str = DATETIME_FORMAT_JSON) -> str|None:
        """ Convert a UTC datetime string into a local datetime string """
        if tstr == None: return ''
        try:
            t:datetime = datetime.strptime(tstr, fmt).replace(tzinfo=UTC)
            return t.astimezone(None).strftime(DATETIME_FORMAT_JSON)
        except Exception as e:
            Debug.logger.error(f"Error parsing time {tstr} {e}")
            return ''


    def _get_forsale(self) -> int:
        ### Return the amount of cargo for sale on the carrier. ###

        # For sale is price > 0, buyOrder = 0, and only normal cargo.
        return sum([c.get('stock', 0) for c in self.cargo.get('normal', {}).values() if c.get('price') > 0 and c.get('outstanding') == 0])


    def _get_notforsale(self) -> int:
        ### Return the amount of cargo not for sale on the carrier. ###

        # Not For sale is any cargo with price = 0
        return sum([c.get('stock', 0) for c in self.cargo.get('normal', {}).values() if c.get('price', 0) == 0 or c.get('outstanding', 0) > 0] +
                   [c.get('stock', 0) for c in self.cargo.get('stolen', {}).values() if c.get('price', 0) == 0 or c.get('outstanding', 0) > 0] +
                   [c.get('stock', 0) for c in self.cargo.get('mission', {}).values() if c.get('price', 0) == 0 or c.get('outstanding', 0) > 0])


    def _get_marketused(self) -> int:
        """ Return the amount of carrier space used by cargo """
        return self._get_forsale() + self._get_notforsale()


    def _get_reserved(self) -> int:
        """ Return the amount of cargo space reserved on the carrier. """
        # Reserved is any cargo with price > 0 and outstanding > 0
        return sum([c.get('outstanding', 0) for c in self.cargo.get('normal', {}).values() if c.get('price', 0) > 0 and c.get('outstanding', 0) > 0])


    def _get_usedspace(self) -> int:
        """ All space used on the carrier """
        return self.overview.get('crew', 0) + \
                self.overview.get('ShipPacks', 0) + \
                self.overview.get('modulePacks', 0) + \
                self._get_marketused() + \
                self._get_reserved()


    def _get_freespace(self) -> int:
        ### Return the amount of free cargo space on the carrier. ###
        return self.overview.get('totalCapacity', 25000) - self._get_usedspace()


    def _readable(self, field:str, discord:bool = False) -> str:
        """ Return translated, human-readable versions of various attributes """
        lang:str|None = self.bgstally.state.discord_lang
        readable:dict = {"all": ["All", _("All"), __("All", lang=lang)], # LANG: Readable carrier states
                        "squadronfriends": ["Squadron and Friends", _("Squadron and Friends"), __("Squadron and Friends", lang=lang)],  # LANG: Readable carrier states
                        "friends" : ["Friends", _("Friends"), __("Friends", lang=lang)], # LANG: Readable carrier states
                        "normalOperation": ["Normal", _("Normal"), __("Normal", lang=lang)],  # LANG: Readable carrier states
                        "debtState": ["Offline", _("Offline"), __("Offline", lang=lang)],  # LANG: Readable carrier states
                        "pendingDecommission": ["Decommissioning", _("Decommissioning"), __("Decommissioning", lang=lang)], # LANG: Readable carrier states
                        "SearchAndRescue": ["Search and Rescue", _("Search and Rescue"), __("Search and Rescue", lang=lang)],  # LANG: Readable carrier states
                        "Mining": ["Miner", _("Miner"), __("Miner", lang=lang)],  # LANG: Readable carrier states
                        "Trader" : ["Trader", _("Trader"), __("Trader", lang=lang)],  # LANG: Readable carrier states
                        "Explorer" : ["Explorer", _("Explorer"), __("Explorer", lang=lang)], # LANG: Readable carrier states
                        "AntiXeno": ["Xeno Hunter", _("Xeno Hunter"), __("Xeno Hunter", lang=lang)],  # LANG: Readable carrier states
                        "BountyHunter": ["Bounty Hunter", _("Bounty Hunter"), __("Bounty Hunter", lang=lang)] # LANG: Readable carrier states
                        }
        map:list = readable.get(field, [])
        if discord == False:
            return map[1] if map != [] else str(field)
        return map[2] if map != [] else str(field)


    def _init_cargo_item(self, item:str, alt:str = "") -> dict:
        """ Initialize a cargo item structure """
        if alt == "": alt = item
        return {
            'locName': self.bgstally.ui.commodities[item].get('Name', alt),
            'category': self.bgstally.ui.commodities[item].get('Category', 'Unknown'),
            'stock': 0,
            'buyTotal': 0,
            'outstanding': 0,
            'price': 0
            }


    def _as_dict(self) -> dict:
        """ Return a Dictionary representation of our data, suitable for serializing """
        return {
            'carrier_id': self.carrier_id,
            'last_modified': self.last_modified,
            'overview': self.overview,
            'cargo': self.cargo,
            'locker': self.locker,
            'itinerary': self.itinerary,
            'route': self.route,
            'shipyard': self.shipyard,
            'data': self.data
            }


    def _from_dict(self, dict: dict) -> None:
        """ Populate our data from a Dictionary that has been deserialized """
        self.carrier_id = dict.get('carrier_id', 0)
        self.last_modified = dict.get('last_modified', 0)
        self.overview = dict.get('overview', {})
        self.cargo = dict.get('cargo', {})
        if 'normal' not in self.cargo: self.cargo = {'overview': {}, 'stolen': {}, 'mission': {}, 'normal': {}} # For migration from old to new format
        self.locker = dict.get('locker', {})
        if 'normal' not in self.locker: self.locker = {'overview': {}, 'mission': {}, 'normal': {}} # For migration from old to new format
        if isinstance(self.locker, list): self.locker = {} # For migration from old to new format
        self.itinerary = dict.get('itinerary', [])
        self.route = dict.get('route', [])
        self.shipyard = dict.get('shipyard', {})
        if 'overview' not in self.shipyard: self.shipyard = {'overview' : {}, 'ships': {}}
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
                    self.cargo = {'overview' : {}, 'normal': {}, 'stolen': {}, 'mission':{}}
                    self.locker = {'normal': {}, 'mission': {}}
                    self.itinerary = []
                    self.route = []
                elif self.overview.get('callsign', None) != get_by_path(self.data, ['name', 'callsign']):
                    # The CAPI callsign doesn't match our stored callsign, so re-parse the CAPI data. This is to clear up
                    # the problem where a squadron carrier was accidentally stored as a personal one, overwriting the user's
                    # actual personal carrier data.
                    self.update(self.data)


    @catch_exceptions
    def save(self) -> None:
        """ Save state to file """
        ind:int = 4 if self.bgstally.dev_mode == True else 0
        file:str = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self._as_dict(), outfile, indent=ind)
