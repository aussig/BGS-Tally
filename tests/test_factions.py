"""
Test suite for faction manager module of BGS-Tally.
"""
import pytest # type: ignore
import shutil
from pathlib import Path
from typing import Generator
from time import sleep
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, patch, MagicMock
import filecmp

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

    # Make sure we always start with a consistent factions.json
    Path(Path(__file__).parent / "otherdata" / "factions.json").unlink(missing_ok=True)
    factions_init_file:str = getattr(request, 'param', 'factions_init.json')
    if factions_init_file != 'None':
        shutil.copy(Path(__file__).parent / "config" / factions_init_file,
                    Path(__file__).parent / "otherdata" / "factions.json")
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

class TestFactions:
    """Test faction management functionality."""

    @pytest.mark.parametrize('harness', ['None', 'factions_init.json'], indirect=True)
    def test_initialization(self, harness) -> None:
        fm = harness.plugin.faction_manager
        assert fm.factions == []

    def test_add_favourite(self, harness) -> None:
        fm = harness.plugin.faction_manager

        assert fm.is_favourite("Faction A") is False
        fm.set_favourite("Faction A", True)
        assert fm.is_favourite("Faction A") is True

    def test_remove_favourite(self, harness) -> None:
        fm = harness.plugin.faction_manager

        fm.set_favourite("Faction A", True)
        assert fm.is_favourite("Faction A") is True
        fm.set_favourite("Faction A", False)
        assert fm.is_favourite("Faction A") is False

    def test_dupe_favourite(self, harness) -> None:
        fm = harness.plugin.faction_manager

        fm.set_favourite("Faction A", True)
        fm.set_favourite("Faction A", True)
        assert fm.is_favourite("Faction A") is True

    def test_remove_not_present(self, harness) -> None:
        fm = harness.plugin.faction_manager

        fm.set_favourite("Faction A", False)
        assert fm.is_favourite("Faction A") is False

    def test_save(self, harness) -> None:
        fm = harness.plugin.faction_manager

        fm.set_favourite("Faction A", True)
        fm.set_favourite("Faction B", True)
        fm.save()
        saved_file = Path(harness.plugin.plugin_dir) / "otherdata" / "factions.json"
        assert saved_file.exists()
        with open(saved_file) as f:
            assert f.read() == "[\"Faction A\", \"Faction B\"]"

        # Create a new instance to load the data
        fm2 = harness.plugin.faction_manager.__class__(harness.plugin)
        assert fm2.is_favourite("Faction A") is True
        assert fm2.is_favourite("Faction B") is True

    def test_load(self, harness) -> None:
        fm = harness.plugin.faction_manager

        fm.set_favourite("Faction A", True)
        fm.set_favourite("Faction B", True)
        fm.save()

        # Create a new instance to load the data
        fm2 = harness.plugin.faction_manager.__class__(harness.plugin)
        fm2.load()
        assert fm2.is_favourite("Faction A") is True
        assert fm2.is_favourite("Faction B") is True