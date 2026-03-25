"""
Test suite for BGS-Tally plugin using pytest.

Run with: .venv/bin/python -m pytest tests/test_plugin.py -v --tb=short 2>&1 | tail -30
Run with: .venv_win\\Scripts\\python.exe -m pytest tests\\test_plugin.py -v --tb=short
"""

import pytest # type: ignore
from typing import Generator
from time import sleep
from unittest.mock import patch

# Config is already mocked by conftest.py
from harness import TestHarness

@pytest.fixture
def harness() -> Generator:
    """ Provide a fresh test harness for each test. """  
    test_harness = TestHarness() 
    test_harness.set_edmc_config()

    import bgstally.constants
    bgstally.constants.FOLDER_ASSETS = "../assets"
    bgstally.constants.FOLDER_DATA = "../data"
    
    # Now we can import Router modules
    from load import plugin_start3, plugin_app, journal_entry
    import bgstally.globals
    test_harness.plugin = bgstally.globals.this  

    plugin_start3(str(test_harness.plugin_dir))
    plugin_app(test_harness.parent)

    test_harness.load_events("journal_events.json")
    test_harness.register_journal_handler(journal_entry, 'Testy', 'Sol', False)
        
    yield test_harness

class TestStartup:
    """Test plugin startup behavior."""

    def test_harness_initialization(self, harness) -> None:
        """Test basic harness initialization."""
        assert harness is not None
        assert harness.config.get_str('BGST_Status', default='On') == 'Yes'
