import asyncio
import csv

from ..core.base import AbstractReader


class DictReader(AbstractReader):
    async def init(self):
        self._executor = None  # TODO
        self._lock = asyncio.Lock()
        self._file = open(self.config.file)
        self._reader = csv.DictReader(self._file)
        self.context.on_cleanup.append(self.cleanup)

    async def get(self):
        # will not raise an exception StopIteration TODO ?
        async with self._lock:
            return await self.loop.run_in_executor(
                self._executor,
                next,
                self._reader,
            )

    def cleanup(self):
        self._file.close()
