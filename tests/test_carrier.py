"""
Test suite for EDMC plugins using pytest.

Run with: .venv/bin/python -m pytest tests/test_plugin.py -v --tb=short 2>&1 | tail -30
Run with: .venv_win\\Scripts\\python.exe -m pytest tests\\test_plugin.py -v --tb=short
"""

import pytest # type: ignore
import shutil
from pathlib import Path
from typing import Generator
from time import sleep
from unittest.mock import Mock, patch, MagicMock

import filecmp
from datetime import UTC, datetime, timedelta

from harness import TestHarness

@pytest.fixture
def harness() -> Generator:
    """ Provide a fresh test harness for each test. """  
    test_harness = TestHarness() 
    test_harness.set_edmc_config()

    # Use the "normal" locations for assets and data
    import bgstally.constants
    bgstally.constants.FOLDER_ASSETS = "../assets"
    bgstally.constants.FOLDER_DATA = "../data"

    # Make sure we always start with a consistent fleetcarrier.json
    shutil.copy(Path(__file__).parent / "config" / "fleetcarrier_init.json", 
                Path(__file__).parent / "otherdata" / "fleetcarrier.json")

    # Now we can import Router modules
    from load import plugin_start3, plugin_app, journal_entry
    import bgstally.globals
    test_harness.plugin = bgstally.globals.this
    
    plugin_start3(str(test_harness.plugin_dir))
    plugin_app(test_harness.parent)
    
    test_harness.load_events("journal_events.json")
    test_harness.register_journal_handler(journal_entry, 'Testy', 'Sol', False)

    # Used in event firing
    test_harness.commander = 'Testy'
    test_harness.is_beta = False

    yield test_harness

class TestCarrierInitialization:
    def test_available_no_data(self, harness) -> None:
        """ Test available() with no carrier data """
        fc = harness.plugin.fleet_carrier
        fc.overview = {} # Clear any existing data
        assert not fc.available()

    def test_available_with_data(self, harness) -> None:
        """ Test available() with carrier data """
        fc = harness.plugin.fleet_carrier
        fc.overview = {'name': 'Test Carrier', 'callsign': 'ABC-123'}
        assert fc.available()

    def test_available_missing_name(self, harness) -> None:
        """ Test available() with missing name """
        fc = harness.plugin.fleet_carrier
        fc.overview = {'callsign': 'ABC-123'}
        assert not fc.available()

    def test_available_missing_callsign(self, harness) -> None:
        """ Test available() with missing callsign """
        fc = harness.plugin.fleet_carrier
        fc.overview = {'name': 'Test Carrier'}
        assert not fc.available()

