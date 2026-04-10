import os
import json
import importlib
import sys
import types as _types
import semantic_version
import logging
from pathlib import Path
from unittest.mock import patch

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    tomllib = importlib.import_module('tomli')

# We keep a copy of edmc_data here.
this_dir:Path = Path(__file__).parent
parent:Path = Path(__file__).parent.parent

# Force it to look like Linux
#with patch.object(sys, 'platform', 'linux'):
#    with patch.dict(os.environ, {'XDG_DATA_HOME': str(this_dir)}, clear=False):
#        import config

class MockConfig:
    _instance = None

    # Singleton pattern
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'): return

        self.data = {} # Any variables that need setting
        self.shutting_down = False
        self.app_dir_path = parent
        self.default_journal_dir = parent / "journal_folder"
        self.internal_plugin_dir_path = self.default_journal_dir
        self.plugin_dir_path = parent
        self._initialized = True

    @staticmethod
    def get_appdirpath() -> Path:
        return this_dir

    def __setitem__(self, key, value):
        self.data[key.lower()] = value

    def __getitem__(self, key):
        a = self.data.get(key)
        b = self.data.get(key.lower())
        logging.info(f"Returning config key: {a} or {b}")
        return self.data.get(key, self.data.get(key.lower(), None))

    def get(self, key, default=None):
        value = self.__getitem__(key)
        return default if value is None else value

    def set(self, key, value):
        self.__setitem__(key, value)

    def get_int(self, key, default=None):
        value = self.__getitem__(key)
        if value is None: return default
        return int(value)

    def get_str(self, key, default=None):
        if key == "journaldir": return self.default_journal_dir
        value = self.__getitem__(key)
        if value is None: return default
        return str(value)

    def delete(self, key: str, *, suppress=False) -> None:
        if key in self.data:
            del self.data[key]

def appversion() -> semantic_version.Version:
    return semantic_version.Version('10.0.0')

_cfg_attrs = {'appname': 'EDMC',
                'appversion': appversion,
                'appcmdname': 'EDMC',
                'app_dir_path': parent,
                'config_logger': logging.getLogger('TestHarness'),
                'shutting_down': False,
                'logger': logging.getLogger('TestHarness')
            }

_cfg = _types.ModuleType('config')
_cfg.config = MockConfig() # type:ignore

for name, val in MockConfig.__dict__.items():
    if not name.startswith('__'):
        setattr(_cfg, name, val)

for name, val in _cfg_attrs.items():
    setattr(_cfg, name, val)

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
_companion.SERVER_LIVE = '' # type: ignore
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
    @staticmethod
    def is_live_galaxy() -> bool:
        return True

for name, val in MockEDLogs.__dict__.items():
    if not name.startswith('__'):
        setattr(_monitor, name, val)

_monitor.monitor = MockEDLogs # type: ignore
sys.modules['monitor'] = _monitor

_plug = _types.ModuleType('Plugin')
class MockPlugin:
    def __init__(self) -> None:
        pass
    @staticmethod
    def show_error(message:str) -> None:
        print(f"Plugin error: {message}")

for name, val in MockPlugin.__dict__.items():
    if not name.startswith('__'):
        setattr(_plug, name, val)

sys.modules['plug'] = _plug

_l10n = _types.ModuleType('l10n')
_l10n.FALLBACK = 'en' # type: ignore
_l10n.LOCALISATION_DIR = 'L10n' # type: ignore
_translations = _types.ModuleType('Translations')
class MockTranslations:
    FALLBACK = 'en'

    def __init__(self) -> None:
        pass
    def translate(self, x = "", context = None, lang = None) -> str:
        return x
    def tl(self, x: str = "", context: str | None = None, lang: str | None = None) -> str:
        return x
    @staticmethod
    def available() -> set[str]:
        return set('en')
    @staticmethod
    def get_system_lang() -> str:
        return 'en'

