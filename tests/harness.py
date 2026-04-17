"""
Test harness for EDMC plugins.

This harness simulates EDMC's journal entry events and provides tools to test
the plugin's routing functionality without running the full EDMC application.
"""
import shutil
import threading
threading.get_native_id = lambda: 0

import os
import atexit
import json
import sys
import tomllib
from pathlib import Path
from typing import Optional, Callable, Dict
from datetime import datetime, timezone, timedelta, UTC
from time import sleep, monotonic
import logging
import tkinter as tk
import threading
from typing import Any
from types import SimpleNamespace

edmc_dir:Path = Path(__file__).parent / 'edmc'
sys.path.insert(0, str(edmc_dir))

# Configure logging to output INFO level messages and higher to the console
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Add plugin directory to path for imports (go up one level from tests/)
test_dir:Path = Path(__file__).parent
sys.path.insert(0, str(test_dir))

CONFIG_FILES:dict = {
    'Backpack': ('Backpack.json', "Items"),
    'Cargo': ('Cargo.json', "Inventory"),
    'Market': ('Market.json', "Items"),
    'ModuleInfo': ('ModulesInfo.json', "Modules"),
    'NavRouteClear': ('NavRoute.json', 'Route'),
    'Outfitting': ('Outfitting.json', 'Items'),
    'ShipLocker': ('ShipLocker.json', 'Items'),
    'Shipyard': ('Shipyard.json', 'Pricelist'),
    'Status': ('Status.json', '')
}

STARTUP_ATTRS:dict = {
    'StarSystem': 'SystemName',
    'StarPos': 'StarPos',
    'SystemAddress': 'SystemAddress',
    'Population': 'SystemPopulation',
    'Body': 'Body',
    'BodyID': 'BodyID',
    'BodyType': 'BodyType',
    'MarketID': 'MarketID',
    'StationName': 'StationName',
    'StationType': 'StationType'
}

import tests.edmc.requests
import tests.edmc.mocks as mocks
from tests.edmc.TkScheduler import HarnessTkScheduler
from tests.edmc.monitor import monitor


