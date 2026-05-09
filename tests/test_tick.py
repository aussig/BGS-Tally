"""Test the tick handling code for BGS-Tally."""

import pytest # type: ignore
from typing import Generator
from pathlib import Path
import shutil
from time import sleep
from datetime import datetime, UTC
from unittest.mock import patch

# Config is already mocked by conftest.py
from harness import TestHarness

from bgstally.constants import DATETIME_FORMAT_ACTIVITY, DATETIME_FORMAT_TICK_DETECTOR_SYSTEM
from bgstally.constants import RequestMethod
from bgstally.tick import URL_GALAXY_TICK_DETECTOR, URL_SYSTEM_TICK_DETECTOR, TICKID_UNKNOWN
from bgstally.requestmanager import BGSTallyRequest


@pytest.fixture
def harness(request) -> Generator:
    """Provide a fresh test harness for each test."""
    live = request.node.get_closest_marker('live_requests') is not None

    test_harness:TestHarness = TestHarness(live_requests=live)

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

    yield test_harness
    test_harness.assert_no_unhandled_exceptions()


class TestTick:
    """Tick module tests."""

    def test_fetch_tick_with_mocked_response(self, harness) -> None:
        from tests.edmc.requests import queue_response, MockResponse

        harness.plugin.tick.tick_time = datetime(2000, 1, 1, tzinfo=UTC)

        queue_response('get', MockResponse(200, url=URL_GALAXY_TICK_DETECTOR,
                                           json_data={'lastGalaxyTick': datetime.now(UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')}),
                       url=URL_GALAXY_TICK_DETECTOR)

        result = harness.plugin.tick.fetch_tick()

        assert result is True
        assert harness.plugin.tick.tick_id != TICKID_UNKNOWN
        assert harness.plugin.tick.tick_time > datetime(2000, 1, 1, tzinfo=UTC)

    @pytest.mark.live_requests
    def test_fetch_tick_with_live_response(self, harness) -> None:
        result = harness.plugin.tick.fetch_tick()

        assert result is not None
        assert harness.plugin.tick.tick_id.startswith("zoy-") or result is False

    def test_force_tick_generates_forced_id(self, harness) -> None:
        harness.plugin.tick.force_tick()

        assert harness.plugin.tick.tick_id.startswith("frc-")
        assert harness.plugin.tick.tick_time is not None

    def test_system_tick_received_updates_current_activity(self, harness) -> None:
        from tests.edmc.requests import MockResponse

        current_system_id = "12345"
        harness.plugin.state.current_system_id = current_system_id
        current_activity = harness.plugin.activity_manager.get_current_activity()
        current_activity.systems[current_system_id] = {}
        current_activity.dirty = False

        timestamp = datetime.now(UTC).strftime(DATETIME_FORMAT_TICK_DETECTOR_SYSTEM)
        response = MockResponse(200, json_data={'timestamp': timestamp})
        request = BGSTallyRequest(URL_SYSTEM_TICK_DETECTOR,
                                 RequestMethod.POST,
                                 callback=None,
                                 params={},
                                 headers={},
                                 stream=False,
                                 payload=None,
                                 data={'SystemAddress': current_system_id},
                                 attempts=0)

        harness.plugin.tick._system_tick_received(True, response, request)

        assert current_activity.systems[current_system_id]['TickTime'] == datetime.strptime(timestamp, DATETIME_FORMAT_TICK_DETECTOR_SYSTEM).replace(tzinfo=UTC).strftime(DATETIME_FORMAT_ACTIVITY)
        assert current_activity.dirty is True
