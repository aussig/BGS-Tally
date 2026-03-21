"""
Test harness for EDMC Neutron Dancer plugin.

This harness simulates EDMC's journal entry events and provides tools to test
the plugin's routing functionality without running the full EDMC application.
"""
import threading
threading.get_native_id = lambda: 0
threading.thread_native_id = lambda: 0

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

edmc_dir:Path = Path(__file__).parent / 'edmc'
sys.path.insert(0, str(edmc_dir))

# Configure logging to output INFO level messages and higher to the console
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Add plugin directory to path for imports (go up one level from tests/)
test_dir:Path = Path(__file__).parent
sys.path.insert(0, str(test_dir))

import tests.edmc.mocks
from tests.edmc.mocks import MockConfig

class TestHarness:
    """ Main test harness for the Neutron Dancer plugin. """
    # Prevent pytest from trying to collect this helper class as a test class
    __test__ = False
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, plugin_dir:Optional[str] = None):
        """ Initialize the test harness. """

        if plugin_dir is None:
            plugin_dir = str(Path(__file__).parent)

        self.plugin_dir:Path = Path(plugin_dir).resolve()
        
        # Load our event sequences
        self.events:Dict[str, list] = self._load_events()

        # Event handlers registered by plugins
        self.journal_handlers: list[Callable] = []
        self.config = MockConfig()

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


    def set_edmc_config(self, config_file:str = "edmc_config.json") -> None:
        # Load config
        config_path:Path = self.plugin_dir / "config" / config_file               
        if not config_path.is_file():
            self.config.data = {}
            return
        try:
            with open(config_path, 'r') as f:
                self.config.data = json.load(f)                
        except Exception as e:
            print(f"Warning: Could not load edmc config file {config_path}: {e}")

    def register_journal_handler(self, handler: Callable) -> None:
        """ Register a journal event handler (simulates journal_entry callback). """
        self.journal_handlers.append(handler)

    def fire_event(self, event:dict, state:Optional[dict] = None) -> None:
        """ Fire a journal event through the harness. """
        if state is None: state = {}
        sys:str = event.get("StarSystem", event.get("System", ""))
        if sys != "": self.system = sys
        event['timestamp'] = event.get('timestamp', datetime.now(timezone.utc).isoformat())
        # Call all registered handlers
        for handler in self.journal_handlers:
            try:
                handler(
                    cmdr=self.commander,
                    is_beta=self.is_beta,
                    system=self.system,
                    station="",
                    entry=event,
                    state=state
                )
            except Exception as e:
                print(f"Error in journal handler: {e}")
                raise
            sleep(0.5)  # Allow time for any asynchronous processing (if applicable)

    def play_sequence(self, name:str) -> None:
        """ Fire a sequence of events """
        for event in self.events.get(name, []):
            self.fire_event(event)

    def _load_events(self) -> Dict[str, list]:
        """ Load journal events from events.json file. """
        events:Dict[str, list] = {}

        EVENTS_FILE = Path(self.plugin_dir, "config", "journal_events.json")
        logging.info(f"Events file: {EVENTS_FILE}")
        if not EVENTS_FILE.exists():
            return events
        try:
            with open(EVENTS_FILE, 'r') as f:
                tmp:dict = json.load(f)

                # The following allows the use of f strings in the json which enables time-based events.
                res:dict = {}
                for sequence, elements in tmp.items():
                    lines:list = []
                    for line in elements:
                        event:dict = {}
                        for k1, v1 in line.items():                            
                            event[k1] = eval("f'" + v1 + "'") if isinstance(v1, str) else v1
                        lines.append(event)
                    res[sequence] = lines
            print(res)
            return res
                        
        except Exception as e:
            print(f"Warning: Could not load journal_events.json: {e}")

        return events
