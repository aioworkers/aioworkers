import asyncio
import csv

from ..core.base import AbstractReader


class DictReader(AbstractReader):
    async def init(self):
        self._reader = csv.DictReader(open(self.config.file))
        self._executor = None  # TODO
        self._lock = asyncio.Lock(loop=self.loop)

    async def get(self):
        # will not raise an exception StopIteration TODO ?
        async with self._lock:
            return await self.loop.run_in_executor(
                self._executor, next, self._reader)
