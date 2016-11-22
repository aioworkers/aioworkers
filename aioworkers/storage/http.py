import asyncio

from aiohttp import client

from . import base


class HostStorage(base.AbstractStorage):
    async def init(self):
        self._semaphore = asyncio.Semaphore(
            self._config.semaphore, loop=self.loop)

    async def get(self, key):
        async with self._semaphore:
            with client.ClientSession(loop=self.loop) as session:
                async with session.get(key) as response:
                    return await response.read()

    async def set(self, key, value):
        pass
