import l10n
import functools

# Localisation main translation function
_ = functools.partial(l10n.Translations.translate, context=__file__)

# Localisation conditional translation function
def __(string:str, translate:bool = True): return _(string) if translate else string


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
