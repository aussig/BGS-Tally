"""
Test harness for EDMC Neutron Dancer plugin.

This harness simulates EDMC's journal entry events and provides tools to test
the plugin's routing functionality without running the full EDMC application.
"""
import os
import json
import sys
import logging
import semantic_version # type: ignore
from pathlib import Path
from typing import Optional, Callable, Dict
from datetime import datetime, timezone
from time import sleep
import logging
import types as _types
import tkinter as tk

# Configure logging to output INFO level messages and higher to the console
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Add plugin directory to path for imports (go up one level from tests/)
plugin_dir:Path = Path(__file__).parent.parent
sys.path.insert(0, str(plugin_dir))

# We keep a copy of edmc_data here.
this_dir:Path = Path(__file__).parent
edmc_dir:Path = Path(__file__).parent / 'edmc'
sys.path.insert(0, str(edmc_dir))

os.environ['EDMC_NO_UI'] = '1'

if 'config' not in sys.modules:
    class MockConfig:
        def __init__(self):
            self.data = {'loglevel': 'DEBUG',
                         'ui_scale': 100,
                         'theme' : 0} # Any variables that need setting
            self.shutting_down = False
            self.app_dir_path = this_dir

        def __setitem__(self, key, value):
            self.data[key] = value

        def __getitem__(self, key):
            return self.data.get(key)

        def get(self, key, default=None):
            return self.data.get(key, default)

        def set(self, key, value):
            self.data[key] = value

        def get_int(self, key, default=None):
            return int(self.data.get(key, default)) #type: ignore
        
        def get_str(self, key, default=None):
            return str(self.data.get(key, default)) #type: ignore

        def delete(self, key: str, *, suppress=False) -> None:
            if key in self.data:
                del self.data[key]

    def appversion() -> semantic_version.Version:
        return semantic_version.Version('1.0.0')

    _cfg = _types.ModuleType('config')
    _cfg.appname = 'EDMC' # type:ignore
    _cfg.config = MockConfig() # type:ignore    
    _cfg.appversion = appversion
    _cfg.appcmdname = "EDMC"
    _cfg.config_logger = logging.getLogger("pre_config")
    _cfg.shutting_down = False # type:ignore
    _cfg.logger = (logging.getLogger('TestHarness'))
    sys.modules['config'] = _cfg

# Minimal EDMC `theme` module emulator for direct runs (examples.py / __main__)
theme_mod = _types.ModuleType("theme")
theme_mod.theme = _types.SimpleNamespace() # type:ignore
theme_mod.theme.name = "default"
theme_mod.theme.dark = False
sys.modules['theme'] = theme_mod

class MockCAPIData:
    def __init__(self, data = None, source_host = None, source_endpoint = None, request_cmdr = None) -> None:
        pass

_companion = _types.ModuleType('companion')
_companion.SERVER_LIVE = ''
sys.modules['companion'] = _companion

_capidata = _types.ModuleType('CAPIData')
for name, val in MockCAPIData.__dict__.items():
    if not name.startswith('__'):
        setattr(_capidata, name, val)
sys.modules['companion.CAPIData'] = _capidata

_monitor = _types.ModuleType('EDLogs')
class MockEDLogs:    
    def __init__(self) -> None:
        pass        

for name, val in MockEDLogs.__dict__.items():
    if not name.startswith('__'):
        setattr(_monitor, name, val)

_monitor.monitor = MockEDLogs
sys.modules['monitor'] = _monitor

_plug = _types.ModuleType('Plugin')
class MockPlugin:    
    def __init__(self) -> None:
        pass        

for name, val in MockPlugin.__dict__.items():
    if not name.startswith('__'):
        setattr(_plug, name, val)

sys.modules['plug'] = _plug

_l10n = _types.ModuleType('l10n')
sys.modules['l10n'] = _l10n
_translations = _types.ModuleType('Translations')
class MockTranslations:
    def __init__(self) -> None:
        pass
    def translate(self, x = "", context = None, lang = None) -> str:
        return ""

