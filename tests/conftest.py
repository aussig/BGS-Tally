# Sections marked PLUGIN need editing to reuse this file for another plugin; the rest is generic.
import sys
import threading
import time
from datetime import datetime, UTC
from time import monotonic, sleep as real_sleep
from typing import Generator

import pytest
from harness import TestHarness

JOIN_S:float = 2

# GENERIC: set at teardown to end every worker thread sleeping via _sleep
stop:threading.Event = threading.Event()

# GENERIC: keep as is; test files override it
@pytest.fixture
def pre_start():
    """Per-file setup run before the plugin starts; override to return a function taking (request, harness)."""
    return lambda request, harness: None


# PLUGIN: wires TestHarness to your plugin; edit the marked steps, keep the harness, yield and teardown
@pytest.fixture
def harness(request, pre_start) -> Generator:
    """Fresh harness with the plugin started and journal events loaded."""
    live:bool = request.node.get_closest_marker('live_requests') is not None
    test_harness:TestHarness = TestHarness(live_requests=live)

    # PLUGIN: point your plugin's asset and data folders at the real ones
    import bgstally.constants
    bgstally.constants.FOLDER_ASSETS = "../assets"
    bgstally.constants.FOLDER_DATA = "../data"

    # PLUGIN: queue mocked responses for whatever your plugin requests at startup
    if not live:
        from tests.edmc.requests import queue_response, MockResponse
        url:str = 'http://tick.infomancer.uk/galtick.json'
        tick:str = datetime.now(UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        queue_response('get', MockResponse(200, url=url, json_data={"lastGalaxyTick": tick}), url=url, sticky=True)

    pre_start(request, test_harness)

    # PLUGIN: import and start your plugin through its load.py entry points
    from load import plugin_start3, plugin_app, journal_entry
    import bgstally.globals
    test_harness.plugin = bgstally.globals.this

    plugin_start3(str(test_harness.plugin_dir))
    plugin_app(test_harness.parent)

    # PLUGIN: your journal events file, and the commander and system to simulate
    test_harness.load_events("journal_events.json")
    test_harness.register_journal_handler(journal_entry, 'Testy', 'Sol', False)

    yield test_harness
    test_harness.assert_no_unhandled_exceptions()

def _sleep(secs:float) -> None:
    """Sleep, but end a worker thread as soon as stop is set."""
    if threading.current_thread() is threading.main_thread(): return real_sleep(secs)
    if stop.wait(secs): raise SystemExit

# Installed once at import so any later "from time import sleep" binds this; per-test patching would miss them
time.sleep = _sleep

@pytest.fixture(autouse=True)
def stop_workers():
    """Stop and join the workers started during each test."""
    stop.clear()
    before:set = set(threading.enumerate())

    yield

    stop.set()

    # PLUGIN: wake any worker blocked on a queue (here the request queue) so it sees stop
    plugin = getattr(sys.modules.get('bgstally.globals'), 'this', None)
    if plugin is not None: plugin.request_manager.request_queue.put(None)

    deadline:float = monotonic() + JOIN_S
    # PLUGIN: your worker threads' name prefix
    for t in set(threading.enumerate()) - before:
        if t.name.startswith('BGSTally'): t.join(max(0, deadline - monotonic()))