class TestCarrierUIDataMethods:
    """ Test the methods used by the UI to retrieve carrier data """
    def test_get_overview(self, harness) -> None:
        """ Test get_overview() method """
        fc = harness.plugin.fleet_carrier
        
        data:dict = fc.get_overview()        

        assert data['Name'] == 'Testy MctestFace'
        assert data['Callsign'] == 'T3S-TY'
        assert data['Fuel'][0] == 1000


    def test_get_summary(self, harness) -> None:
        """ Test get_summary() method """
        fc = harness.plugin.fleet_carrier
        fc.overview = {
            'bankBalance': 1000000,
            'bankReservedBalance': 200000,
            'maintenance': 50000,
            'coreCost': 20000,
            'servicesCost': 15000,
            'totalCapacity': 25000,
            'crew': 50,
            'shipPacks': 10,
            'modulePacks': 5
        }
        fc.data = {
            'finance': {'numJumps': 5}
        }

        summary = fc.get_summary()
        assert 'finances' in summary
        assert 'costs' in summary
        assert 'capacity' in summary

    def test_get_cargo(self, harness) -> None:
        """ Test get_cargo() method """
        fc = harness.plugin.fleet_carrier
        fc.cargo = {
            'normal': {
                'tritium': {'stock': 100, 'price': 1000, 'outstanding': 0, 'category': 'Chemicals'},
                'steel': {'stock': 50, 'price': 0, 'outstanding': 0, 'category': 'Metals'}
            },
            'stolen': {
                'fruitandvegetables': {'stock': 25, 'price': 0, 'outstanding': 0, 'category': 'Foods'}
            }
        }

        cargo = fc.get_cargo()
        assert 'overview' in cargo
        assert 'inventory' in cargo
        assert len(cargo['inventory']) == 3

    def test_get_locker(self, harness) -> None:
        """ Test get_locker() method """
        fc = harness.plugin.fleet_carrier
        fc.locker = {
            'normal': {
                'tritium': {'stock': 10, 'price': 1000, 'outstanding': 5, 'category': 'Chemicals', 'locName': 'Tritium'},
                'steel': {'stock': 20, 'price': 500, 'outstanding': 0, 'category': 'Metals', 'locName': 'Steel'}
            }
        }
        fc.data = {
            'capacity': {'microresourceCapacityTotal': 100, 'microresourceCapacityUsed': 30, 'microresourceCapacityReserved': 5},
            'finance': {'bartender': {'microresourcesTotalValue': 15000, 'allTimeProfit': 5000}}
        }

        locker = fc.get_locker()
        assert 'overview' in locker
        assert 'inventory' in locker

    def test_get_itinerary(self, harness) -> None:
        """ Test get_itinerary() method """
        fc = harness.plugin.fleet_carrier
        fc.overview = {
            'currentStarSystem': 'Sol',
            'jumpDestination': 'Alpha Centauri',
            'jumpDestinationBody': 'Alpha Centauri A',
            'departureScheduled': '2024-01-01T12:00:00Z',
            'fuel': 1000
        }
        fc.cargo = {'normal': {'tritium': {'stock': 500}}}
        fc.route = [
            {'name': 'Sol', 'distance': 0, 'distance_to_destination': 4.37, 'fuel_used': 50},
            {'name': 'Alpha Centauri', 'distance': 4.37, 'distance_to_destination': 0, 'fuel_used': 100}
        ]
        fc.itinerary = [
            {'arrivalTime': '2024-01-01T10:00:00Z', 'departureTime': '2024-01-01T11:00:00Z', 'state': 'success', 'visitDurationSeconds': 3600, 'starsystem': 'Sol', 'body': 'Earth'}
        ]

        itinerary = fc.get_itinerary()
        assert 'overview' in itinerary
        assert 'route' in itinerary
        assert 'completed' in itinerary

    def test_get_shipyard(self, harness) -> None:
        """ Test get_shipyard() method """
        fc = harness.plugin.fleet_carrier
        fc.shipyard = {
            'overview': {'shipCount': 5, 'totalValue': 1000000},
            'ships': {
                '1': {'name': 'Ship1', 'type': 'Eagle', 'location': 'Carrier', 'value': 50000, 'transferTime': 0, 'transferPrice': 0, 'hot': False}
            }
        }

        shipyard = fc.get_shipyard()
        assert 'overview' in shipyard
        assert 'ships' in shipyard
        assert shipyard['overview']['Maximum Ships'] == 40
