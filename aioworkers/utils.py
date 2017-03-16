import functools
import importlib
import logging

logger = logging.getLogger(__name__)


def import_name(stref: str):
    package, name = stref.rsplit('.', maxsplit=1)
    module = importlib.import_module(package)
    cls = getattr(module, name)
    logger.debug('Imported "{}" as {}'.format(stref, cls))
    return cls


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
