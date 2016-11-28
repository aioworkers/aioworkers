import asyncio

from aiohttp import client
from yarl import URL

from . import base


class Storage(base.AbstractStorageReadOnly):
    """
    config:
        semaphore: int
        allow_hosts: list
        prefix: url prefix
        format: [json|str|bytes]
    """
    async def init(self):
        self._prefix = self.config.get('prefix')
        if self._prefix:
            self._prefix = URL(self._prefix)
        self._semaphore = asyncio.Semaphore(
            self.config.semaphore, loop=self.loop)
        self._allow_hosts = self.config.get('allow_hosts')
        self._format = self.config.get('format', 'json')

    async def get(self, key):
        if self._prefix:
            url = self._prefix / key
        elif isinstance(key, str):
            url = URL(key)
        else:
            url = key
        if self._allow_hosts and url.host not in self._allow_hosts:
            raise KeyError(key)
        async with self._semaphore:
            with client.ClientSession(loop=self.loop) as session:
                async with session.get(url) as response:
                    if self._format in ('str', 'bytes'):
                        data = await response.read()
                    else:
                        return await response.json()
        if self._format == 'str':
            return data.decode()
        return data
