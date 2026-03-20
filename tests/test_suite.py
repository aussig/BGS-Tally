"""
Test suite for EDMC Neutron Dancer plugin using pytest.

Run with: .venv/bin/python -m pytest tests/test_plugin.py -v --tb=short 2>&1 | tail -30
Run with: .venv_win\\Scripts\\python.exe -m pytest tests\\test_plugin.py -v --tb=short
"""

import pytest # type: ignore
import sys
import os
from pathlib import Path
from typing import Generator, Optional
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

    # Now we can import Router modules
    from load import plugin_start3, plugin_app
    import bgstally.globals
    test_harness.bgstally = bgstally.globals.this
    
    plugin_start3(str(test_harness.plugin_dir))
    plugin_app(test_harness.parent)

    test_harness.register_journal_handler(test_harness.bgstally.journal_entry)
    test_harness.commander = 'Testy'
    test_harness.is_beta = False
    test_harness.system = 'Sol'
        
    yield test_harness

class TestStartup:
    """Test plugin startup behavior."""

    def test_harness_initialization(self, harness) -> None:
        """Test basic harness initialization."""
        assert harness is not None

class TestFleetCarrier:
    """ Test fleet carrier functions """

    def test_jump_sequence(self, harness) -> None:
        # @note: Need a carrierstats event to initialize the carrier data.
        events:list = harness.events.get('carrier_events', [])
        harness.bgstally.fleet_carrier.overview['carrier_id'] = 3709409280
        assert harness.bgstally.fleet_carrier.overview.get('carrier_id') == 3709409280
        assert harness.config.get_str('BGST_Status', default='On') == 'On'
        harness.fire_event(events[0])
        assert harness.bgstally.fleet_carrier.overview.get('jumpDestination') == 'Bleae Thua ZE-I b23-1'
        #assert harness.bgstally.fleet_carrier.jump_state == 'Jumping'
        harness.fire_event(events[1])
        