for name, val in MockTranslations.__dict__.items():
    if not name.startswith('__'):
        setattr(_translations, name, val)
translation_attributes = {'FALLBACK': 'en'}
for name, val in translation_attributes.items():
    setattr(_translations, name, val)

_l10n.Translations = _translations # type: ignore
_l10n.translations = MockTranslations() # type: ignore

_locale = _types.ModuleType('_Locale')
class MockLocale:
    def __init__(self) -> None:
        pass
    @staticmethod
    def preferred_languages() -> list[str]:
        return ['en']
for name, val in MockLocale.__dict__.items():
    if not name.startswith('__'):
        setattr(_locale, name, val)
_l10n.Locale = _locale # type: ignore
_l10n._Locale = _l10n # type: ignore

sys.modules['l10n'] = _l10n
class MockEDMCOverlay:
    def __init__(self): pass

class Mockedmcoverlay:
    def __init__(self): pass
    class Overlay():
        def __init__(self):
            self.messages:dict = {}
            self.shapes:dict = {}

        def send_message(self, *args, **kw):
            msgid = args[0] if args else kw.get('msgid')
            if not msgid:
                print("send_message called with no msgid")
                return
            self.messages[msgid] = [*args, kw]

        def send_shape(self, *args, **kw):
            if not args:
                print("send_shape called with no positional arguments")
                return
            self.shapes[args[0]] = [*args, kw]

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

# Mock watchdog for file system monitoring
class MockFileSystemEvent:
    def __init__(self, event_type='', src_path=''):
        self.event_type = event_type
        self.src_path = src_path

class MockFileSystemEventHandler:
    def on_created(self, event): pass
    def on_deleted(self, event): pass
    def on_modified(self, event): pass
    def on_moved(self, event): pass

class MockBaseObserver:
    def __init__(self): pass
    def start(self): pass
    def stop(self): pass
    def join(self): pass
    def schedule(self, event_handler, path, recursive=False): pass

class MockObserver:
    def __init__(self): pass
    def start(self): pass
    def stop(self): pass
    def join(self): pass
    def schedule(self, event_handler, path, recursive=False): pass

_watchdog_events = _types.ModuleType('watchdog.events')
_watchdog_events.FileSystemEvent = MockFileSystemEvent  # type: ignore
_watchdog_events.FileSystemEventHandler = MockFileSystemEventHandler  # type: ignore
sys.modules['watchdog.events'] = _watchdog_events

_watchdog_observers_api = _types.ModuleType('watchdog.observers.api')
_watchdog_observers_api.BaseObserver = MockBaseObserver  # type: ignore
sys.modules['watchdog.observers.api'] = _watchdog_observers_api

_watchdog_observers = _types.ModuleType('watchdog.observers')
_watchdog_observers.Observer = MockObserver  # type: ignore
sys.modules['watchdog.observers'] = _watchdog_observers

_watchdog = _types.ModuleType('watchdog')
sys.modules['watchdog'] = _watchdog

from edmc_data import ship_name_map
ship_map = ship_name_map.copy()

# Ship masses
with open(parent / "config" / "ships.json", encoding="utf-8") as ships_file_handle:
    ships = json.load(ships_file_handle)

_edshipyard = _types.ModuleType('edshipyard')
setattr(_edshipyard, 'ship_name_map', ship_map)
setattr(_edshipyard, 'ships', ships)
sys.modules['edshipyard'] = _edshipyard

# Monkey‑patch LogRecord.__init__ to always add 'osthreadid'
_orig_init = logging.LogRecord.__init__

def _patched_init(self, name, level, fn, lno, msg, args, exc_info, func=None, sinfo=None):
    _orig_init(self, name, level, fn, lno, msg, args, exc_info, func, sinfo)
    # Set a harmless default value
    self.osthreadid = -1
    self.qualname = 'TestHarness'

logging.LogRecord.__init__ = _patched_init # type: ignore
