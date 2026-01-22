import functools
import re
import traceback
import threading
from datetime import datetime
from math import floor
from copy import deepcopy
from os import listdir, path
from os.path import join
from pathlib import Path
from re import Pattern, compile, Match
from typing import Any, Callable, Tuple
from bgstally.constants import DATETIME_FORMAT_JSON, DATETIME_FORMAT_CARRIER

import semantic_version

import bgstally.globals
import l10n
from bgstally.debug import Debug
from config import appversion, config

PAT_HUMAN_READABLE_NUM:Pattern = compile(r"^(\d*\.?\d*)([KkMmBbTt]?)$")
PAT_HUMAN_READABLE_NUM_OR_PERC:Pattern = compile(r"^(\d*\.?\d*)([KkMmBbTt%]?)$")

# Language codes for languages that should be omitted
BLOCK_LANGS: list = []
# Assign the current EDMC version to the variable.
edmc_version: semantic_version.Version = appversion()


def _get_tl_func(edmc_version: semantic_version.Version) -> Tuple[Callable[[str], str], Any, l10n._Locale]:
    """
    Returns the appropriate translation function and translations object based on the EDMC version.

    Starting from EDMC version 5.11.0, the translation API changed: the old method
    `l10n.Translations.translate` was deprecated in favor of the new function
    `l10n.translations.tl`. The legacy method is officially deprecated as of 5.11.0 and
    will be removed or made private (thus inaccessible) in version 6.0.
    This function abstracts this difference, returning both a translation function with the
    same interface and the correct translations object, so the rest of the code can always use
    the same call regardless of the EDMC version.

    Args:
        edmc_version (semantic_version.Version): The already parsed EDMC version.

    Returns:
        tuple: (translation function, translations object)
            - Callable[[str], str]: The translation function to use.
            - Any: The translations object to use (l10n.Translations or l10n.translations).
    """
    if edmc_version < semantic_version.Version('5.11.0'):
        return functools.partial(l10n.Translations.translate, context=__file__), l10n.Translations, l10n.Locale
    else:
        return functools.partial(l10n.translations.tl, context=__file__), l10n.translations, l10n.Locale


# Assign the translation function and the translations object based on the current EDMC version.
_, translations_obj, translations_locale = _get_tl_func(edmc_version)


def __(string: str, lang: str|None) -> str:
    """
    Translate a string using the specified language, compatible with all EDMC versions.

    This function attempts to translate the given string into the specified language.
    If the language is None, empty, or the fallback language, or if translation fails,
    it safely returns the string translated in the plugin's currently active language
    or falls back to the original string.

    Args:
        string (str): The string to translate.
        lang (str): The language code to use for translation.

    Returns:
        str: The translated string, or the original string if translation is not possible.
    """
    # Return the original string if the language is empty, None, or the fallback language.
    if lang == "":
        return _(string)  # LANG: Ignore

    # Return original string and log warning if language is None.
    elif lang is None:
        Debug.logger.warning("Translation requested with None language, returning original string.\n"
                             + f">>> {string} <<<")
        return string

    # Return original string if the requested language is the fallback (e.g., 'en').
    elif lang == translations_obj.FALLBACK:
        return string

    # Attempt to translate the string using the translations object.
    try:
        return translations_obj.translate(string, context=__file__, lang=lang)
    except KeyError as e:
        # If the translation file or language is not found, log the error and return the original string.
        Debug.logger.error(
            f"Translation file missing or language not available for '{string}' in '{lang}': {e}"
        )
        return string


def available_langs() -> dict[str | None, str]:
    """Return a dict containing our available plugin language names by code.

    Returns:
        dict[str | None, str]: The available language names indexed by language code
    """
    l10n_path:str | Path

    if edmc_version < semantic_version.Version('5.12.0'):
        l10n_path = join(bgstally.globals.this.plugin_dir, l10n.LOCALISATION_DIR)
    else:
        l10n_path = Path(join(bgstally.globals.this.plugin_dir, l10n.LOCALISATION_DIR))

    available: set[str] = {x[:-len('.strings')] for x in listdir(l10n_path)
                           if x.endswith('.strings')
                           and "template" not in x
                           and x[:-len('.strings')] not in BLOCK_LANGS}

    names: dict[str | None, str] = {
        # LANG: The system default language choice in Settings > Appearance
        None: _('Default'),  # Appearance theme and language setting
    }
    names.update(sorted(
        [(lang, translations_obj.contents(lang, l10n_path).get(l10n.LANGUAGE_ID, lang)) for lang in available]
        + [(translations_obj.FALLBACK, translations_obj.FALLBACK_NAME)],
        key=lambda x: x[1]
    ))

    return names


