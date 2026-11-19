"""
Test suite for BGS-Tally plugin using pytest.

Run with: .venv/bin/python -m pytest tests/test_plugin.py -v --tb=short 2>&1 | tail -30
Run with: .venv_win\\Scripts\\python.exe -m pytest tests\\test_plugin.py -v --tb=short
"""

import pytest # type: ignore
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Config is already mocked by conftest.py
from config import config # type: ignore
import edmc_data # type: ignore
from bgstally.constants import UpdateUIPolicy, Vehicle, Location, ShipState, UIState

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
        """ Test check_tick() when no new tick is available. This may fail if the server is running slowly or is down. """
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

    def test_tick_worker_exits_shutdown(self, harness) -> None:
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
