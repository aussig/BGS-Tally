"""Unit tests for UI behavior in bgstally.ui."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest  # type: ignore

from bgstally.activity import STATES_WAR
from bgstally.constants import FavouriteActivity
from harness import TestHarness
from config import config  # type: ignore


@pytest.fixture
def harness(request) -> Generator:
    """Provide a fresh test harness for each test."""
    live = request.node.get_closest_marker("live_requests") is not None

    test_harness: TestHarness = TestHarness(live_requests=live)

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

    from load import plugin_app, plugin_start3
    import bgstally.globals

    test_harness.plugin = bgstally.globals.this

    plugin_start3(str(test_harness.plugin_dir))
    plugin_app(test_harness.parent)

    yield test_harness
    test_harness.assert_no_unhandled_exceptions()


class TestUI:
    """Focused tests for UI helper and callback behavior."""

    def test_init(self, harness) -> None:
        assert harness is not None
        assert harness.plugin.ui is not None

    def test_show_activity_window_ignores_none_activity(self, harness) -> None:
        ui = harness.plugin.ui
        before = dict(ui.window_activity)
        ui._show_activity_window(None)
        assert ui.window_activity == before

    def test_show_activity_window_reuses_existing_window(self, harness) -> None:
        ui = harness.plugin.ui
        existing = SimpleNamespace(show=MagicMock())
        activity = SimpleNamespace(tick_id="tick-1")
        ui.window_activity["tick-1"] = existing

        ui._show_activity_window(activity)

        existing.show.assert_called_once_with(activity)

    def test_show_activity_window_creates_window_for_new_tick(self, harness) -> None:
        ui = harness.plugin.ui
        activity = SimpleNamespace(tick_id="tick-new")

        with patch("bgstally.ui.WindowActivity") as mock_window_activity:
            mock_instance = MagicMock()
            mock_window_activity.return_value = mock_instance

            ui._show_activity_window(activity)

            mock_window_activity.assert_called_once_with(harness.plugin, ui, activity)
            assert ui.window_activity["tick-new"] is mock_instance

    def test_language_and_formatter_callbacks_update_state(self, harness) -> None:
        ui = harness.plugin.ui

        ui.languages = {None: "Default", "en": "English"}
        ui.language = SimpleNamespace(get=lambda: "English")
        ui._language_modified()
        assert harness.plugin.state.discord_lang == "en"

        ui.formatters = {None: "Default", "text": "Text"}
        ui.formatter = SimpleNamespace(get=lambda: "Text")
        ui._formatter_modified()
        assert harness.plugin.state.discord_formatter == "text"

    def test_overlay_options_state_reflects_overlay_availability(self, harness) -> None:
        ui = harness.plugin.ui

        ui.bgstally.overlay.edmcoverlay = None
        assert ui.overlay_options_state() == "disabled"

        ui.bgstally.overlay.edmcoverlay = object()
        assert ui.overlay_options_state() == "enabled"

    def test_build_station_info_contains_station_and_faction(self, harness) -> None:
        ui = harness.plugin.ui
        result = ui._build_station_info({"station": "Jameson Memorial", "faction": "Pilots Federation"})

        assert "Jameson Memorial" in result
        assert "Pilots Federation" in result

    def test_favourite_and_cooldown_callbacks_update_state(self, harness) -> None:
        ui = harness.plugin.ui

        ui.bgstally.state.refresh = MagicMock()
        ui._favourite_type_selected(
            {
                FavouriteActivity.IGNORE: "Include all factions",
                FavouriteActivity.FACTIONS: "Include favourite factions only",
            },
            "Include favourite factions only",
        )
        assert ui.bgstally.state.FavouriteActivityMode.get() == FavouriteActivity.FACTIONS

        ui._cooldown_selected({"popup": "Popup only"}, "Popup only")
        assert ui.bgstally.state.FcCooldown.get() == "popup"
        ui.bgstally.state.refresh.assert_called_once()

    def test_update_plugin_frame_shows_update_available_notice(self, harness) -> None:
        ui = harness.plugin.ui

        ui.btn_latest_tick = MagicMock()
        ui.btn_previous_ticks = MagicMock()
        ui.lbl_active = MagicMock()
        ui.lbl_tick = MagicMock()
        ui.lbl_version = MagicMock()
        ui.btn_carrier = MagicMock()
        ui.btn_objectives = MagicMock()
        ui.btn_colonisation = MagicMock()
        ui.window_progress = MagicMock()

        ui.bgstally.update_manager.update_available = True
        ui.bgstally.api_manager.api_updated = False

        ui.update_plugin_frame()

        ui.lbl_version.configure.assert_called_with(
            text="Update will be installed on shutdown",
            url="https://github.com/aussig/BGS-Tally/releases/latest",
            foreground="red",
        )
        ui.window_progress.update_display.assert_called_once()

    def test_update_plugin_frame_shows_api_changed_notice(self, harness) -> None:
        ui = harness.plugin.ui

        ui.btn_latest_tick = MagicMock()
        ui.btn_previous_ticks = MagicMock()
        ui.lbl_active = MagicMock()
        ui.lbl_tick = MagicMock()
        ui.lbl_version = MagicMock()
        ui.btn_carrier = None
        ui.btn_objectives = MagicMock()
        ui.btn_colonisation = MagicMock()
        ui.window_progress = MagicMock()

        ui.bgstally.update_manager.update_available = False
        ui.bgstally.api_manager.api_updated = True

        ui.update_plugin_frame()

        ui.lbl_version.configure.assert_called_with(
            text="API changed, open settings to re-approve",
            url="",
            foreground="red",
        )

    def test_build_system_info_handles_no_factions(self, harness) -> None:
        ui = harness.plugin.ui

        activity = SimpleNamespace(get_ordered_factions=lambda _: [])
        system = {
            "System": "Sol",
            "Factions": {},
            "Population": 1000,
            "Government": "Democracy",
            "Security": "High",
        }

        result = ui._build_system_info(activity, system)

        assert "Entered System: Sol" in result
        assert "No factions found in system" in result

    def test_build_system_info_includes_conflicts(self, harness) -> None:
        ui = harness.plugin.ui

        war_state = STATES_WAR[0]
        ordered_factions = [
            {
                "Faction": "Faction A",
                "Influence": 0.55,
                "FactionState": war_state,
                "Opponent": "Faction B",
                "Score": 3,
                "Stake": "Base Alpha",
            }
        ]
        activity = SimpleNamespace(get_ordered_factions=lambda _: ordered_factions)
        system = {
            "System": "Achenar",
            "Factions": {
                "Faction B": {
                    "Faction": "Faction B",
                    "Score": 2,
                    "Stake": "Port Beta",
                }
            },
            "Population": 42,
            "Government": "Dictatorship",
            "Security": "Low",
        }

        result = ui._build_system_info(activity, system)

        assert "Controlling Faction: Faction A" in result
        assert "Conflicts:" in result
        assert "Faction A vs Faction B" in result

    def test_worker_exits_when_shutting_down(self, harness) -> None:
        ui = harness.plugin.ui
        config.shutting_down = True

        try:
            # Call wrapped function to directly exercise worker loop behavior.
            ui._worker.__wrapped__(ui)
        finally:
            config.shutting_down = False

    def test_worker_tick_and_activity_indicator_single_iteration(self, harness) -> None:
        ui = harness.plugin.ui
        state = ui.bgstally.state

        state.enable_overlay_current_tick = True
        state.enable_overlay_activity = True
        state.enable_overlay_tw_progress = False
        state.enable_overlay_system = False
        state.enable_overlay_cmdr = False
        state.enable_overlay_warning = False
        state.enable_overlay_objectives = False
        state.enable_overlay_colonisation = False
        state.enable_overlay_carrier = False

        ui.indicate_activity = True

        ui.bgstally.overlay.display_message = MagicMock()
        ui.bgstally.overlay.display_indicator = MagicMock()
        ui.bgstally.activity_manager.get_current_activity = MagicMock(return_value=None)
        ui.bgstally.tick.get_formatted = MagicMock(return_value="2026-07-11 00:00")
        ui.bgstally.tick.next_predicted = MagicMock(return_value=datetime.now(UTC) + timedelta(days=1))

        config.shutting_down = False

        def _sleep_once(_: float) -> None:
            config.shutting_down = True

        try:
            with patch("bgstally.ui.sleep", side_effect=_sleep_once):
                ui._worker.__wrapped__(ui)

            ui.bgstally.overlay.display_message.assert_any_call("tick", "Galaxy Tick: 2026-07-11 00:00", True)
            ui.bgstally.overlay.display_indicator.assert_called_once_with("indicator")
            assert ui.indicate_activity is False
        finally:
            config.shutting_down = False