def get_localised_filepath(filename: str, basepath: str) -> str | None:
    """Attempt to load a localised file from a given base path and filename, looking in the standard EDMC l10n subfolder,
    falling back to the default language if necessary.

    Args:
        filename (str): The name of the file to load
        basepath (str): The base path where the file is located
        encoding (str, optional): The encoding to use when opening the file. Defaults to "utf-8".

    Returns:
        str | None: The file path if it exists or None if the file is not found.
    """
    lang: str | None = config.get_str('language')
    if lang is None or lang == '': # This is the case when EDMC is set to the default (system) language
        lang = get_system_lang()

    filepath: str | None = None

    if lang and lang != 'en':
        filepath = path.join(basepath, l10n.LOCALISATION_DIR, f"{lang}.{filename}")
        if path.exists(filepath):
            return filepath
        else:
            Debug.logger.debug(f"Missing translatable file {filepath} for language: {lang}, falling back to default.")

    filepath = path.join(basepath, filename)
    if path.exists(filepath):
        return filepath

    Debug.logger.info(f"Missing translatable file {filepath} for language: {lang}")
    return None


def get_system_lang() -> str | None:
    """
    Attempt to retrieve the system language preference and select the first preferred language if available.
    Return the selected language or None if no language is selected.

    EDMC doesn't store the default (system) language so we use exactly the same logic here as l10n.install() to ensure
    the same language is chosen
    """
    lang: str | None = None
    available: set[str] = translations_obj.available()
    available.add(translations_obj.FALLBACK)

    for preferred in translations_locale.preferred_languages():
        components = preferred.split('-')
        if preferred in available:
            lang = preferred

        elif '-'.join(components[0:2]) in available:
            lang = '-'.join(components[0:2])

        elif components[0] in available:
            lang = components[0]  # just base language

        if lang:
            break

    return lang


