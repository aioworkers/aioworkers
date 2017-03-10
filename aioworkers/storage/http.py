import asyncio
import json
import logging
from collections import Mapping, Sequence

from aiohttp import client, errors
from yarl import URL

from . import base, StorageError


class RoStorage(base.AbstractStorageReadOnly):
    """ ReadOnly storage over http GET
    config:
        semaphore: int
        allow_hosts: list
        return_status: bool, method get returns tuple (CODE, VALUE)
        prefix: url prefix
        headers: Mapping or None
        template: url template
        format: [json|str|bytes], default json
    """
    async def init(self):
        self._prefix = self.config.get('prefix')
        self._template = self.config.get('template')
        if self._prefix:
            self._prefix = URL(self._prefix)
        self._semaphore = asyncio.Semaphore(
            self.config.get('semaphore', 20), loop=self.loop)
        self._allow_hosts = self.config.get('allow_hosts')
        self._format = self.config.get('format', 'json')
        self._return_status = self.config.get('return_status', False)
        self.session = client.ClientSession(
            headers=self.config.get('headers'), loop=self.loop)
        self.context.on_stop.append(self.stop)

    async def stop(self):
        self.session.close()

    def raw_key(self, key):
        if self._prefix:
            url = self._prefix / key
        elif self._template and isinstance(key, Mapping):
            url = URL(self._template.format_map(key))
        elif self._template and isinstance(key, Sequence):
            url = URL(self._template.format(*key))
        elif self._template:
            url = URL(self._template.format(key))
        elif isinstance(key, str):
            url = URL(key)
        else:
            url = key
        if self._allow_hosts and url.host not in self._allow_hosts:
            raise KeyError(key)
        return url

    async def _request(self, url, *, method='get', **kwargs):
        async with self._semaphore:
            coro = getattr(self.session, method)
            async with coro(url, **kwargs) as response:
                if self._format == 'json':
                    return response.status, await response.json()
                elif self._format == 'str':
                    return response.status, await response.text()
                else:
                    return response.status, await response.read()

    async def request(self, url, **kwargs):
        try:
            status, data = await self._request(url, **kwargs)
        except errors.ClientOSError as e:
            raise StorageError('URL %s: %s' % (url, e)) from e

        if status == 404:
            data = None
        elif status >= 400:
            raise StorageError('URL %s: %s' % (url, status))

        if self._return_status:
            return status, data
        return data

    def get(self, key):
        url = self.raw_key(key)
        return self.request(url)

    async def copy(self, key_source, storage_dest, key_dest):
        """ Return True if data are copied
        * optimized for http->fs copy
        * not supported return_status
        """
        from aioworkers.storage.filesystem import FileSystemStorage
        if not isinstance(storage_dest, FileSystemStorage):
            return super().copy(key_source, storage_dest, key_dest)
        url = self.raw_key(key_source)
        logger = self.context.logger
        async with self._semaphore:
            async with self.session.get(url) as response:
                if response.status == 404:
                    return
                elif response.status >= 400:
                    if logger.getEffectiveLevel() == logging.DEBUG:
                        logger.debug(
                            'HttpStorage request to %s '
                            'returned code %s:\n%s' % (
                                url, response.status,
                                (await response.read()).decode()))
                    return
                f = await storage_dest._open(key_dest, 'wb')
                try:
                    async for chunk in response.content.iter_any():
                        await storage_dest._write_chunk(f, chunk)
                    return True
                finally:
                    await storage_dest._close(f)


class Storage(RoStorage, base.AbstractStorageWriteOnly):
    """ RW storage over http
    config:
        semaphore: int
        allow_hosts: list
        return_status: bool, method get returns tuple (CODE, VALUE)
        prefix: url prefix
        template: url template
        headers: Mapping or None
        format: [json|str|bytes], default json
        set: [post|put|patch], default post
        dumps: str, path in context to dumps
    """

    def set(self, key, value):
        url = self.raw_key(key)
        if self._format == 'json':
            if self.config.get('dumps'):
                dumps = self.context[self.config.dumps]
            else:
                dumps = json.dumps
            data = dumps(value)
            headers = {'content-type': 'application/json'}
        else:
            data = value
            headers = {}

        return self.request(
            url, method=self.config.get('set', 'post'),
            data=data, headers=headers)
