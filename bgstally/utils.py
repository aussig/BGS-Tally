import functools
from os import listdir
from os.path import join

import bgstally.globals
import l10n
from bgstally.debug import Debug
from config import config

# Localisation main translation function
_ = functools.partial(l10n.Translations.translate, context=__file__)

# Localisation conditional translation function for when PR [2188] is merged in to EDMC
# __ = functools.partial(l10n.Translations.translate, context=__file__, lang=bgstally.globals.this.state.discord_lang)

# Localisation conditional translation function before PR [2188] is merged in to EDMC
def __(string:str):
    """Translate using our overridden language

    Args:
        string (str): The string to translate
        lang (str): The override language

    Returns:
        _type_: Translated string
    """
    plugin_path:str = join(config.plugin_dir_path, "BGS-Tally", l10n.LOCALISATION_DIR)
    lang:str = bgstally.globals.this.state.discord_lang
    if lang == "" or lang is None: return _(string)

    contents:dict[str, str] = l10n.Translations.contents(lang=lang, plugin_path=plugin_path)

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

    plugin_path:str = join(config.plugin_dir_path, "BGS-Tally", l10n.LOCALISATION_DIR)
    available:set[str] = {x[:-len('.strings')] for x in listdir(plugin_path) if x.endswith('.strings') and "template" not in x}

    names: dict[str | None, str] = {
        # LANG: The system default language choice in Settings > Appearance
        None: _('Default'),  # Appearance theme and language setting
    }
    names.update(sorted(
        [(lang, l10n.Translations.contents(lang, plugin_path).get(l10n.LANGUAGE_ID, lang)) for lang in available] +
        [(l10n._Translations.FALLBACK, l10n._Translations.FALLBACK_NAME)],
        key=lambda x: x[1]
    ))

    return names


def get_by_path(dic:dict, keys:list, default:any = None):
    """
    Access a nested dict by key sequence
    """
    try:
        for key in keys:
            dic = dic[key]
    except KeyError:
        return default

    return dic


def human_format(num):
    """
    Format a BGS value into shortened human-readable text
    """
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])


def is_number(s:str):
    """
    Return True if the string represents a number
    """
    try:
        float(s)
        return True
    except ValueError:
        return False
