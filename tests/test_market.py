"""
Test suite for market module of BGS-Tally.
"""
import pytest # type: ignore
from typing import Generator
from pathlib import Path
import shutil
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

    Path(Path(__file__).parent / "journal_folder" / "Market.json").unlink(missing_ok=True)
    market_init_file:str = getattr(request, 'param', 'market_init.json')
    if market_init_file != 'None':
        shutil.copy(Path(__file__).parent / "journal_config" / market_init_file,
                    Path(__file__).parent / "journal_folder" / "Market.json")

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

class TestMethods:
    """Test methods in bsgatally/market.py."""

    def test_not_available(self, harness) -> None:
        """Test not available."""
        assert harness is not None
        res:bool = harness.plugin.market.available(1111111111)

        assert res == False

    def test_available(self, harness) -> None:
        """Test available."""
        assert harness is not None

        res:bool = harness.plugin.market.available(4292118787)
        assert res == True

    def test_load(self, harness) -> None:
        """Test load."""
        assert harness is not None
        res:bool = harness.plugin.market.available(4292118787)
        assert res == True

        assert harness.plugin.market.name == "Nakamura's Syntheticals"
        assert harness.plugin.market.id == 4292118787
        assert len(harness.plugin.market.commodities) == 44

    def test_get_commodity(self, harness) -> None:
        """Test get_commodity."""
        assert harness is not None
        res:bool = harness.plugin.market.available(4292118787)
        assert res == True

        assert harness.plugin.market.get_commodity('cmmcomposite')['SellPrice'] == 5972
        assert harness.plugin.market.get_commodity('steel')['BuyPrice'] == 0
        assert harness.plugin.market.get_commodity('titanium')['StockBracket'] == 2
