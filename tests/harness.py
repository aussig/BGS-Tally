"""
Test harness for EDMC plugins.

This harness simulates EDMC's journal entry events and provides tools to test
the plugin's routing functionality without running the full EDMC application.
"""
import threading
threading.get_native_id = lambda: 0

import os
import json
import sys
from pathlib import Path
from typing import Optional, Callable, Dict
from datetime import datetime, timezone, timedelta, UTC
from time import sleep
import logging
import tkinter as tk
import threading
from typing import Any

edmc_dir:Path = Path(__file__).parent / 'edmc'
sys.path.insert(0, str(edmc_dir))

# Configure logging to output INFO level messages and higher to the console
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Add plugin directory to path for imports (go up one level from tests/)
test_dir:Path = Path(__file__).parent
sys.path.insert(0, str(test_dir))

import tests.edmc.requests
import tests.edmc.mocks
from tests.edmc.mocks import MockConfig
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

        self.monitor = monitor

        # Event handlers registered by plugins
        self.journal_handlers: list[Callable] = []
        self.config = MockConfig()
        self.set_edmc_config() # Load config data into the mock config object
        self.events:Dict[str, list] = {}
        self.set_requests_mode(live_requests)

        os.environ['EDMC_NO_UI'] = '1'

        # Create Tk root for headless mode
        try:
            if not hasattr(self, '_initialized'):
                root:tk.Tk = tk.Tk()
                self.parent:tk.Frame = tk.Frame(root)
                root.withdraw()
        except Exception as e:
            print(f"Failed to create Tk root: {e}")

        self._initialized = True

    def set_requests_mode(self, live_requests:bool) -> None:
        self.live_requests = live_requests
        tests.edmc.requests.live_requests(live_requests)

    def set_edmc_config(self, config_file:str = "edmc_config.json") -> None:
        # Load config
        config_path:Path = self.plugin_dir / "config" / config_file
        if not config_path.is_file():
            self.config.data = {}
            print(f"Warning: edmc's config file not found {config_path}")
        try:
            with open(config_path, 'r') as f:
                self.config.data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load edmc config file {config_path}: {e}")
        self.config.data['app_dir_path'] = str(self.plugin_dir) # Override app_dir_path to plugin dir for testing purposes

    def get_config_data(self, config_file:str) -> str|dict|None:
        """Load and return a chosen config file"""

        config_path:Path = self.plugin_dir / "config" / config_file
        format = config_file.split('.')[1]
        if not config_path.is_file():
            self.config.data = {}
            return
        try:
            with open(config_path, 'r') as f:
                match format:
                    case 'json':
                        return json.load(f)
                    case 'csv':
                        #@TODO: Add csv support
                        return None
                    case _:
                        return f.read()
        except Exception as e:
            print(f"Warning: Could not load {format} config file {config_path}: {e}")
            return

    def load_events(self, source:str) -> dict:
        """ Load journal events from events.json file. """

        events_file = Path(self.plugin_dir, "config", source)
        logging.info(f"Events file: {events_file}")
        if not events_file.exists():
            print(f" Events file {events_file} not found")
            return {}
        try:
            with open(events_file, 'r') as f:
                tmp:dict = json.load(f)

                # The following allows the use of f strings in the json which enables time-based events.
                res:dict = {}
                for sequence, elements in tmp.items():
                    lines:list = []
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
                                event[k1] = eval("f'" + v1 + "'")
                            if isinstance(event[k1], str) and event[k1].isnumeric():
                                event[k1] = int(event[k1])
                        lines.append(event)
                    res[sequence] = lines
            print(res)
            self.events = res
            return res

        except Exception as e:
            print(f"Warning: Could not load {events_file}: {e}")
            return {}

    def register_journal_handler(self, handler: Callable, commander:str, system:str, is_beta:bool) -> None:
        """ Register a journal event handler (simulates journal_entry callback). """
        self.journal_handlers.append(handler)
        self.commander = commander
        self.system = system
        self.is_beta = is_beta

    def fire_event(self, event:dict, state:dict = {}) -> None:
        """ Fire a journal event through the harness. """

        # Update monitor state with provided state data before firing the event
        for k, v in state.items():
            self.monitor.state[k] = v
        # Add a timestamp if not provided.
        if 'timestamp' not in event:
            event['timestamp'] = datetime.now(timezone.utc).isoformat()
        self.monitor.parse_entry(json.dumps(event).encode("utf-8"))

        # Call registered handlers
        for handler in self.journal_handlers:
            try:
                handler(
                    cmdr=self.monitor.cmdr,
                    is_beta=self.monitor.is_beta,
                    system=self.monitor.state['SystemName'],
                    station=self.monitor.state['StationName'],
                    entry=event,
                    state=state
                )
            except Exception as e:
                print(f"Error in journal handler: {e}")
                raise

    def play_sequence(self, name:str, delay:float = 0.5) -> None:
        """ Fire a sequence of events """
        for event in self.events.get(name, []):
            self.fire_event(event)
            sleep(delay)
