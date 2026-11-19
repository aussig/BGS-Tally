"""
Test suite for BGS-Tally plugin using pytest.

Run with: .venv/bin/python -m pytest tests/test_plugin.py -v --tb=short 2>&1 | tail -30
Run with: .venv_win\\Scripts\\python.exe -m pytest tests\\test_plugin.py -v --tb=short
"""

import pytest # type: ignore
from datetime import datetime, UTC
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# Config is already mocked by conftest.py
from config import config # type: ignore
import edmc_data # type: ignore
from bgstally.constants import UpdateUIPolicy, Vehicle, Location, ShipState, UIState
from bgstally.tick import URL_GALAXY_TICK_DETECTOR
from tests.edmc.requests import queue_response, MockResponse

def _queue_tick(tick_time:datetime) -> None:
    """ Have the mocked tick server report this galaxy tick next. """
    stamp:str = tick_time.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    queue_response('get', MockResponse(200, url=URL_GALAXY_TICK_DETECTOR, json_data={'lastGalaxyTick': stamp}), url=URL_GALAXY_TICK_DETECTOR)

def _clear_overlay(plugin) -> None:
    """ Enable the overlay and drop the messages startup put on the mocked one. """
    plugin.state.enable_overlay = True
    plugin.overlay.edmcoverlay.messages.clear()

def _overlay_texts(plugin) -> list[str]:
    """ Text of every message on the mocked overlay. """
    return [msg[1] for msg in plugin.overlay.edmcoverlay.messages.values()]

class TestBGSTally:
    """Test BGS-Tally plugin behavior."""

    def test_bgstally_initialization(self, harness) -> None:
        """Test bgstally initialization."""
        assert harness is not None
        assert harness.plugin is not None
        assert harness.plugin.plugin_name == 'BGS-Tally'

    def test_plugin_stop(self, harness) -> None:
        other:Path = Path(harness.plugin_dir) / "otherdata"
        for saved in other.glob("*.json"): saved.unlink()

        harness.plugin.plugin_stop()

        assert {"colonisation.json", "missionlog.json", "targetlog.json"} <= {f.name for f in other.glob("*.json")}

    def test_check_tick_trigger(self, harness) -> None:
        plugin = harness.plugin
        _clear_overlay(plugin)
        plugin.tick.tick_time = datetime(2000, 1, 1, tzinfo=UTC)
        _queue_tick(datetime.now(UTC))

        assert plugin.check_tick(UpdateUIPolicy.IMMEDIATE) is True
        assert plugin.activity_manager.get_current_activity().tick_id == plugin.tick.tick_id
        assert "NEW TICK DETECTED!" in _overlay_texts(plugin)

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
        """ Test check_tick() when the tick server reports nothing newer than our current tick. """
        plugin = harness.plugin
        _clear_overlay(plugin)
        tick_id:str = plugin.tick.tick_id
        _queue_tick(datetime(2000, 1, 1, tzinfo=UTC))

        assert plugin.check_tick(UpdateUIPolicy.LATER) is False
        assert plugin.tick.tick_id == tick_id
        assert "NEW TICK DETECTED!" not in _overlay_texts(plugin)

    def test_new_tick_updates_ui(self, harness) -> None:
        plugin = harness.plugin
        _clear_overlay(plugin)

        plugin.new_tick(True, UpdateUIPolicy.IMMEDIATE)

        assert plugin.tick.tick_id.startswith("frc-")
        assert plugin.ui.lbl_tick.cget('text').endswith(plugin.tick.get_formatted())
        assert "NEW TICK DETECTED!" in _overlay_texts(plugin)

    def test_new_tick_schedules_update(self, harness) -> None:
        plugin = harness.plugin
        _clear_overlay(plugin)
        pending:int = harness._tk_scheduler.pending_count()

        plugin.new_tick(False, UpdateUIPolicy.LATER)

        assert harness._tk_scheduler.pending_count() == pending + 1
        assert "NEW TICK DETECTED!" in _overlay_texts(plugin)

    def test_rejected_tick(self, harness) -> None:
        """ A tick older than the current activity's is ignored. """
        plugin = harness.plugin
        _clear_overlay(plugin)
        activity = plugin.activity_manager.get_current_activity()
        plugin.tick.tick_time = datetime(2000, 1, 1, tzinfo=UTC)

        plugin.new_tick(False, UpdateUIPolicy.IMMEDIATE)

        assert plugin.activity_manager.get_current_activity() is activity
        assert "NEW TICK DETECTED!" not in _overlay_texts(plugin)

    def test_tick_worker_exits_shutdown(self, harness) -> None:
        plugin = harness.plugin
        config.shutting_down = True

        try:
            plugin._tick_worker()
        finally:
            config.shutting_down = False

    def test_tick_worker_runs_one_iteration(self, harness) -> None:
        plugin = harness.plugin
        plugin.tick.tick_time = datetime(2000, 1, 1, tzinfo=UTC)
        _queue_tick(datetime.now(UTC))
        config.shutting_down = False

        def _sleep_once(_: int) -> None:
            config.shutting_down = True

        try:
            with patch("bgstally.bgstally.sleep", side_effect=_sleep_once):
                plugin._tick_worker()

            assert plugin.tick.tick_time.year > 2000
        finally:
            config.shutting_down = False