class TestCarrierJumps:
    """ Test fleet carrier functions """

    def test_jump_request(self, harness) -> None:
        """ Test handling a jump request """
        fc = harness.plugin.fleet_carrier
        # Read the carrier events from the journal_events.json
        events:list = harness.events.get('carrier_events', [])

        # Pre-flight checks.         
        assert fc.overview.get('carrier_id') == 12345
        assert fc.overview.get('currentStarSystem', '') == 'Sol'
        
        # Send event 0
        harness.fire_event(events[0])
        
        # Confirm that the carrier's jump destination is now what the carrier event indicated.
        assert fc.overview.get('jumpDestination') == 'Bleae Thua ZE-I b23-1'
        assert fc.jump_state == 'Jumping'

        # Wait for the worker thread and see if the overlay message is set.
        sleep(2)
        assert harness.plugin.overlay.edmcoverlay.messages != {}

    def test_jump_completed(self, harness) -> None:
        """ Test a successful jump """      
        fc = harness.plugin.fleet_carrier  
        
        events:list = harness.events.get('carrier_events', [])        
        assert fc.overview.get('carrier_id') == 12345
        assert fc.overview.get('currentStarSystem', '') == 'Sol'
        
        harness.fire_event(events[0])
        assert fc.overview.get('jumpDestination') == 'Bleae Thua ZE-I b23-1'
        
        harness.fire_event(events[1])
        assert fc.overview.get('currentStarSystem', '') == 'Bleae Thua ZE-I b23-1'
        assert fc.jump_state == 'Cooldown'

        # Wait for the worker thread and see if the overlay message is set.
        sleep(2)
        assert harness.plugin.overlay.edmcoverlay.messages != {}

    def test_jump_cancellation(self, harness) -> None:
        """ A cancelled jump """
        fc = harness.plugin.fleet_carrier
        events:list = harness.events.get('carrier_events', [])
        
        assert fc.overview.get('carrier_id') == 12345
        assert fc.overview.get('currentStarSystem', '') == 'Sol'
        harness.fire_event(events[0])

        assert fc.overview.get('jumpDestination') == 'Bleae Thua ZE-I b23-1'
        
        harness.fire_event(events[2])
        assert fc.overview.get('currentStarSystem', '') == 'Sol'        
        assert fc.overview.get('jumpDestination') == None
        assert datetime.now(tz=UTC) + timedelta(seconds=58) <= fc.timer <= datetime.now(tz=UTC) + timedelta(seconds=60)
        assert fc.jump_state == 'Cooldown'

        # Wait for the worker thread and see if the overlay message is set.
        sleep(2)
        assert harness.plugin.overlay.edmcoverlay.messages != {}


    def test_update_overlay_idle(self, harness) -> None:
        """ Test update_overlay() when idle """
        fc = harness.plugin.fleet_carrier
        message = fc.update_overlay()
        assert message == "<H>"
class TestCarrierRoute:
    """ Test the Spansh Routing """

    def test_clear_route(self, harness) -> None:
        """ Test clear_route() method """
        fc = harness.plugin.fleet_carrier
        fc.route = [{'name': 'Test System'}]

        fc.clear_route()

        assert fc.route == []
    
    def test_spansh_route(self, harness) -> None:
        """ Test spansh_route() method """
        fc = harness.plugin.fleet_carrier
        fc.overview = {
            'currentStarSystem': 'Sol',
            'totalCapacity': 25000,
            'fuel': 1000
        }
        fc.cargo = {'normal': {'tritium': {
                "locName": "tritium",
                "stock": 100,
                "buyTotal": 0,
                "outstanding": 0,
                "price": 0,
                "mission": False,
                "stolen": False
            }}}
        sleep(20)
        fc.spansh_route('Alpha Centauri')

        assert len(fc.route) == 1
        assert fc.route[0]['name'] == 'Alpha Centauri'

    def test_update_overlay_with_route(self, harness) -> None:
        """ Test update_overlay() with planned route """
        fc = harness.plugin.fleet_carrier
        fc.overview = {'currentStarSystem': 'Sol'}
        fc.route = [
            {'name': 'Sol'},
            {'name': 'Alpha Centauri'}
        ]

        message = fc.update_overlay()
        assert 'Route Next' in message

