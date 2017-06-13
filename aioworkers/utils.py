import contextlib
import functools
import importlib
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def import_name(stref: str):
    package, name = stref.rsplit('.', maxsplit=1)
    module = importlib.import_module(package)
    cls = getattr(module, name)
    logger.debug('Imported "{}" as {}'.format(stref, cls))
    return cls


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
