import functools
import re
from copy import deepcopy
from os import listdir
from os.path import join
from pathlib import Path
from typing import Callable, Any, Tuple

import semantic_version

import bgstally.globals
import l10n
from bgstally.debug import Debug
from config import appversion

# Language codes for languages that should be omitted
BLOCK_LANGS: list = []
# Assign the current EDMC version to the variable.
edmc_version: semantic_version.Version = appversion()


def _get_tl_func(edmc_version: semantic_version.Version) -> Tuple[Callable[[str], str], Any]:
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
        return functools.partial(l10n.Translations.translate, context=__file__), l10n.Translations
    else:
        return functools.partial(l10n.translations.tl, context=__file__), l10n.translations


# Assign the translation function and the translations object based on the current EDMC version.
_, translations_obj = _get_tl_func(edmc_version)


def __(string: str, lang: str) -> str:
    """
    Translate a string using the specified language, compatible with all EDMC versions.

    This wrapper handles the KeyError that occurs if the requested language
    or translation file is missing, ensuring the original string is returned
    as a fallback instead of raising an exception.

    Args:
        string (str): The string to translate.
        lang (str): The language code to use for translation.

    Returns:
        str: The translated string. If the language is empty, None, the fallback language,
             or if translation fails, returns the original string.
    """
    # Return the original string if the language is empty, None, or the fallback language.
    if lang == "":
        Debug.logger.warning("Translation requested with empty language, returning original string.\n"
                             + f">>> {string} <<<")
        return string
    elif lang is None:
        Debug.logger.warning("Translation requested with None language, returning original string.\n"
                             + f">>> {string} <<<")
        return string
    elif lang == translations_obj.FALLBACK:
        # If the requested language is the fallback (usually 'en'), return the original string.
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
    if edmc_version < semantic_version.Version('5.12.0'):
        l10n_path: str = join(bgstally.globals.this.plugin_dir, l10n.LOCALISATION_DIR)
    else:
        l10n_path: Path = Path(join(bgstally.globals.this.plugin_dir, l10n.LOCALISATION_DIR))

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