class TestCarrierTrade:
    def test_trade_order_sale(self, harness) -> None:
        """ Test trade_order() for sale order """
        fc = harness.plugin.fleet_carrier
        entry = {
            'event': 'CarrierTradeOrder',
            'CarrierID': 12345,
            'Commodity': 'tritium',
            'Commodity_Localised': 'Tritium',
            'SaleOrder': 100,
            'Price': 1000
        }
        
        free:int = fc._get_freespace()

        fc.trade_order(entry)

        assert 'tritium' in fc.cargo['normal']
        assert fc.cargo['normal']['tritium']['stock'] == 100
        assert fc.cargo['normal']['tritium']['price'] == 1000
        assert fc._get_freespace() == free - 100
        
    def test_trade_order_purchase(self, harness) -> None:
        """ Test trade_order() for purchase order """
        fc = harness.plugin.fleet_carrier
        entry = {
            'event': "CarrierTradeOrder",
            'CarrierID': 12345,
            'Commodity': 'tritium',
            'Commodity_Localised': 'Tritium',
            'PurchaseOrder': 50,
            'Price': 900
        }

        free:int = fc._get_freespace()
        reserved:int = fc._get_reserved()
        fc.trade_order(entry)

        assert 'tritium' in fc.cargo['normal']
        assert fc.cargo['normal']['tritium']['outstanding'] == 50
        assert fc.cargo['normal']['tritium']['price'] == 900
        assert fc._get_freespace() == free - 50
        assert fc._get_reserved() == reserved + 50

    def test_trade_order_cancel(self, harness) -> None:
        """ Test trade_order() for cancel order """
        fc = harness.plugin.fleet_carrier
        entry = {
            'event': 'CarrierTradeOrder',            
            'CarrierID': 12345,
            'Commodity': 'tritium',
            'CancelTrade': True
        }
        fc.overview = {'carrier_id': 12345}
        fc.cargo = {
            'normal': {
                'tritium': {'stock': 100, 'price': 1000, 'outstanding': 50, 'buyTotal': 50}
            }
        }

        fc.trade_order(entry)

        assert fc.cargo['normal']['tritium']['outstanding'] == 0
        assert fc.cargo['normal']['tritium']['buyTotal'] == 0
        assert fc.cargo['normal']['tritium']['price'] == 0

    def test_cargo_transfer(self, harness) -> None:
        """ Test cargo_transfer() method """
        fc = harness.plugin.fleet_carrier
        fc.cargo = {
            'normal': {
                'steel': {'stock': 100, 'outstanding': 50, 'price': 1000}
            }
        }

        entry = {
            'event':'CargoTransfer',
            'Transfers': [
                {'Type': 'tritium', 'Count': 50, 'Direction': 'tocarrier'},
                {'Type': 'steel', 'Count': 25, 'Direction': 'fromcarrier'},
                {'Type': 'platinum', 'Count': 15, 'Direction': 'fromcarrier'}
            ]
        }
        free:int = fc._get_freespace()
        fc.cargo_transfer(entry)

        assert fc.cargo['normal']['tritium']['stock'] == 50
        assert fc.cargo['normal']['steel']['stock'] == 75
        assert fc._get_freespace() == free - 50 + 25
        

    def test_market_activity_buy(self, harness) -> None:
        """ Test market_activity() for sell event  """
        fc = harness.plugin.fleet_carrier
        entry = {
            'event':'MarketSell',
            'MarketID': 12345,
            'Type': 'tritium',
            'Type_Localised': 'Tritium',
            'Count': 10
        }
        fc.cargo = {
            'normal': {
                'tritium': {'stock': 100, 'outstanding': 50, 'price': 1000}
            }
        }
        free:int = fc._get_freespace()
        fc.market_activity(entry)

        assert fc.cargo['normal']['tritium']['outstanding'] == 40
        assert fc.cargo['normal']['tritium']['stock'] == 110
        assert fc._get_freespace() == free

    def test_market_activity_sell(self, harness) -> None:
        """ Test market_activity() for buy event """
        fc = harness.plugin.fleet_carrier
        fc.cargo = {
            'normal': {
                'tritium': {'stock': 100, 'outstanding': 0, 'price': 1000}
            }
        }
        entry = {
            'event': 'MarketBuy',
            'MarketID': 12345,
            'Type': 'tritium',
            'Type_Localised': 'Tritium',
            'Count': 20
        }        
        free:int = fc._get_freespace()        
        fc.market_activity(entry)

        assert fc.cargo['normal']['tritium']['stock'] == 80
        assert fc._get_freespace() == free + 20
    
