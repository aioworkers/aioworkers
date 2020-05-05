import re
from math import log2
from typing import Union


def size(value: int, suffixes: list = None) -> str:
    """
    >>> size(1024)
    '1 KB'
    """
    suffixes = suffixes or [
        'bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    order = int(log2(value) / 10) if value else 0
    return '{:.4g} {}'.format(value / (1 << (order * 10)), suffixes[order])


pattern_valid = re.compile(r'\d+[a-z\s\d]*', re.I | re.A)
pattern = re.compile(r'(?P<n>\d+)(?P<unit>[a-z]*)', re.I)
size_levels = {
    'KB': 10,
    'MB': 20,
    'GB': 30,
    'TB': 40,
    'PB': 50,
}
for k, v in size_levels.copy().items():
    size_levels[k[0]] = v


def parse_size(value: Union[int, float, str]) -> Union[int, float]:
    """
    >>> parse_size('1M')
    1048576
    >>> parse_size('512K512K')
    1048576
    >>> parse_size('512K 512K')
    1048576
    >>> parse_size('512K 512K 4')
    1048580
    """
    if isinstance(value, (int, float)):
        return value
    elif not pattern_valid.fullmatch(value):
        raise ValueError(value)

    result = 0
    for m in pattern.finditer(value):
        v = m.groupdict()
        n = int(v['n'])
        unit = v['unit']
        if not unit:
            result += n
        elif unit in size_levels:
            result += n << size_levels[unit]
        else:
            raise ValueError(value)
    return result


durations = {
    'w': 7 * 24 * 60 * 60,
    'd': 24 * 60 * 60,
    'h': 60 * 60,
    'm': 60,
    's': 1,
}


def parse_duration(value: Union[int, float, str]) -> Union[int, float]:
    """
    >>> parse_duration('1h')
    3600
    >>> parse_duration('1m')
    60
    >>> parse_duration('1m 2s')
    62
    >>> parse_duration('1')
    1

    """
    if isinstance(value, (int, float)):
        return value
    elif not pattern_valid.fullmatch(value):
        raise ValueError(value)

    result = 0
    for m in pattern.finditer(value):
        v = m.groupdict()
        n = int(v['n'])
        unit = v['unit']
        if not unit:
            result += n
        elif unit in durations:
            result += n * durations[unit]
        else:
            raise ValueError(value)
    return result
