import contextlib
import functools
import importlib.util
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


@functools.lru_cache(None)
def import_name(stref: str):
    """
    >>> import_name('datetime.datetime.utcnow') is not None
    True
    >>> import_name('aioworkers.utils.import_name') is not None
    True
    """
    h = stref
    p = []
    m = None
    try:
        r = importlib.util.find_spec(stref)
    except (AttributeError, ImportError):
        r = None

    if r is not None:
        return importlib.import_module(stref)

    while '.' in h:
        h, t = h.rsplit('.', 1)
        p.append(t)
        if h in sys.modules:
            m = sys.modules[h]
            break

    if m is None:
        m = importlib.import_module(h)

    for i in reversed(p):
        if hasattr(m, i):
            m = getattr(m, i)
        else:
            h += '.' + i
            m = importlib.import_module(h)

    logger.debug('Imported "{}" as {}'.format(stref, h))
    return m


def module_path(str_module, return_str=False):
    if str_module in sys.modules:
        m = sys.modules[str_module]
    else:
        m = import_name(str_module)
    p = Path(m.__file__).parent
    if return_str:
        return str(p)
    return p


def method_replicate_result(key):
    futures = {}

    def wrapped(coro):
        @functools.wraps(coro)
        async def wrapper(self, *args, **kwargs):
            k = key(self, *args, **kwargs)
            if k in futures:
                return await futures[k]
            c = coro(self, *args, **kwargs)
            fut = self.loop.create_task(c)
            futures[k] = fut
            result = await fut
            del futures[k]
            return result
        return wrapper
    return wrapped


@contextlib.contextmanager
def monkey_close(loop):
    close = loop.close
    closed = False

    def patched_close():
        nonlocal closed
        closed = True

    loop.close = patched_close
    yield
    if closed:
        close()
