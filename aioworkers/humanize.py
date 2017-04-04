from math import log2


def size(value, suffixes=None):
    """
    >>> size(1024)
    '1 KB'

    :param size: 
    :param suffixes: 
    :return: 
    """
    suffixes = suffixes or [
        'bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    order = int(log2(value) / 10) if value else 0
    return '{:.4g} {}'.format(value / (1 << (order * 10)), suffixes[order])