def get_by_path(dic: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    """Access a multi-level nested dict by a sequence of keys.

    Args:
        dic (dict[str, any]): The dict to access
        keys (list[str]): A list of keys to access in sequence
        default (any, optional): The default value to be returned if the key cannot be found at any level. Defaults to None.

    Returns:
        any: The value of the nested key
    """
    try:
        for key in keys:
            if dic.get(key, None) == None: return default
            dic = dic[key]
    except KeyError:
        return default

    return dic


def human_format(num:int) -> str:
    """Format a number into a shortened human-readable string, using abbreviations for larger values, e.g. 1300 -> 1.3K.

    Args:
        num (int): The value to convert

    Returns:
        str: The human-readable result
    """
    abbrs:list[str] = ['', 'K', 'M', 'B', 'T']  # Abbreviations for thousands, millions, billions, trillions
    fnum:float = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(fnum) >= 1000:
        if magnitude >= len(abbrs) - 1: break
        magnitude += 1
        fnum /= 1000.0

    return '{}{}'.format('{:f}'.format(fnum).rstrip('0').rstrip('.'), abbrs[magnitude])


def parse_human_format(text:str, include_percent:bool = False) -> int:
    """Convert shortened human-readable text into a number

    Args:
        text (str): The human-readable text to convert
        include_percent (bool, optional): Allow % in the string. Defaults to False.

    Returns:
        int: The numeric result
    """
    if not isinstance(text, str) or text.replace(' ', '') == '': return 0
    text = re.sub(r'[, ]', '', text) # Remove commas or spaces if we're showing them.
    match:Match[str]|None = PAT_HUMAN_READABLE_NUM_OR_PERC.match(text) if include_percent else PAT_HUMAN_READABLE_NUM.match(text)

    if match:
        num:float = float(match.group(1))
        multiplier:int = {'%': 0.01, '': 1, 'k': 1000, 'm': 1000000, 'b': 1000000000, 't': 1000000000000}[match.group(2).lower()]
        return int(num * multiplier)
    else:
        return int(text)


def hfplus(val:int|float|str|bool|tuple, type:str|None = None) -> str:
    """
        A general customized formatting function.
        It's a lot like human_format() and even uses human_format() but has more options for different types of data.


    Args:
        val (int|float|str|bool|tuple): A tuple or a value

    Returns:
        str: The human-readable result
    """
    units:str = ''
    default:str = ''

    if isinstance(val, tuple): # Handle a tuple of 1-4 elements: (value, type, default, units)
        if len(val) > 1: type = val[1]
        if len(val) > 2: default = val[2]
        if len(val) > 3: units = val[3]
        if len(val) > 0: value = val[0]
    else:
        value = val
        if (isinstance(value, str) and re.match(value, r"^\d+-\d+-\d+ \d+\:\d+")): type = 'datetime'
        if isinstance(value, bool): type = 'bool'
        if isinstance(value, int) or isinstance(value, float): type = 'num'

    # Fixed is left entirely alone
    if type == 'fixed': return str(value)

    # Empty, zero or false we return the default so the display isn't full of "No" and "0" etc.
    if value == None or value == 0 or value == '' or value == False: return default

    ret:str = ""
    match type:
        case 'bool': # We're going to display Yes (blanks and False are handled above)
            ret = _("Yes") # LANG: Yes

        case 'datetime': # If it's a datetime convert it from the json date format to our date format
            ret = datetime.strptime(str(value), DATETIME_FORMAT_JSON).strftime(DATETIME_FORMAT_CARRIER)

        case 'interval': # Approximated interval (no seconds, only show minutes if it's less than a day)
            days , rem = divmod(int(value), 60*60*24)
            hours, rem = divmod(rem, 60*60)
            mins, rem = divmod(rem, 60)
            tmp:list = []
            if floor(days) > 1: tmp.append(f"{floor(days)} days")
            elif int(days) > 0: tmp.append(f"1 day")
            if floor(hours) > 1: tmp.append(f"{floor(hours)} hours")
            elif int(hours) > 0: tmp.append(f" 1 hour")
            if len(tmp) < 2:
                if floor(mins) > 1: tmp.append(f" {int(mins)} minutes")
                elif mins > 0: tmp.append(f" 1 minute")
            ret = ' '.join(tmp)

        case 'num': # We only shorten/simplify numbers over 100k. Smaller ones we just display with commas at thousands
            ret = human_format(int(value)) if int(value) > 100000 else f"{value:,}"

        case _: # Title case two words, leave longer strings as is
            ret = str(value).title() if str(value).count(' ') < 2 and re.search(r"[A-Z0-9]", str(value)) == None else str(value)

    return ret + units


def is_number(s: str) -> bool:
    """
    Return True if the string represents a number
    """
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def all_subclasses(cls: type) -> set[type]:
    """Find all subclasses of a given Python class

    Args:
        cls (type): The class to search for subclasses

    Returns:
        set[type]: A set of Python subclasses
    """
    return set(cls.__subclasses__()).union([s for c in cls.__subclasses__() for s in all_subclasses(c)])


def string_to_alphanumeric(s: str) -> str:
    """Clean a string so it only contains alphanumeric characters

    Args:
        s (str): The string to clean

    Returns:
        str: The cleaned string
    """
    pattern: re.Pattern = re.compile(r'[\W_]+')
    return pattern.sub('', s)


def add_dicts(d1: dict, d2: dict) -> dict:
    """Sum each individual numeric value from two dicts. For non-numeric values,
    The result is the value from dict d1. Neither d1 nor d2 are modified by this function.

    Args:
        d1 (dict): The first dict
        d2 (dict): The second dict

    Returns:
        dict: The summed dict
    """

    # Copy on first entry to the function
    result: dict = deepcopy(d1)

    def _recursive_add(d1: dict, d2: dict) -> dict:
        for d2k, d2v in d2.items():
            d1v = d1.get(d2k)
            if isinstance(d1v, dict):
                # We have a dict in d1
                if isinstance(d2v, dict):
                    # We have a dict in d2. Recursively merge nested dictionaries (otherwise, just use d1 dict).
                    d1[d2k] = _recursive_add(d1v, d2v)
            elif isinstance(d2v, dict):
                # We have a dict in d2, but not in d1. Copy the d2 dict into d1.
                d1[d2k] = deepcopy(d2v)
            elif d1v is None:
                # No matching key in d1. Copy the d2 value into d1.
                d1[d2k] = deepcopy(d2v)
            elif is_number(d1v) and is_number(d2v):
                # Add numeric values
                d1[d2k] = d1v + d2v

            # For non-numeric values, do nothing so d1 wins

        return d1

    return _recursive_add(result, d2)

def str_truncate(s:str, length:int = 20, elipsis:str = '…', loc:str = 'right') -> str:
    """ Truncate a string to a specified length, adding an ellipsis if the string is longer than the specified length. """
    if len(s) <= length:
        return s

    match loc:
        case 'left':
            return elipsis + s[-(length - len(elipsis)):]
        case 'middle':
            half_length = (length - len(elipsis)) // 2
            return s[:half_length] + elipsis + s[-half_length:]
        case _:
            # Default to truncating at the right side
            return s[:length - len(elipsis)] + elipsis


def catch_exceptions(func):
    """ Generic exception handler called via decorators """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            Debug.logger.info(f"An error occurred in {func.__name__}: {e}")
            trace:list = traceback.format_exc().splitlines()
            #Debug.logger.error("\n".join(trace[4:]))
            Debug.logger.error(trace[0] + "\n" + "\n".join(trace[4:]))
    return wrapper


class DelayQueue:
    """
    Manages a queue of delayed updates to Fleet Carrier data,
    to avoid excessive API calls when multiple events occur in quick succession.

    Usage:
        def notify(message:str) -> None:
            print(f"Notified: {message}")
    DelayQueue('notify', 60, self._notify, ['message'])
    DelayQueue.cancel('notify')
    """
    _instance = None

    # Singleton pattern
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, key:str, delay:float, function:callable, *args, **kwargs) -> None:
        """
        Adds a delayed function call to a queue.
        If a function with the same key already exists, it is cancelled and replaced.
        """

        # Only initialize if it's the first time
        if not hasattr(self, '_initialized'):
            self.queue:dict[str,threading.Timer] = {}
            self._initialized = True

        # Add an item to the queue
        if key in self.queue:
            self.queue[key].cancel()
        timer = threading.Timer(delay, function, args=args, kwargs=kwargs)
        self.queue[key] = timer
        timer.start()


    def cancel(self, key:str) -> None:
        """ Cancels a delayed function call in the queue. """
        if key in self.queue:
            self.queue[key].cancel()
            del self.queue[key]
