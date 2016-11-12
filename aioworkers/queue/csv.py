import asyncio
import csv

from .base import AbstractReader


class DictReader(AbstractReader):
    def __init__(self, config, *, context=None, loop=None):
        AbstractReader.__init__(self, config, context=context, loop=loop)
        self._reader = csv.DictReader(open(config.file))
        self._executor = None  # TODO
        self._lock = asyncio.Lock(loop=self.loop)

    async def get(self):
        # will not raise an exception StopIteration TODO ?
        async with self._lock:
            return await self.loop.run_in_executor(
                self._executor, next, self._reader)
