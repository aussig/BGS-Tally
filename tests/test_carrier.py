"""
Test suite for EDMC Neutron Dancer plugin using pytest.

Run with: .venv/bin/python -m pytest tests/test_plugin.py -v --tb=short 2>&1 | tail -30
Run with: .venv_win\\Scripts\\python.exe -m pytest tests\\test_plugin.py -v --tb=short
"""

import pytest # type: ignore
import shutil
from pathlib import Path
from typing import Generator
from time import sleep
from unittest.mock import Mock, patch, MagicMock
import logging

# Config is already mocked by conftest.py
from harness import TestHarness

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@pytest.fixture
def harness() -> Generator:
    """ Provide a fresh test harness for each test. """  
    test_harness = TestHarness() 
    test_harness.set_edmc_config()

    # Use the "normal" locations for assets and data
    import bgstally.constants
    bgstally.constants.FOLDER_ASSETS = "../assets"
    bgstally.constants.FOLDER_DATA = "../data"

    # Make sure we always start with our clean fleetcarrier.json
    shutil.copy(Path(__file__).parent / "otherdata" / "fleetcarrier.test.json", Path(__file__).parent / "otherdata" / "fleetcarrier.json")

    # Now we can import Router modules
    from load import plugin_start3, plugin_app
    import bgstally.globals
    test_harness.bgstally = bgstally.globals.this
    
    plugin_start3(str(test_harness.plugin_dir))
    plugin_app(test_harness.parent)

    # Point code at a tmp dir so that saves won't overwrite our test data    
    test_harness.register_journal_handler(test_harness.bgstally.journal_entry)
    test_harness.commander = 'Testy'
    test_harness.is_beta = False
    test_harness.system = 'Sol'
        
    yield test_harness

class TestFleetCarrier:
    """ Test fleet carrier functions """

    def test_jump_request(self, harness) -> None:
        """ Test handling a jump request """
        # Read the carrier events from the journal_events.json
        events:list = harness.events.get('carrier_events', [])
        # Pre-flight checks.         
        assert harness.bgstally.fleet_carrier.overview.get('carrier_id') == 3709409280
        assert harness.bgstally.fleet_carrier.overview.get('currentStarSystem', '') == 'Sol'
        # Send event 0
        harness.fire_event(events[0])
        # Confirm that the carrier's jump destination is now what the carrier event indicated.
        assert harness.bgstally.fleet_carrier.overview.get('jumpDestination') == 'Bleae Thua ZE-I b23-1'

    def test_jump_completed(self, harness) -> None:
        """ Test a successful jump """        
        events:list = harness.events.get('carrier_events', [])        
        assert harness.bgstally.fleet_carrier.overview.get('carrier_id') == 3709409280
        assert harness.bgstally.fleet_carrier.overview.get('currentStarSystem', '') == 'Sol'
        harness.fire_event(events[0])
        assert harness.bgstally.fleet_carrier.overview.get('jumpDestination') == 'Bleae Thua ZE-I b23-1'
        harness.fire_event(events[1])
        assert harness.bgstally.fleet_carrier.overview.get('currentStarSystem', '') == 'Bleae Thua ZE-I b23-1'

    def test_jump_cancellation(self, harness) -> None:
        """ A cancelled jump """
        events:list = harness.events.get('carrier_events', [])
        
        assert harness.bgstally.fleet_carrier.overview.get('carrier_id') == 3709409280
        assert harness.bgstally.fleet_carrier.overview.get('currentStarSystem', '') == 'Sol'
        harness.fire_event(events[0])
        assert harness.bgstally.fleet_carrier.overview.get('jumpDestination') == 'Bleae Thua ZE-I b23-1'
        harness.fire_event(events[2])
        assert harness.bgstally.fleet_carrier.overview.get('jumpDestination') == None