class TestHarness:
    """ Main test harness. """
    # Prevent pytest from trying to collect this helper class as a test class
    __test__ = False
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, plugin_dir:Optional[str] = None, live_requests:bool = False):
        """ Initialize the test harness. """

        if plugin_dir is None:
            plugin_dir = str(Path(__file__).parent)

        self.plugin_dir:Path = Path(plugin_dir).resolve()
        self.plugin:Any = None

        # Copy the initial config state files
        Path(__file__).parent.joinpath("journal_folder").mkdir(exist_ok=True)
        for (file, key) in CONFIG_FILES.values():
            shutil.copy(Path(__file__).parent / "journal_config" / file,
                Path(__file__).parent / "journal_folder" / file)

        monitor.currentdir = str(Path(__file__).parent / "journal_folder")
        self.monitor = monitor
        self.monitor.state['Credits'] = 1000000
        self.unhandled_exceptions:list[str] = []

        # Event handlers registered by plugins
        self.journal_handlers: list[Callable] = []
        self.config = mocks.MockConfig()
        self.set_edmc_config() # Load config data into the mock config object
        self.events:Dict[str, list] = {}
        self.set_requests_mode(live_requests)

        if not hasattr(self, '_original_threading_excepthook'):
            self._original_threading_excepthook = threading.excepthook
        threading.excepthook = self._capture_thread_exception

        #os.environ['EDMC_NO_UI'] = '1'

        # Create Tk root for headless mode
        try:
            if not hasattr(self, '_initialized'):
                self.root:tk.Tk = tk.Tk()
                self.parent:tk.Frame = tk.Frame(self.root)
                #root.withdraw()
        except Exception as e:
            logging.error(f"Failed to create Tk root: {e}")

        if hasattr(self, 'root') and not hasattr(self, '_tk_scheduler'):
            self._tk_scheduler = HarnessTkScheduler(self.root)
            self._tk_scheduler.install()
            if not hasattr(self, '_atexit_registered'):
                atexit.register(self._tk_scheduler.uninstall)
                self._atexit_registered = True

        self._initialized = True

    def _capture_thread_exception(self, args: threading.ExceptHookArgs) -> None:
        """Record unhandled worker-thread exceptions so tests can fail deterministically."""
        exc_type = getattr(args.exc_type, '__name__', str(args.exc_type))
        thread_name = getattr(args.thread, 'name', '<unknown>')
        self.unhandled_exceptions.append(f"{thread_name}: {exc_type}: {args.exc_value}")

        if hasattr(self, '_original_threading_excepthook') and self._original_threading_excepthook:
            self._original_threading_excepthook(args)

    def assert_no_unhandled_exceptions(self) -> None:
        """Fail the current test if any unhandled thread exceptions were captured."""
        self.pump_ui(timeout_s=0.4)

        scheduler_failures: list[str] = []
        if hasattr(self, '_tk_scheduler'):
            scheduler_failures = self._tk_scheduler.consume_failures()
            if scheduler_failures:
                self.unhandled_exceptions.extend(scheduler_failures)

        if not self.unhandled_exceptions:
            return

        failures = "\n".join(f"- {item}" for item in self.unhandled_exceptions)
        self.unhandled_exceptions.clear()
        raise AssertionError(
            "Unhandled exception(s) were raised by background thread(s):\n"
            f"{failures}"
        )

    def pump_ui(self, timeout_s: float = 0.2, poll_interval_s: float = 0.01) -> None:
        """Pump deferred Tk callbacks and process pending UI events."""
        if not hasattr(self, 'root'):
            return

        end_time = monotonic() + max(timeout_s, 0.0)

        while True:
            callbacks_ran = 0
            if hasattr(self, '_tk_scheduler'):
                callbacks_ran = self._tk_scheduler.drain_due_callbacks()

            try:
                self.root.update_idletasks()
                self.root.update()
            except tk.TclError:
                return

            pending = self._tk_scheduler.pending_count() if hasattr(self, '_tk_scheduler') else 0
            if pending == 0 and callbacks_ran == 0:
                return
            if monotonic() >= end_time:
                return

            sleep(poll_interval_s)

    def set_requests_mode(self, live_requests:bool) -> None:
        """ Set whether the harness should use live HTTPS requests or mocked responses. """
        self.live_requests = live_requests
        tests.edmc.requests.live_requests(live_requests)

    def set_edmc_config(self, config_file:str = "config.toml") -> None:
        """ Load a config file from the config directory and set it in the mock config object. """
        config_path:Path = self.plugin_dir / "config" / config_file
        if not config_path.is_file():
            self.config.data = {}
            logging.warning(f"Warning: edmc's config file not found {config_path}")
            return
        try:
            with config_path.open('rb') as f:
                match config_path.suffix:
                    case '.toml':
                        self.config.data = tomllib.load(f)
                        self.config.data = self.config.data['settings']
                    case '.json':
                        self.config.data = json.load(f)
                    case _:
                        self.config.data = {}

        except Exception as e:
            logging.warning(f"Warning: Could not load edmc config file {config_path}: {e}")

        self.config.data['app_dir_path'] = str(self.plugin_dir) # Override app_dir_path
        self.config.data['outdir'] = str(self.plugin_dir) # Override outdir path
        logging.info(f"Config data: {self.config.data}")

    def get_config_data(self, config_file:str) -> dict:
        """Read and return a chosen config file. Useful for comparing plugin output to expected config data."""

        config_path:Path = self.plugin_dir / "config" / config_file
        format = config_file.split('.')[1]
        if not config_path.is_file():
            return {}
        try:
            with config_path.open('rb') as f:
                match format:
                    case 'toml':
                        data = tomllib.load(f)
                        if 'settings' in data:
                            return data['settings']
                        return data
                    case 'json':
                        return json.load(f)
                    case 'csv':
                        #@TODO: Add csv support
                        return {}
                    case _:
                        logging.warning(f"Warning: Unsupported config file format: {format}")
                        return {}
        except Exception as e:
            logging.warning(f"Warning: Could not load {format} config file {config_path}: {e}")
            return {}

    def load_state(self, source:str) -> dict:
        """ Load monitor state from a json file. """
        state_file = Path(self.plugin_dir, "config", source)
        logging.info(f"State file: {state_file}")
        if not state_file.exists():
            logging.warning(f" State file {state_file} not found")
            return {}
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
                self.monitor.state.update(state)
                return state
        except Exception as e:
            logging.warning(f"Warning: Could not load {state_file}: {e}")
            return {}

    def load_events(self, source:str, **kwargs) -> dict[str, list[dict]]:
        """ Load journal events from a json file or a direct ED log. """

        events_file = Path(self.plugin_dir, "journal_config", source)
        logging.info(f"Events file: {events_file}")
        params = SimpleNamespace(**kwargs)
        if not events_file.exists():
            logging.warning(f" Events file {events_file} not found")
            return {}
        try:
            with open(events_file, 'r') as f:
                if events_file.suffix == '.json':
                    tmp:dict[str, list[dict]] = json.load(f)
                else:
                    # Assume it's a direct ED log
                    tmp:dict[str, list[dict]] = {"default": [json.loads(line) for line in f.readlines()]}

                # The following allows the use of f strings in the json which enables time-based events.
                res:dict[str, list[dict]] = {}
                for sequence, elements in tmp.items():
                    lines:list[dict] = []
                    for line in elements:
                        event:dict = {}
                        for k1, v1 in line.items():
                            event[k1] = v1
                            if isinstance(v1, str) and v1.startswith("delta:"):
                                delta_seconds = int(v1.split(":")[1])
                                event[k1] = (datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)).isoformat()
                            if isinstance(v1, str) and v1.startswith("now:"):
                                event[k1] = datetime.now(timezone.utc).isoformat()
                            if isinstance(v1, str) and '{' in v1 and '}' in v1:
                                try:
                                    event[k1] = eval("f'" + v1 + "'")
                                except Exception as e:
                                    logging.warning(f"Warning: Could not evaluate f-string {v1}: {e}")
                            if isinstance(event[k1], str) and event[k1].isnumeric():
                                event[k1] = int(event[k1])
                        lines.append(event)
                    res[sequence] = lines
            self.events = res
            return res

        except Exception as e:
            logging.warning(f"Warning: Could not load {events_file}: {e}")
            return {}

    def register_journal_handler(self, handler: Callable, commander:str, system:str, is_beta:bool) -> None:
        """ Register a journal event handler (simulates journal_entry callback). """
        self.journal_handlers.append(handler)
        self.monitor.cmdr = commander
        self.monitor.state['SystemName'] = system
        self.monitor.is_beta = is_beta

    def fire_event(self, event:dict, state:dict = {}) -> None:
        """ Fire a journal event through the harness. """

        # Update monitor state with provided state data before firing the event
        self.monitor.state.update(state)
        self.monitor.state['Credits'] = state.get('Credits', self.monitor.state.get('Credits', 1000000))

        self._update_journal_files(event, state)

        # Add a timestamp if not provided.
        if 'timestamp' not in event:
            event['timestamp'] = datetime.now(timezone.utc).isoformat()

        # Do the opposite of what EDMC does with a startup event. i.e. update monitor fron the faux event rather than create a faux event from the monitor state.
        if event['event'] == 'Startup':
            for k, v in STARTUP_ATTRS.items():
                if k in event:
                    self.monitor.state[v] = event[k]
            if 'StationName' in event:
                self.monitor.state['Docked'] = True
        else:
            self.monitor.parse_entry(json.dumps(event).encode("utf-8"))

        # Call registered handler(s)
        for handler in self.journal_handlers:
            try:
                handler(
                    cmdr=self.monitor.cmdr,
                    is_beta=self.monitor.is_beta,
                    system=self.monitor.state['SystemName'],
                    station=self.monitor.state['StationName'],
                    entry=event,
                    state=self.monitor.state
                )
            except Exception as e:
                logging.error(f"Error in journal handler: {e}")
                raise

        self.pump_ui()

    def play_sequence(self, name:str, delay:float = 0.5, state:dict = {}) -> None:
        """ Fire a sequence of events """
        for event in self.events.get(name, []):
            self.fire_event(event, state=state)
            state = {}  # Clear state after the first event
            sleep(delay)
            self.pump_ui()

    def _update_journal_files(self, event:dict, state:dict = {}) -> None:
        """ Simulate EDMC's journal file updates based on the event type. """
        # Update the separate journal files that ED maintains
        match event['event']:
            case 'Cargo' | 'MarketBuy' | 'MarketSell' | 'CargoTransfer' | 'CollectCargo' | 'EjectCargo' | 'MiningRefined' | 'LaunchDrone':
                cargo:dict = state.get('Cargo', {})
                if not cargo:
                    with open(self.plugin_dir / "journal_folder" / CONFIG_FILES['Cargo'][0], 'r') as f:
                        cargo = json.load(f)
                cargo['Inventory'] = cargo.get('Inventory', [])

                match event['event']:
                    case 'CargoTransfer':
                        for item in event.get('Transfers', []):
                            cargo['Inventory'].append({
                                'Name': self.monitor.canonicalise(item['Type']),
                                'Name_Localised': item.get('Type_Localised', self.monitor.canonicalise(item['Type'])),
                                'Count': item['Count'] if item.get('Direction') == "toship" else -item['Count'],
                                'Stolen': item.get('Stolen', 0)
                            })
                    case 'MarketBuy' | 'MarketSell' | 'CollectCargo' | 'EjectCargo' | 'MiningRefined':
                        cargo['Inventory'].append({
                            'Name': self.monitor.canonicalise(event['Type']),
                            'Name_Localised': event.get('Type_Localised', self.monitor.canonicalise(event['Type'])),
                            'Count': event['Count'] if event['event'] in ['MarketBuy', 'CollectCargo'] else -event['Count'],
                            'Stolen': event.get('Stolen', 0)
                        })
                    case 'LaunchDrone':
                        cargo['Inventory'].append({
                            'Name': "drone",
                            'Name_Localised': "Drone",
                            'Count': -1,
                            'Stolen': 0
                        })
                    case 'Cargo' if 'Cargo' in state:
                        cargo = state['Cargo']
                        if 'Inventory' not in cargo: cargo['Inventory'] = []

                cargo['Inventory'] = self.monitor.coalesce_cargo(cargo['Inventory'])
                cargo['Count'] = sum(item['Count'] for item in cargo['Inventory'])

                with open(self.plugin_dir / "journal_folder" / CONFIG_FILES['Cargo'][0], 'w') as f:
                    json.dump(cargo, f)

            case _ if event['event'] in CONFIG_FILES.keys():
                # Add empty elements where we're unable to infer them.
                if CONFIG_FILES[event['event']][1] and CONFIG_FILES[event['event']][1] not in event:
                     event[CONFIG_FILES[event['event']][1]] = state.get(CONFIG_FILES[event['event']][1], [])
                with open(self.plugin_dir / "journal_folder" / CONFIG_FILES[event['event']][0], 'w') as f:
                    json.dump(event, f)