class TestCarrierEvents:
    def test_capi_event(self, harness) -> None:
        """ Test handling a jump request """
        fc = harness.plugin.fleet_carrier
        capi_data:dict = harness.get_config_data('carrier_capi_data.json')

        # Pre-flight checks.         
        assert fc.overview.get('carrier_id') == 12345
        assert fc.overview.get('currentStarSystem', '') == 'Sol'
        assert len(fc.itinerary) == 0

        fc.update(capi_data)
        
        assert fc.overview.get('currentStarSystem') == 'Sol'
        
        fc.save()
        assert filecmp.cmp(harness.plugin_dir / "otherdata" / "fleetcarrier.json", 
                           harness.plugin_dir / "config" / "fleetcarrier_capi_result.json", 
                           shallow=False)

    def test_stats_received_wrong_carrier(self, harness) -> None:
        """ Test stats_received() method """
        fc = harness.plugin.fleet_carrier
        entry = {
            'CarrierID': 99999,
            'Name': 'Test Carrier',
            'Callsign': 'ABC-123',
            'DockingAccess': 'all',
            'AllowNotorious': True,
            'SpaceUsage': {
                'TotalCapacity': 25000,
                'Crew': 50,
                'ShipPacks': 10,
                'ModulePacks': 5,
                'FreeSpace': 24000,
                'CargoSpaceReserved': 100
            },
            'Finance': {
                'CarrierBalance': 1000000,
                'ReserveBalance': 200000
            }
        }

        fc.stats_received(entry)

        assert fc.carrier_id != 99999
        assert fc.overview['name'] != 'Test Carrier'
        assert fc.overview['callsign'] != 'ABC-123'


    def test_carrier_location(self, harness) -> None:
        """ Test carrier_location() method """
        fc = harness.plugin.fleet_carrier
        entry = {
            'CarrierID': 12345,
            'StarSystem': 'Alpha Centauri',
            'Body': 'Alpha Centauri A'
        }
        assert fc.overview['carrier_id'] == 12345
        fc.carrier_location(entry)

        assert fc.overview['currentStarSystem'] == 'Alpha Centauri'
        assert fc.overview['currentBody'] == 'Alpha Centauri' # location doesn't provide body

    def test_deposit_fuel(self, harness) -> None:
        """ Test deposit_fuel() method """
        fc = harness.plugin.fleet_carrier
        qty:int = 100
        assert fc.overview['fuel'] != qty
        
        entry = {'CarrierID': 12345, 'Total': qty}
        fc.deposit_fuel(entry)
        assert fc.overview['fuel'] == qty

    def test_shipyard_event(self, harness) -> None:
        """ Test shipyard_event() method """
        fc = harness.plugin.fleet_carrier
        entry = {
            'event': 'StoredShips',
            'ShipsHere': [
                {'ShipID': 1, 'Name': 'Eagle', 'ShipType': 'Eagle', 'ShipType_Localised': 'Eagle', 
                 'Value': 50000, 'TransferPrice': 1000, 'TransferTime': 300, 'Hot': False, 'ShipMarketID': 12345}
            ],
            'ShipsRemote': []
        }

        fc.shipyard_event(entry)

        assert '1' in fc.shipyard['ships']
        assert fc.shipyard['ships']['1']['name'] == 'Eagle'
        assert fc.shipyard['overview']['shipCount'] == 1
        assert fc.shipyard['overview']['totalValue'] == 50000


