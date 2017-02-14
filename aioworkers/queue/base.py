import asyncio

from aioworkers.core.base import AbstractEntity


class AbstractReader(AbstractEntity):
    async def get(self):
        raise NotImplementedError()


class AbstractWriter(AbstractEntity):
    async def put(self, value):
        raise NotImplementedError()


class AbstractQueue(AbstractReader, AbstractWriter):
    pass


class Queue(asyncio.Queue, AbstractQueue):
    def __init__(self, config, *, context=None, loop=None):
        maxsize = config.get('maxsize', 0)
        AbstractQueue.__init__(self, config, context=context, loop=loop)
        asyncio.Queue.__init__(self, maxsize=maxsize, loop=loop)


class PriorityQueue(asyncio.PriorityQueue, AbstractQueue):
    def __init__(self, config, *, context=None, loop=None):
        maxsize = config.get('maxsize', 0)
        AbstractQueue.__init__(self, config, context=context, loop=loop)
        asyncio.Queue.__init__(self, maxsize=maxsize, loop=loop)
