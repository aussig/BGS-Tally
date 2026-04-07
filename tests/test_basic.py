"""
Test suite for BGS-Tally plugin using pytest.

Run with: .venv/bin/python -m pytest tests/test_plugin.py -v --tb=short 2>&1 | tail -30
Run with: .venv_win\\Scripts\\python.exe -m pytest tests\\test_plugin.py -v --tb=short
"""

import pytest # type: ignore
from typing import Generator
from time import sleep
from datetime import datetime, UTC
from unittest.mock import patch

# Config is already mocked by conftest.py
from harness import TestHarness

@pytest.fixture
def harness(request) -> Generator:
    """ Provide a fresh test harness for each test. """
    live = request.node.get_closest_marker('live_requests') is not None

    test_harness = TestHarness(live_requests=live)

    import bgstally.constants
    bgstally.constants.FOLDER_ASSETS = "../assets"
    bgstally.constants.FOLDER_DATA = "../data"

    if not live:
        from tests.edmc.requests import queue_response, MockResponse
        queue_response('get', MockResponse(200,
                                           url='https://api.github.com/repos/aussig/BGS-Tally/releases/latest',
                                           json_data={'tag_name': 'v1.0.0','draft': True,'prerelease': True,
                                                       'assets': [{'browser_download_url': 'https://example.com/download'}]}),
                                            url='https://api.github.com/repos/aussig/BGS-Tally/releases/latest')
        queue_response('get', MockResponse(200,
                                           url='http://tick.infomancer.uk/galtick.json',
                                           json_data={"lastGalaxyTick": datetime.now(UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')}),
                                           url='http://tick.infomancer.uk/galtick.json',
                                           sticky=True)

    # Now we can start the plugin
    from load import plugin_start3, plugin_app, journal_entry
    import bgstally.globals
    test_harness.plugin = bgstally.globals.this

    plugin_start3(str(test_harness.plugin_dir))
    plugin_app(test_harness.parent)

    test_harness.load_events("journal_events.json")
    test_harness.register_journal_handler(journal_entry, 'Testy', 'Sol', False)

    yield test_harness
    test_harness.assert_no_unhandled_exceptions()

class TestStartup:
    """Test plugin startup behavior."""
    @pytest.mark.live_requests
    def test_harness_initialization(self, harness) -> None:
        """Test basic harness initialization."""
        assert harness is not None
        assert harness.config.get_str('BGST_Status', default='On') == 'Yes'
