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

class TestCarrierCAPI:
    """ Test fleet carrier handling of CAPI data """

    def test_capi_event(self, harness) -> None:
        """ Test handling a jump request """
        fc = harness.plugin.fleet_carrier
        capi_data:dict = harness.get_config_data('carrier_capi_data.json')

        # Pre-flight checks.         
        assert fc.overview.get('carrier_id') == 3709409280
        assert fc.overview.get('currentStarSystem', '') == 'Sol'
        assert len(fc.itinerary) == 0

        fc.update(capi_data)
        
        assert fc.overview.get('currentStarSystem') == 'Sol'
        
        fc.save()
        assert filecmp.cmp(harness.plugin_dir / "otherdata" / "fleetcarrier.json", 
                           harness.plugin_dir / "config" / "fleetcarrier_capi_result.json", 
                           shallow=False)

class TestCarrierJumps:
    """ Test fleet carrier functions """

    def test_jump_request(self, harness) -> None:
        """ Test handling a jump request """
        fc = harness.plugin.fleet_carrier
        # Read the carrier events from the journal_events.json
        events:list = harness.events.get('carrier_events', [])

        # Pre-flight checks.         
        assert fc.overview.get('carrier_id') == 3709409280
        assert fc.overview.get('currentStarSystem', '') == 'Sol'
        
        # Send event 0
        harness.fire_event(events[0])
        
        # Confirm that the carrier's jump destination is now what the carrier event indicated.
        assert fc.overview.get('jumpDestination') == 'Bleae Thua ZE-I b23-1'

        # Wait for the worker thread and see if the overlay message is set.
        sleep(2)
        assert harness.plugin.overlay.edmcoverlay.messages != {}

    def test_jump_completed(self, harness) -> None:
        """ Test a successful jump """      
        fc = harness.plugin.fleet_carrier  
        events:list = harness.events.get('carrier_events', [])        
        assert fc.overview.get('carrier_id') == 3709409280
        assert fc.overview.get('currentStarSystem', '') == 'Sol'
        harness.fire_event(events[0])
        assert fc.overview.get('jumpDestination') == 'Bleae Thua ZE-I b23-1'
        harness.fire_event(events[1])
        assert fc.overview.get('currentStarSystem', '') == 'Bleae Thua ZE-I b23-1'

        # Wait for the worker thread and see if the overlay message is set.
        sleep(2)
        assert harness.plugin.overlay.edmcoverlay.messages != {}

    def test_jump_cancellation(self, harness) -> None:
        """ A cancelled jump """
        fc = harness.plugin.fleet_carrier
        events:list = harness.events.get('carrier_events', [])
        
        assert fc.overview.get('carrier_id') == 3709409280
        assert fc.overview.get('currentStarSystem', '') == 'Sol'
        harness.fire_event(events[0])
        assert fc.overview.get('jumpDestination') == 'Bleae Thua ZE-I b23-1'
        harness.fire_event(events[2])
        assert fc.overview.get('currentStarSystem', '') == 'Sol'        
        assert fc.overview.get('jumpDestination') == None
        assert fc.timer == datetime.now(tz=UTC) + timedelta(seconds=60)

        # Wait for the worker thread and see if the overlay message is set.
        sleep(2)
        assert harness.plugin.overlay.edmcoverlay.messages != {}
