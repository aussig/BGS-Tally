"""
Simple unit tests for state.py.
"""
import pytest # type: ignore
from typing import Generator
from pathlib import Path
import shutil
from time import sleep
from datetime import datetime, UTC
from unittest.mock import patch

from harness import TestHarness
from bgstally.constants import CheckStates, DiscordActivity, FavouriteActivity
from bgstally.state import State

from config import config #type:ignore

@pytest.fixture
def harness(request) -> Generator:
    """ Provide a fresh test harness for each test. """
    live = request.node.get_closest_marker('live_requests') is not None

    test_harness:TestHarness = TestHarness(live_requests=live)
    test_harness.set_edmc_config('config_basic.toml')

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


class TestState:
    """Tests for state management."""
    def test_state_load_defaults(self, harness) -> None:
        assert harness is not None
        state = harness.plugin.state

        assert state.Status.get() == CheckStates.STATE_ON
        assert state.DiscordActivity.get() == DiscordActivity.BOTH
        assert state.ColonisationMaxCommodities.get() == "20"
        assert state.EnableOverlay.get() == CheckStates.STATE_ON
        assert state.enable_overlay is True
        assert state.enable_overlay_colonisation is True


    def test_state_refresh_updates_computed_flags(self, harness) -> None:
        assert harness is not None
        state:State = harness.plugin.state

        state.EnableOverlay.set(CheckStates.STATE_OFF)
        state.EnableOverlayCurrentTick.set(CheckStates.STATE_OFF)
        state.EnableOverlayActivity.set(CheckStates.STATE_ON)
        state.EnableOverlayColonisation.set(CheckStates.STATE_ON)
        state.ColonisationStatus.set(CheckStates.STATE_OFF)
        state.AbbreviateFactionNames.set(CheckStates.STATE_ON)
        state.IncludeSecondaryInf.set(CheckStates.STATE_OFF)
        state.OverlayObjectivesMode.set("3")
        state.FavouriteActivityMode.set(FavouriteActivity.SYSTEMS)

        state.refresh()

        assert state.enable_overlay is False
        assert state.enable_overlay_current_tick is False
        assert state.enable_overlay_activity is True
        assert state.enable_overlay_colonisation is False
        assert state.abbreviate_faction_names is True
        assert state.secondary_inf is False
        assert state.overlay_objectives_mode == 3
        assert state.favourite_activity_mode == FavouriteActivity.SYSTEMS


    def test_state_save_persists_values(self, harness) -> None:
        assert harness is not None
        state:State = harness.plugin.state

        state.Status.set(CheckStates.STATE_OFF)
        state.ColonisationStatus.set(CheckStates.STATE_OFF)
        state.ShowZeroActivitySystems.set(CheckStates.STATE_OFF)
        state.AbbreviateFactionNames.set(CheckStates.STATE_ON)
        state.IncludeSecondaryInf.set(CheckStates.STATE_ON)
        state.DiscordUsername.set("TestCmdr")
        state.EnableOverlay.set(CheckStates.STATE_ON)
        state.EnableOverlayCurrentTick.set(CheckStates.STATE_OFF)
        state.EnableOverlayActivity.set(CheckStates.STATE_OFF)
        state.EnableOverlayTWProgress.set(CheckStates.STATE_ON)
        state.EnableOverlaySystem.set(CheckStates.STATE_OFF)
        state.EnableOverlayWarning.set(CheckStates.STATE_ON)
        state.EnableOverlayCMDR.set(CheckStates.STATE_OFF)
        state.EnableOverlayObjectives.set(CheckStates.STATE_ON)
        state.OverlayObjectivesMode.set("1")
        state.EnableOverlayColonisation.set(CheckStates.STATE_ON)
        state.EnableSystemActivityByDefault.set(CheckStates.STATE_OFF)
        state.EnableShowMerits.set(CheckStates.STATE_ON)
        state.DetailedInf.set(CheckStates.STATE_OFF)
        state.DetailedTrade.set(CheckStates.STATE_ON)
        state.DiscordActivity.set(DiscordActivity.BGS)
        state.DiscordAvatarURL.set("https://example.com/avatar.png")
        state.DiscordBGSTWAutomatic.set(CheckStates.STATE_ON)
        state.FcCargo.set("Selling")
        state.FcLocker.set("Buying")
        state.ColonisationMaxCommodities.set("35")
        state.EnableProgressScrollbar.set(CheckStates.STATE_ON)
        state.ColonisationRCAPIKey.set("secret-key")
        state.FavouriteActivityMode.set(FavouriteActivity.FACTIONS)
        state.UseColonisationName.set(CheckStates.STATE_ON)

        state.current_system_id = ''
        state.station_faction = "TestFaction"
        state.station_type = "TestStation"
        state.discord_lang = None
        state.discord_formatter = "TestFormatter"

        state.save()

        assert config.get_str('BGST_Status', default='') == CheckStates.STATE_OFF
        assert config.get_str('BGST_ColonisationStatus', default='') == CheckStates.STATE_OFF
        assert config.get_str('BGST_ShowZeroActivity', default='') == CheckStates.STATE_OFF
        assert config.get_str('BGST_AbbreviateFactions', default='') == CheckStates.STATE_ON
        assert config.get_str('BGST_SecondaryInf', default='') == CheckStates.STATE_ON
        assert config.get_str('BGST_DiscordUsername', default='') == "TestCmdr"
        assert config.get_str('BGST_EnableOverlayCurrentTick', default='') == CheckStates.STATE_OFF
        assert config.get_str('BGST_DiscordActivity', default='') == DiscordActivity.BGS
        assert config.get_str('BGST_DiscordAvatarURL', default='') == "https://example.com/avatar.png"
        assert config.get_str('BGST_FcCargo', default='') == "Selling"
        assert config.get_str('BGST_FcLocker', default='') == "Buying"
        assert config.get_str('BGST_ColonisationMaxCommodities', default='') == "35"
        assert config.get_str('BGST_CurrentSystemID', default='') == ""
        assert config.get_str('BGST_StationFaction', default='') == "TestFaction"
        assert config.get_str('BGST_StationType', default='') == "TestStation"
        assert config.get_str('BGST_DiscordLang', default='') == ""
        assert config.get_str('BGST_DiscordFormatter', default='') == "TestFormatter"


    def test_state_load_migrates_legacy_config_keys(self, harness) -> None:
        assert harness is not None
        state:State = harness.plugin.state

        config.data['XShowZeroActivity'] = CheckStates.STATE_OFF.value
        config.data['XAbbreviate'] = CheckStates.STATE_ON.value
        config.data['XSecondaryInf'] = CheckStates.STATE_OFF.value
        config.data['XDiscordUsername'] = "LegacyCmdr"
        config.data['XEnableOverlay'] = CheckStates.STATE_OFF.value
        config.data['XCurrentSystemID'] = "LegacySystem"
        config.data['XStationFaction'] = "LegacyFaction"
        config.data['XStationType'] = "LegacyStation"

        state = State(None)

        assert state.ShowZeroActivitySystems.get() == CheckStates.STATE_OFF
        assert state.AbbreviateFactionNames.get() == CheckStates.STATE_ON
        assert state.IncludeSecondaryInf.get() == CheckStates.STATE_OFF
        assert state.DiscordUsername.get() == "LegacyCmdr"
        assert state.EnableOverlay.get() == CheckStates.STATE_OFF
        assert state.current_system_id == "LegacySystem"
        assert state.station_faction == "LegacyFaction"
        assert state.station_type == "LegacyStation"

        assert 'XShowZeroActivity' not in config.data
        assert 'XAbbreviate' not in config.data
        assert 'XSecondaryInf' not in config.data
        assert 'XDiscordUsername' not in config.data
        assert 'XEnableOverlay' not in config.data
        assert 'XCurrentSystemID' not in config.data
        assert 'XStationFaction' not in config.data
        assert 'XStationType' not in config.data
