from re import Pattern, compile

human_readable_number_pat:Pattern = compile(r"^(\d*\.?\d*)([KkMmBbTt]?)$")


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


def human_format(num:int) -> str:
    """
    Format a BGS value into shortened human-readable text
    """
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])


def parse_human_format(self, text:str) -> int:
    """
    Convert shortened human-readable text into a number
    """
    if not isinstance(text, str): return 0

    match = human_readable_number_pat.match(text)

    if match:
        num = float(match.group(1))
        multiplier = {'': 1, 'k': 1000, 'm': 1000000, 'b': 1000000000, 't': 1000000000000}[match.group(2).lower()]
        return int(num * multiplier)
    else:
        return 0


def validate_human_format(self, text:str) -> bool:
    """
    Validate whether a string value is in standard shortened human-readable (integer) format
    """
    if not isinstance(text, str): return False
    else: return human_readable_number_pat.match(text)


def is_number(s:str):
    """
    Return True if the string represents a number
    """
    try:
        float(s)
        return True
    except ValueError:
        return False
