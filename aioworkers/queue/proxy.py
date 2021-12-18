import asyncio
import sys

from ..core.base import ExecutorEntity
from ..core.formatter import FormattedEntity
from .base import AbstractQueue


class ProxyQueue(ExecutorEntity, AbstractQueue):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = None

    async def init(self):
        lock = asyncio.Lock(loop=self._loop)
        await lock.acquire()
        self._lock = lock

    def set_queue(self, queue):
        self._queue = queue
        self._lock.release()

    async def get(self):
        async with self._lock:
            return await self.run_in_executor(self._queue.get)

    async def put(self, value):
        async with self._lock:
            return await self.run_in_executor(self._queue.put, value)


class PipeLineQueue(FormattedEntity, ExecutorEntity, AbstractQueue):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._read_lock = asyncio.Lock(loop=self._loop)
        self._write_lock = asyncio.Lock(loop=self._loop)
        self.set_reader(sys.stdin.buffer)
        self.set_writer(sys.stdout.buffer)
        self._timeout = self.config.get('timeout')

    def set_reader(self, reader):
        self._reader = reader

    def set_writer(self, writer):
        self._writer = writer

    async def get(self):
        async with self._read_lock:
            while True:
                v = await self.run_in_executor(self._reader.readline)
                if v:
                    break
                elif not self._timeout:
                    return
                await asyncio.sleep(self._timeout)
        return self.decode(v)

    async def put(self, value):
        value = self.encode(value)
        async with self._write_lock:
            return await self.run_in_executor(self._writer.write, value)
