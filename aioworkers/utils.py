import contextlib
import functools
import importlib.util
import logging
import pickle
import struct
import sys
import time
from pathlib import Path
from typing import Mapping

try:
    from setproctitle import setproctitle
except ImportError:
    setproctitle = lambda title: None  # noqa

SIZE = struct.Struct('!I')
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

    logger.debug('Imported "%s" as %r', stref, m)
    return m


def import_uri(obj):
    """
    >>> import_uri(import_uri)
    'aioworkers.utils.import_uri'
    >>> import_uri(Path)
    'pathlib.Path'
    >>> import_uri(Path.exists)
    'pathlib.Path.exists'
    """
    return '.'.join((obj.__module__, obj.__qualname__))


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


def try_read(n, fd, timeout=1):
    result = None
    while n:
        b = fd.read(n)
        if not b:
            time.sleep(timeout)
        elif len(b) == n:
            return b
        elif not result:
            result = b
        else:
            result += b
            n -= len(b)
    return result


def load_from_fd(fd):
    size = SIZE.unpack(try_read(SIZE.size, fd=fd))[0]
    d = try_read(size, fd=fd)
    return pickle.loads(d)


def dump_to_fd(fd, data):
    buf = pickle.dumps(data)
    fd.write(SIZE.pack(len(buf)))
    fd.write(buf)


def mapping_repr(*maps, indent=0, **kwargs):
    result = []
    maps += (kwargs,)

    for m in maps:
        for k, v in sorted(m.items()):
            result.append('  ' * indent)
            result.append(k)
            result.append(': ')
            if isinstance(v, Mapping):
                result.append('\n')
                result.append(mapping_repr(v, indent=indent + 1))
            else:
                result.append(repr(v))
                result.append('\n')
    return ''.join(result)
