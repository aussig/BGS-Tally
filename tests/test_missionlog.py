"""Test the missionlog code for BGS-Tally."""

from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Generator
import shutil

import pytest # type: ignore

# Config is already mocked by conftest.py
from harness import TestHarness

from bgstally.constants import DATETIME_FORMAT_JOURNAL, FOLDER_OTHER_DATA
from bgstally.missionlog import MissionLog, TIME_MISSION_EXPIRY_D


@pytest.fixture
def harness(request) -> Generator:
    """Provide a fresh test harness for each test."""
    live = request.node.get_closest_marker('live_requests') is not None

    test_harness: TestHarness = TestHarness(live_requests=live)

    import bgstally.constants
    bgstally.constants.FOLDER_ASSETS = "../assets"
    bgstally.constants.FOLDER_DATA = "../data"

    # Put in a response for the update manager so it doesn't error
    if not live:
        from tests.edmc.requests import queue_response, MockResponse
        queue_response('get',
                       MockResponse(200, url='https://api.github.com/repos/aussig/BGS-Tally/releases/latest',
                                    json_data={'tag_name': 'v1.0.0','draft': True,'prerelease': True,
                                                'assets': [{'browser_download_url': 'https://example.com/download'}]}),
                        url='https://api.github.com/repos/aussig/BGS-Tally/releases/latest')
        queue_response('get',
                       MockResponse(200, url='http://tick.infomancer.uk/galtick.json',
                                    json_data={"lastGalaxyTick": datetime.now(UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')}),
                        url='http://tick.infomancer.uk/galtick.json', sticky=True)

    Path(Path(__file__).parent / "otherdata" / "missionlog.json").unlink(missing_ok=True)
    missionlog_init_file:str = getattr(request, 'param', 'missionlog_init.json')
    if missionlog_init_file != 'None':
        shutil.copy(Path(__file__).parent / "config" / missionlog_init_file,
                    Path(__file__).parent / "otherdata" / "missionlog.json")

    # Now we can import plugin modules
    from load import plugin_start3, plugin_app, journal_entry
    import bgstally.globals
    test_harness.plugin = bgstally.globals.this

    plugin_start3(str(test_harness.plugin_dir))
    plugin_app(test_harness.parent)

    test_harness.register_journal_handler(journal_entry, 'Testy', 'Sol', False)

    yield test_harness
    test_harness.assert_no_unhandled_exceptions()


class TestMissionLogFunctions:
    """Mission log module tests."""

    @pytest.mark.parametrize('harness', ['None', 'missionlog_init.json' ], indirect=True)
    def test_save_files(self, harness) -> None:
        """ Test that the plugin initializes correctly with no existing data and doesn't save an empty overview. """
        mission_log = harness.plugin.mission_log

        # If we start with no file, we should end with a file containing an empty list
        assert mission_log.get_missionlog() == []

        mission_log.save()
        saved_file = Path(harness.plugin.plugin_dir) / FOLDER_OTHER_DATA / "missionlog.json"
        assert saved_file.exists()
        with open(saved_file) as f:
            assert f.read() == "[]"

    def test_no_mission_log(self, harness) -> None:
        mission_log = harness.plugin.mission_log
        mission_log.missionlog.clear()

        assert mission_log.get_missionlog() == []

    def test_add_and_retrieve_mission(self, harness) -> None:
        mission_log = harness.plugin.mission_log
        mission_log.missionlog.clear()

        mission_log.add_mission(
            name="Test Mission",
            faction="Test Faction",
            missionid="1001",
            expiry=datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC).strftime(DATETIME_FORMAT_JOURNAL),
            destination_system="Sol",
            destination_settlement="Test Settlement",
            system_name="Sol",
            station_name="Test Station",
            commodity_count=0,
            passenger_count=0,
            kill_count=0,
            target_faction="Target Faction"
        )

        mission = mission_log.get_mission("1001")

        assert mission is not None
        assert mission["Name"] == "Test Mission"
        assert mission["Faction"] == "Test Faction"
        assert mission["System"] == "Sol"
        assert mission_log.get_mission("missing") is None

    def test_delete_mission_by_id(self, harness) -> None:
        mission_log = harness.plugin.mission_log
        mission_log.missionlog = [
            {"MissionID": 111111, "System": "Sol"},
            {"MissionID": 222222, "System": "Alpha Centauri"}
        ]

        mission_log.delete_mission_by_id(111111)

        assert len(mission_log.missionlog) == 1
        assert mission_log.missionlog[0]["MissionID"] == 222222

    def test_delete_mission_by_index(self, harness) -> None:
        mission_log = harness.plugin.mission_log
        mission_log.missionlog = [
            {"MissionID": 111111, "System": "Sol"},
            {"MissionID": 222222, "System": "Alpha Centauri"}
        ]

        mission_log.delete_mission_by_index(0)

        assert len(mission_log.missionlog) == 1
        assert mission_log.missionlog[0]["MissionID"] == 222222

    def test_get_active_systems_dedupes(self, harness) -> None:
        mission_log = harness.plugin.mission_log
        mission_log.missionlog = [
            {"MissionID": 111111, "System": "Sol"},
            {"MissionID": 222222, "System": "Sol"},
            {"MissionID": 333333, "System": "Alpha Centauri"}
        ]

        assert mission_log.get_active_systems() == ["Sol", "Alpha Centauri"]

    def test_save_and_load_missionlog(self, harness) -> None:
        mission_log = harness.plugin.mission_log
        mission_log.missionlog = [
            {"MissionID": 111111, "System": "Sol", "Name": "Saved Mission", "Expiry": datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC).strftime(DATETIME_FORMAT_JOURNAL)}
        ]

        mission_log.save()
        saved_file = Path(harness.plugin.plugin_dir) / FOLDER_OTHER_DATA / "missionlog.json"

        loaded = MissionLog(harness.plugin)

        assert loaded.get_mission(111111) is not None
        m:dict|None = loaded.get_mission(111111)
        assert m is not None
        assert m.get('Name', '') == "Saved Mission"


    def test_expire_old_missions(self, harness) -> None:
        mission_log = harness.plugin.mission_log
        mission_log.missionlog = [
            {"MissionID": 111111, "System": "Sol", "Name": "Expired Mission", "Expiry": (datetime.now(UTC) - timedelta(days=TIME_MISSION_EXPIRY_D + 1)).strftime(DATETIME_FORMAT_JOURNAL)},
            {"MissionID": 222222, "System": "Alpha", "Name": "Active Mission", "Expiry": (datetime.now(UTC) + timedelta(days=1)).strftime(DATETIME_FORMAT_JOURNAL)}
        ]

        mission_log._expire_old_missions()

        assert mission_log.get_mission(111111) is None
        assert mission_log.get_mission(222222) is not None

class TestMissionLogEvents:
    """Tests for mission log event handling."""

    def test_mission_accepted(self, harness) -> None:
        mission_log = harness.plugin.mission_log
        harness.load_events("mission_events.json")
        harness.play_sequence("accepted")
        assert len(mission_log.get_missionlog()) == 2

    def test_mission_abandoned(self, harness) -> None:
        mission_log = harness.plugin.mission_log
        harness.load_events("mission_events.json")
        harness.play_sequence("abandoned")
        assert len(mission_log.get_missionlog()) == 0
