import functools
from os.path import join

import l10n
from bgstally.debug import Debug
from config import config

# Localisation main translation function
_ = functools.partial(l10n.Translations.translate, context=__file__)

# Localisation conditional translation function
def __(string:str):
    lang:str = "de"
    # context = __file__[len(config.plugin_dir)+1:].split(sep)[0]
    # plugin_path = join(config.plugin_dir_path, context, l10n.LOCALISATION_DIR)
    # plugin_path = join(__file__, l10n.LOCALISATION_DIR)
    plugin_path = join(config.plugin_dir_path, "BGS-Tally", l10n.LOCALISATION_DIR)
    contents:dict[str, str] = l10n.Translations.contents(lang=lang, plugin_path=plugin_path)
    # Debug.logger.info(f'context: {context}')
    # Debug.logger.info(f'plugin_path: {plugin_path}')
    # Debug.logger.info(f'Contents: {contents}')
    # For EDMC contribution, use try: catch: here something like
    # try:
    #     lang_contents:dict[str, str] = l10n.Translations.contents(lang='de', plugin_path = __file__)

    # except UnicodeDecodeError as e:
    #     logger.warning(f'Malformed file {lang}.strings in plugin {plugin}: {e}')

    # except Exception:
    #     logger.exception(f'Exception occurred while parsing {lang}.strings in plugin {plugin}')

    if not contents:
        Debug.logger.debug(f'Failure loading translations for language {lang!r}')
        return string
    elif string in contents.keys():
        return contents[string]
    else:
        Debug.logger.debug(f'Missing translation: {string!r} in language {lang!r}')
        return string


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
