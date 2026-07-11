"""
Test suite for BGS-Tally plugin using pytest.

Run with: .venv/bin/python -m pytest tests/test_plugin.py -v --tb=short 2>&1 | tail -30
Run with: .venv_win\\Scripts\\python.exe -m pytest tests\\test_plugin.py -v --tb=short
"""

import pytest # type: ignore
from typing import Generator
from types import SimpleNamespace
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

# Config is already mocked by conftest.py
from config import config # type: ignore
import edmc_data # type: ignore
from bgstally.constants import UpdateUIPolicy, Vehicle, Location, ShipState, UIState
from harness import TestHarness

@pytest.fixture
def harness(request) -> Generator:
    """ Provide a fresh test harness for each test. """
    live = request.node.get_closest_marker('live_requests') is not None

    test_harness = TestHarness(live_requests=live)

    import bgstally.constants
    bgstally.constants.FOLDER_ASSETS = "../assets"
    bgstally.constants.FOLDER_DATA = "../data"

    # Put in a response for the update manager so it doesn't error
    if not live:
        from tests.edmc.requests import queue_response, MockResponse
        queue_response('get',
                       MockResponse(200, url='http://tick.infomancer.uk/galtick.json',
                                    json_data={"lastGalaxyTick": datetime.now(UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')}),
                        url='http://tick.infomancer.uk/galtick.json', sticky=True)

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

class TestBGSTally:
    """Test BGS-Tally plugin behavior."""

    def test_bgstally_initialization(self, harness) -> None:
        """Test bgstally initialization."""
        assert harness is not None
        assert harness.plugin is not None
        assert harness.plugin.plugin_name == 'BGS-Tally'

    def test_plugin_stop(self, harness) -> None:
        plugin = harness.plugin
        plugin.ui.shut_down = MagicMock()
        plugin.colonisation.save = MagicMock()
        plugin.save_data = MagicMock()

        plugin.plugin_stop()

        plugin.ui.shut_down.assert_called_once()
        plugin.colonisation.save.assert_called_once_with('Shutdown')
        plugin.save_data.assert_called_once()


    def test_check_tick_trigger(self, harness) -> None:
        plugin = harness.plugin
        plugin.tick.fetch_tick = MagicMock(return_value=True)
        with patch.object(plugin, "new_tick") as mock_new_tick:
            result = plugin.check_tick(UpdateUIPolicy.IMMEDIATE)

        assert result is True
        mock_new_tick.assert_called_once_with(False, UpdateUIPolicy.IMMEDIATE)

    def test_dashboard_entry(self, harness) -> None:
        plugin = harness.plugin

        entry = {
            "Flags": (
                edmc_data.FlagsInMainShip
                | edmc_data.FlagsDocked
                | edmc_data.FlagsHardpointsDeployed
            ),
            "Flags2": 0,
            "GuiFocus": edmc_data.GuiFocusStationServices,
        }

        plugin.dashboard_entry("Testy", False, entry)

        assert plugin.state.vehicle == Vehicle.SHIP
        assert plugin.state.location == Location.SPACE
        assert ShipState.DOCKED in plugin.state.ship_state
        assert ShipState.HARDPOINTS_DEPLOYED in plugin.state.ship_state
        assert plugin.state.ui_state == UIState.STATION_SERVICES

    def test_check_no_tick(self, harness) -> None:
        plugin = harness.plugin
        plugin.tick.fetch_tick = MagicMock(return_value=False)
        with patch.object(plugin, "new_tick") as mock_new_tick:
            result = plugin.check_tick(UpdateUIPolicy.LATER)

        assert result is False
        mock_new_tick.assert_not_called()

    def test_new_tick_updates_ui(self, harness) -> None:
        plugin = harness.plugin
        plugin.tick.force_tick = MagicMock()
        plugin.activity_manager.new_tick = MagicMock(return_value=True)
        plugin.ui.update_plugin_frame = MagicMock()
        plugin.overlay.display_message = MagicMock()

        plugin.new_tick(True, UpdateUIPolicy.IMMEDIATE)

        plugin.tick.force_tick.assert_called_once()
        plugin.ui.update_plugin_frame.assert_called_once()
        plugin.overlay.display_message.assert_called_once_with("tickwarn", "NEW TICK DETECTED!", True, 180, "green")

    def test_new_tick_schedules_update(self, harness) -> None:
        plugin = harness.plugin
        plugin.activity_manager.new_tick = MagicMock(return_value=True)
        plugin.ui.frame = MagicMock()
        plugin.overlay.display_message = MagicMock()

        plugin.new_tick(False, UpdateUIPolicy.LATER)

        plugin.ui.frame.after.assert_called_once()
        plugin.overlay.display_message.assert_called_once()

    def test_rejected_tick(self, harness) -> None:
        plugin = harness.plugin
        plugin.activity_manager.new_tick = MagicMock(return_value=False)
        plugin.ui.update_plugin_frame = MagicMock()
        plugin.overlay.display_message = MagicMock()

        plugin.new_tick(False, UpdateUIPolicy.IMMEDIATE)

        plugin.ui.update_plugin_frame.assert_not_called()
        plugin.overlay.display_message.assert_not_called()

    def test_tick_worker_exits_when_shutting_down(self, harness) -> None:
        plugin = harness.plugin
        config.shutting_down = True

        try:
            plugin._tick_worker()
        finally:
            config.shutting_down = False

    def test_tick_worker_runs_one_iteration(self, harness) -> None:
        plugin = harness.plugin
        plugin.check_tick = MagicMock()
        config.shutting_down = False

        def _sleep_once(_: int) -> None:
            config.shutting_down = True

        try:
            with patch("bgstally.bgstally.sleep", side_effect=_sleep_once):
                plugin._tick_worker()

            plugin.check_tick.assert_called_once_with(UpdateUIPolicy.LATER)
        finally:
            config.shutting_down = False
