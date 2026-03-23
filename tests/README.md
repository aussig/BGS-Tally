# BGS-Tally Test Harness

This is a unit testing tool for EDMC that mocks up EDMC functionality in order to run pytest unit tests.

This is a work in progress Not all EDMC or tool functionality is mocked up yet.

## Components

### Harness

The `harness.py` does the initialization of EDMC. It uses some actual EDMC modules and some mock modules from the `edmc` folder.

The harness provides a mock edmc config object that can be loaded from a json file using the `set_edmc_config` function and a journal event replay capability.

Journal records can be loaded from a json file using `load_events` and then called individually with `fire_event` or in sequence with `play_sequence`. The journal record processing supports f strings to that they can be customized. e.g. `"DepartureTime":"{datetime.now(tz=UTC):%Y-%m-%d %H:%M:%S}"}` will always produce a departure time of now.

### Test files

Test files and data live in the `/tests` folder which is where BGS-Tally will look for files by default and, apart from the `/assets` and `/data` folders, it uses test-specific data files from within `/tests`.

Unit tests exist in files that start `test_`. These import the test harness, initialize it, and define a class (or classes) with functions that pytest will run.

The harness initialization may vary depending on the tests and the plugin. It typically loads BGS-Tally and then calls the BGS-Tally initial load functions just as EDMC would.

Prior to loading BGS-Tally it may be desirable to copy a standardized version of a BGS-Tally save file to ensure consistent initial conditions.

It will often load a set of journal events that the test series will require and registers the BGS-Tally `journal_entry` function as the recipient of those events when triggered.

### Writing tests

At their most basic a test is just a matter of calling a BGS-Tally function and verifying the result or that the outcome is as expected.

Testing can get quite sophisticated. pytests's monkeypatch capability can intercept individual functions enabling some advanced setup.

### Running tests

Setup a python virtual environment and install `pytest`. You an then run pytest from the command line or from within an IDE such as VS Code. If you install the python debugger you can run the tests with the debugger enabling breakpoints and all that fun stuff.

## Directories

The test environment is entirely contained within the `/tests` directory. 

### /tests/config

This folder is used for test config files including `edmc_config.json` that is used to store EDMC config items, `journal_events.json` used to store journal events that can be replayed and test configuration files.

### /tests/edmc

This contains live and mock edmc modules used to emulate EDMC so the plugin can run standalone.

### Others

Other folders may be created by the plugin for saving data. These are in `/tests` to avoid overwriting or corrupting files in the main plugin directory.