class CarrierUnused:
    def test_parse_date(self, harness) -> None:
        """ Test _parse_date() method """
        fc = harness.plugin.fleet_carrier
        # Test ISO format
        dt = fc._parse_date('2024-01-01T12:00:00Z')
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 1

        # Test JSON format
        dt = fc._parse_date('2024-01-01 12:00:00')
        assert dt.year == 2024

    def test_td(self, harness) -> None:
        """ Test _td() method """
        fc = harness.plugin.fleet_carrier
        dt1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        dt2 = datetime(2024, 1, 1, 11, 0, 0, tzinfo=UTC)

        delta = fc._td(dt1, dt2)
        assert delta == 3600

    def test_td_str(self, harness) -> None:
        """ Test _td_str() method """
        fc = harness.plugin.fleet_carrier
        time_str = fc._td_str(3661)  # 1 hour, 1 minute, 1 second
        assert time_str == "01:01:01"

    def test_time_passed(self, harness) -> None:
        """ Test _time_passed() method """
        fc = harness.plugin.fleet_carrier
        past_time = (datetime.now(UTC) - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        future_time = (datetime.now(UTC) + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

        assert fc._time_passed(past_time) == True
        assert fc._time_passed(future_time) == False

    def test_lt(self, harness) -> None:
        """ Test _lt() method """
        fc = harness.plugin.fleet_carrier
        utc_time = '2024-01-01T12:00:00Z'
        local_str = fc._lt(utc_time)
        assert isinstance(local_str, str)
        assert len(local_str) > 0

    def test_get_forsale(self, harness) -> None:
        """ Test _get_forsale() method """
        fc = harness.plugin.fleet_carrier
        fc.cargo = {
            'normal': {
                'tritium': {'stock': 100, 'price': 1000, 'outstanding': 0},
                'steel': {'stock': 50, 'price': 0, 'outstanding': 0}
            }
        }

        forsale = fc._get_forsale()
        assert forsale == 100

    def test_get_notforsale(self, harness) -> None:
        """ Test _get_notforsale() method """
        fc = harness.plugin.fleet_carrier
        fc.cargo = {
            'normal': {
                'tritium': {'stock': 100, 'price': 0, 'outstanding': 0},
                'steel': {'stock': 50, 'price': 1000, 'outstanding': 10}
            },
            'stolen': {
                'fruitandvegetables': {'stock': 25, 'price': 0, 'outstanding': 0}
            }
        }

        notforsale = fc._get_notforsale()
        assert notforsale == 175

    def test_get_reserved(self, harness) -> None:
        """ Test _get_reserved() method """
        fc = harness.plugin.fleet_carrier
        fc.cargo = {
            'normal': {
                'tritium': {'stock': 100, 'price': 1000, 'outstanding': 50},
                'steel': {'stock': 50, 'price': 0, 'outstanding': 0}
            }
        }

        reserved = fc._get_reserved()
        assert reserved == 50

    def test_get_usedspace(self, harness) -> None:
        """ Test _get_usedspace() method """
        fc = harness.plugin.fleet_carrier
        fc.overview = {
            'crew': 50,
            'shipPacks': 10,
            'modulePacks': 5,
            'totalCapacity': 25000
        }
        fc.cargo = {
            'normal': {
                'tritium': {'stock': 100, 'price': 1000, 'outstanding': 0}
            }
        }

        used = fc._get_usedspace()
        assert used == 165  # 50 + 10 + 5 + 100

    def test_get_freespace(self, harness) -> None:
        """ Test _get_freespace() method """
        fc = harness.plugin.fleet_carrier
        fc.overview = {'totalCapacity': 25000}

        free = fc._get_freespace()
        assert free == 25000  # No used space in this test

    def test_readable(self, harness) -> None:
        """ Test _readable() method """
        fc = harness.plugin.fleet_carrier
        readable = fc._readable('all')
        assert readable == 'All'

        readable = fc._readable('unknown')
        assert readable == 'unknown'

    def test_init_cargo_item(self, harness) -> None:
        """ Test _init_cargo_item() method """
        fc = harness.plugin.fleet_carrier
        item = fc._init_cargo_item('tritium')
        assert item['locName'] == 'Tritium'
        assert item['category'] == 'Chemicals'
        assert item['stock'] == 0
        assert item['price'] == 0

    def test_as_dict(self, harness) -> None:
        """ Test _as_dict() method """
        fc = harness.plugin.fleet_carrier
        fc.carrier_id = 12345
        fc.overview = {'name': 'Test'}

        data = fc._as_dict()
        assert data['carrier_id'] == 12345
        assert data['overview']['name'] == 'Test'

    def test_from_dict(self, harness) -> None:
        """ Test _from_dict() method """
        fc = harness.plugin.fleet_carrier
        data = {
            'carrier_id': 12345,
            'overview': {'name': 'Test'},
            'cargo': {'normal': {}},
            'locker': {'normal': {}},
            'itinerary': [],
            'route': [],
            'shipyard': {'overview': {}, 'ships': {}},
            'data': {}
        }

        fc._from_dict(data)
        assert fc.carrier_id == 12345
        assert fc.overview['name'] == 'Test'
