# BGS-Tally Test Harness

This is a unit testing tool for EDMC that mocks up EDMC functionality in order to run pytest unit tests.

This is a work in progress Not all EDMC or tool functionality is mocked up yet.

## Components

### Harness

The `harness.py` does the initialization of EDMC. It uses some actual EDMC modules and some mock modules from the `edmc` folder.

The harness provides a mock edmc config object loaded from `config/edmc_config.ini` and a journal event replay capability.

Journal records can be loaded from a json file using `load_events()` and then called individually with `fire_event` or in sequence with `play_sequence`. The journal record processing supports f strings so that they can be customized and supports `delta:` and `now:` for times. e.g. `"DepartureTime": "delta:-60"` or `"CarrierID": "{self.plugin.fleet_carrier.carrier_id}"`.

### Test files

Test files and data live in the `/tests` folder which is where BGS-Tally will look for files by default and, apart from the `/assets` and `/data` folders, it uses test-specific data files from within `/tests`.

Unit tests exist in files that start `test_`. These import the test harness, initialize it, and define a class (or classes) with functions that pytest will run.

The harness initialization may vary depending on the tests and the plugin. It typically loads BGS-Tally and then calls the BGS-Tally initial load functions just as EDMC would.

Prior to loading BGS-Tally it may be desirable to copy a standardized version of a BGS-Tally save file to ensure consistent initial conditions.

It will often load a set of journal events that the test series will require and registers the BGS-Tally `journal_entry` function as the recipient of those events when triggered.

### Writing tests

At their most basic a test is just a matter of calling a BGS-Tally function and verifying the result or that the outcome is as expected.

Testing can get quite sophisticated. pytest's monkeypatch capability can intercept individual functions enabling some advanced setup.

### Running tests

Setup a python virtual environment and install `pytest`. You an then run `pytest` from the command line or from within an IDE such as VS Code. If you install the python debugger you can run the tests with the debugger enabling breakpoints and all that fun stuff.

### Debugging tests

With an IDE such as VS Code tests can be run using the python debugger to step through sections.

### Test coverage

`pytest-cov` enables code coverage. In VS Code which lines have, and have not, been executed are highlighted.

## Directories

The test environment is entirely contained within the `/tests` directory.

### /tests/config

This folder is used for test config files including `edmc_config.json` that is used to store EDMC config items, `journal_events.json` used to store journal events that can be replayed and test configuration files.

### /tests/edmc

This contains live and mock edmc modules used to emulate EDMC so the BGS-Tally can run standalone.

### Others

Other folders created by BGS-Tally for saving data will be created in `/tests` to avoid overwriting or corrupting files in the main plugin directory.

## Tips and Tricks

### Mock EDMC Config

The harness mocks the EDMC config and loads config/edmc_config.json as an initial config.

If you want to use an entirely different config for a specific tests call `load_edmc_config(file)`.

### Other data

It's often desirable to use a consistent configuration for testing. BGS-Tally typically stores these in `otherdata`. This can be achieved by storing a standard version in `config` and copying it to `otherdata` prior to startup e.g.

```python
   shutil.copy(Path(__file__).parent / "config" / "colonisation.json",  Path(__file__).parent / "otherdata" / "colonisation.json")
```

### Mock HTTP Requests

By default these are mocked and what they return can be set by using:

```python
from tests.edmc.requests import queue_response, MockResponse
queue_response(method:str, response: MockResponse, url:str|None = None, sticky:bool = False)
```

* `sticky` indicates the response should be for all matching requests, otherwise it's returned just once
* `url` will match only requests with the appropriate method and matching url. If blank any request will be matched

Requests can be made live in any of the following ways:

1. Initializing the harness object with `live_requests=True`, good for an entire suite of tests
1. Adding the decorator `@pytest.mark.live_requests` to a test function, good for a single test
1. Calling `set_requests_mode(True)` on the harness, good for changing the mode partway through a test

### Mock Journal Events

A journal event can be mocked simply by calling `journal_entry` but the test harness provides a more sophisticated solution.

It works as follows:

1. Sequences of journal events are loaded from a json file using `load_events`
1. The BGS-Tally's journal handling function is registered with the harness using `register_journal_handler`
1. A test can then fire individual events with `fire_event` or replay an entire sequence with `play_sequence`

Events fired this way will be given a current timestamp and the json event file can contain f strings enabling variable data or specific timing.

```json
{ "event":"CarrierJumpRequest", "CarrierType":"FleetCarrier", "CarrierID":"{self.plugin.fleet_carrier.overview.get('carrier_id')}", "SystemName":"Bleae Thua ZE-I b23-1", "Body":"Bleae Thua ZE-I b23-1 AB 1", "SystemAddress":2867293399241, "BodyID":12, "DepartureTime":"now:" }
```