for name, val in MockTranslations.__dict__.items():
    if not name.startswith('__'):
        setattr(_translations, name, val)
_l10n.Translations = _translations
_l10n.translations = _translations
_l10n.LOCALISATION_DIR = 'L10n'
_locale = _types.ModuleType('_Locale')
class MockLocale:
    def __init__(self) -> None:
        pass
for name, val in MockLocale.__dict__.items():
    if not name.startswith('__'):
        setattr(_locale, name, val)
_l10n.Locale = _locale

sys.modules['l10n'] = _l10n
class MockEDMCOverlay:
    def __init__(self): pass

class Mockedmcoverlay:
    def __init__(self): pass

    class Overlay():
        def __init__(self): pass
        @staticmethod
        def send_message(**kw): pass

_edmcoverlay = _types.ModuleType('EDMCOverlay')
for name, val in MockEDMCOverlay.__dict__.items():
    if not name.startswith('__'):
        setattr(_edmcoverlay, name, val)
sys.modules['EDMCOverlay'] = _edmcoverlay

_overlay = _types.ModuleType('edmcoverlay')
for name, val in Mockedmcoverlay.__dict__.items():
    if not name.startswith('__'):
        setattr(_overlay, name, val)
sys.modules['EDMCOverlay.edmcoverlay'] = _overlay

# Mock up the modern overlay and its plugin
class MockOverlay_Plugin:
    def __init__(self, **kw): pass
class Mockoverlay_api:
    def __init__(self, **kw): pass
    @staticmethod
    def define_plugin_group(**kw): pass

_overlay_plugin = _types.ModuleType('overlay_plugin')
for name, val in MockOverlay_Plugin.__dict__.items():
    if not name.startswith('__'):
        setattr(_overlay_plugin, name, val)
sys.modules['overlay_plugin'] = _overlay_plugin

_overlay_api = _types.ModuleType('overlay_api')
for name, val in Mockoverlay_api.__dict__.items():
    if not name.startswith('__'):
        setattr(_overlay_api, name, val)
sys.modules['overlay_plugin.overlay_api'] = _overlay_api

# Now we can import Router modules
from load import plugin_start3, plugin_app

class TestHarness:
    """ Main test harness for the Neutron Dancer plugin. """
    # Prevent pytest from trying to collect this helper class as a test class
    __test__ = False

    def __init__(self, plugin_dir:Optional[str] = None):
        """ Initialize the test harness. """
        if plugin_dir is None:
            plugin_dir = str(Path(__file__).parent)

        self.plugin_dir:Path = Path(plugin_dir).resolve()
        self.live_dir:Path = Path(__file__).parent.parent.resolve()

        # Load our event sequences
        self.events:Dict[str, list] = self._load_events()

        # This got stuck with annoying PhotoImage
        try:
            root:tk.Tk = tk.Tk()
            parent:tk.Frame = tk.Frame(root)
        except Exception as e:
            print(f"{e}")
            pass
        root.withdraw()

        plugin_start3(str(self.live_dir))
        plugin_app(parent)

        import bgstally.globals
        self.bgstally = bgstally.globals.this

        
        self.is_beta = False
        self.commander = 'Testy McTest Face'
        self.system = 'Sol'

        # Event handlers registered by plugins
        self.journal_handlers: list[Callable] = []
        return


    def setup(self, config_file:str = "test_config.json") -> None:
        """ Setup the harness with a specific config file. """

        # Load config
        config_path:Path = self.plugin_dir / "data" / config_file
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    self.router._from_dict(json.load(f))
            except Exception as e:
                print(f"Warning: Could not load setup file {config_path}: {e}")


    def set_edmc_config(self, config_file:str = "emdc_config.json") -> None:
        # Load config
        config_path:Path = self.plugin_dir / "data" / config_file
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    self.config.set(json.load(f))
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
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load journal_events.json: {e}")

        return events
