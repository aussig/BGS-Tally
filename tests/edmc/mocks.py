import os
import sys
import types as _types
import semantic_version
import logging
from pathlib import Path

# We keep a copy of edmc_data here.
this_dir:Path = Path(__file__).parent

if 'config' not in sys.modules:
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
            self.app_dir_path = this_dir
            self._initialized = True

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
    @staticmethod
    def is_live_galaxy() -> bool:
        return True

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

# Monkey‑patch LogRecord.__init__ to always add 'osthreadid'
_orig_init = logging.LogRecord.__init__

def _patched_init(self, name, level, fn, lno, msg, args, exc_info, func=None, sinfo=None):
    _orig_init(self, name, level, fn, lno, msg, args, exc_info, func, sinfo)
    # Set a harmless default value
    self.osthreadid = -1
    self.qualname = 'TestHarness'
    
logging.LogRecord.__init__ = _patched_init
