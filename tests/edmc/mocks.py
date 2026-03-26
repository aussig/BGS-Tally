import os
import sys
import types as _types
import semantic_version
import logging
from pathlib import Path
from unittest.mock import patch
from tests.edmc import requests as edmc_requests

# We keep a copy of edmc_data here.
this_dir:Path = Path(__file__).parent
parent:Path = Path(__file__).parent.parent


# Force it to look like Linux
#with patch.object(sys, 'platform', 'linux'):
#    with patch.dict(os.environ, {'XDG_DATA_HOME': str(this_dir)}, clear=False):
#        import config

#def _mock_app_dir() -> Path:
#    return this_dir

#config.get_appdirpath = _mock_app_dir # type: ignore

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
            self.app_dir_path = parent
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
    def __init__(self) -> None:
        FALLBACK = 'en'
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
            self.messages[args[0]] = [*args, kw]

        def send_shape(self, *args, **kw):             
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

# Monkey‑patch LogRecord.__init__ to always add 'osthreadid'
_orig_init = logging.LogRecord.__init__

def _patched_init(self, name, level, fn, lno, msg, args, exc_info, func=None, sinfo=None):
    _orig_init(self, name, level, fn, lno, msg, args, exc_info, func, sinfo)
    # Set a harmless default value
    self.osthreadid = -1
    self.qualname = 'TestHarness'
    
logging.LogRecord.__init__ = _patched_init # type: ignore
