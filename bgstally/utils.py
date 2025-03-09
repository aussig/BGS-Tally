import functools
import re
from copy import deepcopy
from os import listdir
from os.path import join
from pathlib import Path

import semantic_version

import bgstally.globals
import l10n
from bgstally.debug import Debug
from config import appversion

# Language codes for languages that should be omitted
BLOCK_LANGS: list = []

# Localisation main translation function
_ = functools.partial(l10n.Translations.translate, context=__file__)

# Localisation conditional translation function for when PR [2188] is merged in to EDMC
# __ = functools.partial(l10n.Translations.translate, context=__file__, lang=lang)

# Localisation conditional translation function before PR [2188] is merged in to EDMC
def __(string: str, lang: str) -> str:
    """Translate using our overridden language

    Args:
        string (str): The string to translate
        lang (str): The override language

    Returns:
        str: Translated string
    """
    if lang == "" or lang is None: return _(string)

    if appversion() < semantic_version.Version('5.12.0'):
        l10n_path: str = join(bgstally.globals.this.plugin_dir, l10n.LOCALISATION_DIR)
    else:
        l10n_path: Path = Path(join(bgstally.globals.this.plugin_dir, l10n.LOCALISATION_DIR))

    contents: dict[str, str] = l10n.Translations.contents(lang=lang, plugin_path=l10n_path)

    if not contents:
        Debug.logger.debug(f'Failure loading translations for language {lang!r}')
        return string
    elif string in contents.keys():
        return contents[string]
    else:
        Debug.logger.debug(f'Missing translation: {string!r} in language {lang!r}')
        return string


def available_langs() -> dict[str | None, str]:
    """Return a dict containing our available plugin language names by code.

    Returns:
        dict[str | None, str]: The available language names indexed by language code
    """
    if appversion() < semantic_version.Version('5.12.0'):
        l10n_path: str = join(bgstally.globals.this.plugin_dir, l10n.LOCALISATION_DIR)
    else:
        l10n_path: Path = Path(join(bgstally.globals.this.plugin_dir, l10n.LOCALISATION_DIR))

    available: set[str] = {x[:-len('.strings')] for x in listdir(l10n_path)
                          if x.endswith('.strings') and
                          "template" not in x and
                          x[:-len('.strings')] not in BLOCK_LANGS}

    names: dict[str | None, str] = {
        # LANG: The system default language choice in Settings > Appearance
        None: _('Default'),  # Appearance theme and language setting
    }
    names.update(sorted(
        [(lang, l10n.Translations.contents(lang, l10n_path).get(l10n.LANGUAGE_ID, lang)) for lang in available] +
        [(l10n._Translations.FALLBACK, l10n._Translations.FALLBACK_NAME)],
        key=lambda x: x[1]
    ))

    return names


def get_by_path(dic: dict[str, any], keys: list[str], default: any = None) -> any:
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
            dic = dic[key]
    except KeyError:
        return default

    return dic


def human_format(num: int) -> str:
    """Format a number into a shortened human-readable string, using abbreviations for larger values, e.g. 1300 -> 1.3K.

    Args:
        num (int): The value to convert

    Returns:
        str: The human-readable result
    """
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])


def is_number(s: str) -> bool:
    """Return True if the string represents a number.

    Args:
        s (str): The string to check

    Returns:
        bool: True if the string contains a numeric value, False otherwise.
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
