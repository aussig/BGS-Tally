"""Unit tests for UI behavior in bgstally.ui."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest  # type: ignore

from bgstally.activity import STATES_WAR
from bgstally.constants import FavouriteActivity
from config import config  # type: ignore


class TestUI:
    """Focused tests for UI helper and callback behavior."""

    def test_init(self, harness) -> None:
        assert harness is not None
        assert harness.plugin.ui is not None

    def test_show_activity_ignores_none(self, harness) -> None:
        ui = harness.plugin.ui
        before = dict(ui.window_activity)
        ui._show_activity_window(None)
        assert ui.window_activity == before

    def test_show_activity_reuses_window(self, harness) -> None:
        ui = harness.plugin.ui
        activity = harness.plugin.activity_manager.get_current_activity()
        ui._show_activity_window(activity)
        window = ui.window_activity[activity.tick_id]

        ui._show_activity_window(activity)

        assert ui.window_activity == {activity.tick_id: window}

    def test_show_activity_creates_window(self, harness) -> None:
        from bgstally.windows.activity import WindowActivity
        ui = harness.plugin.ui
        activity = harness.plugin.activity_manager.get_current_activity()

        ui._show_activity_window(activity)

        assert isinstance(ui.window_activity[activity.tick_id], WindowActivity)
        assert ui.window_activity[activity.tick_id].toplevel.winfo_exists()

    # def test_language_formatter_update_state(self, harness) -> None:
    #     ui = harness.plugin.ui

    #     ui.languages = {None: "Default", "en": "English"}
    #     ui.language = SimpleNamespace(get=lambda: "English")
    #     ui._language_modified()
    #     assert harness.plugin.state.discord_lang == "en"

    #     ui.formatters = {None: "Default", "text": "Text"}
    #     ui.formatter = SimpleNamespace(get=lambda: "Text")
    #     ui._formatter_modified()
    #     assert harness.plugin.state.discord_formatter == "text"

    def test_overlay_options_reflect_availability(self, harness) -> None:
        ui = harness.plugin.ui

        ui.bgstally.overlay.edmcoverlay = None
        assert ui.overlay_options_state() == "disabled"

        ui.bgstally.overlay.edmcoverlay = object()
        assert ui.overlay_options_state() == "enabled"

    def test_station_info_has_faction(self, harness) -> None:
        ui = harness.plugin.ui
        result = ui._build_station_info({"station": "Jameson Memorial", "faction": "Pilots Federation"})

        assert "Jameson Memorial" in result
        assert "Pilots Federation" in result

    # def test_favourite_cooldown_update_state(self, harness) -> None:
    #     ui = harness.plugin.ui

    #     ui.bgstally.state.refresh = MagicMock()
    #     ui._favourite_type_selected(
    #         {
    #             FavouriteActivity.IGNORE: "Include all factions",
    #             FavouriteActivity.FACTIONS: "Include favourite factions only",
    #         },
    #         "Include favourite factions only",
    #     )
    #     assert ui.bgstally.state.FavouriteActivityMode.get() == FavouriteActivity.FACTIONS

    #     ui._cooldown_selected({"popup": "Popup only"}, "Popup only")
    #     assert ui.bgstally.state.FcCooldown.get() == "popup"
    #     ui.bgstally.state.refresh.assert_called_once()

    def test_frame_shows_update_notice(self, harness) -> None:
        ui = harness.plugin.ui
        ui.bgstally.update_manager.update_available = True
        ui.bgstally.api_manager.api_updated = False

        ui.update_plugin_frame()

        assert ui.lbl_version.cget('text') == "Update will be installed on shutdown"
        assert ui.lbl_version.url == "https://github.com/aussig/BGS-Tally/releases/latest"
        assert ui.lbl_version.foreground == "red"

    def test_frame_shows_api_notice(self, harness, monkeypatch) -> None:
        ui = harness.plugin.ui
        monkeypatch.setattr(ui, 'btn_carrier', None) # also covers the no-carrier-button path
        ui.bgstally.update_manager.update_available = False
        ui.bgstally.api_manager.api_updated = True

        ui.update_plugin_frame()

        assert ui.lbl_version.cget('text') == "API changed, open settings to re-approve"
        assert ui.lbl_version.url == ""
        assert ui.lbl_version.foreground == "red"

    def test_system_info_no_factions(self, harness) -> None:
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

    def test_toggle_switches_frames(self, harness) -> None:
        ui = harness.plugin.ui

        assert ui.bgstally.state.plugin_hidden is False
        assert ui.expanded_frame.grid_info() != {}
        assert ui.collapsed_frame.grid_info() == {}

        ui.view.toggle()

        assert ui.bgstally.state.plugin_hidden is True
        assert ui.expanded_frame.grid_info() == {}
        assert ui.collapsed_frame.grid_info() != {}

        ui.view.toggle()

        assert ui.bgstally.state.plugin_hidden is False
        assert ui.expanded_frame.grid_info() != {}
        assert ui.collapsed_frame.grid_info() == {}

    def test_hide_suppresses_overlay(self, harness) -> None:
        ui = harness.plugin.ui
        ui.bgstally.state.enable_overlay = True

        ui.bgstally.overlay.display_message("info", "test")
        assert ui.bgstally.overlay.edmcoverlay.messages != {}

        ui.bgstally.overlay.edmcoverlay.messages.clear()
        ui.view.toggle()
        ui.bgstally.overlay.display_message("info", "test")

        assert ui.bgstally.overlay.edmcoverlay.messages == {}

    def test_worker_exits_on_shutdown(self, harness) -> None:
        ui = harness.plugin.ui
        config.shutting_down = True

        try:
            # Call wrapped function to directly exercise worker loop behavior.
            ui._worker.__wrapped__(ui)
        finally:
            config.shutting_down = False

    def test_worker_updates_tick(self, harness) -> None:
        from bgstally.ui import DATETIME_FORMAT_OVERLAY
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

        state.enable_overlay = True
        ui.bgstally.tick.tick_time = datetime.now(UTC) - timedelta(hours=1) # next predicted tick is well away
        overlay = ui.bgstally.overlay.edmcoverlay
        overlay.messages.clear()
        overlay.shapes.clear()

        config.shutting_down = False

        def _sleep_once(_: float) -> None:
            config.shutting_down = True

        try:
            with patch("bgstally.ui.sleep", side_effect=_sleep_once):
                ui._worker.__wrapped__(ui)

            assert f"Galaxy Tick: {ui.bgstally.tick.get_formatted(DATETIME_FORMAT_OVERLAY)}" in [msg[1] for msg in overlay.messages.values()]
            assert "bgstally-frame-indicator" in overlay.shapes
            assert ui.indicate_activity is False
        finally:
            config.shutting_down = False
