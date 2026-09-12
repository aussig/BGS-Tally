"""
Minimal mock of EDMC's outfitting.py for the test harness.

Only lookup() is used by BGS-Tally; this is a best-effort stand-in, not a
faithful reproduction of EDMC's real FDev-symbol parser.
"""

RATING_MAP = {'1': 'E', '2': 'D', '3': 'C', '4': 'B', '5': 'A'}


def lookup(module, ship_map, entitled=False):
    """Derive a display dict from a raw module symbol."""
    if not module.get('name'):
        raise ValueError(f"Module with ID {module.get('id')} is missing a 'name' field")

    parts = module['name'].lower().split('_')
    size = next((p[4:] for p in parts if p.startswith('size')), '')
    rating_num = next((p[5:] for p in parts if p.startswith('class')), '')

    return {
        'id': module.get('id'),
        'symbol': module['name'],
        'category': parts[0] if parts else '',
        'name': module['name'],
        'class': size,
        'rating': RATING_MAP.get(rating_num, ''),
    }
