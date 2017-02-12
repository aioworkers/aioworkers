import asyncio
import json
import logging
from collections import Mapping, Sequence

from aiohttp import client
from yarl import URL

from . import base


class RoStorage(base.AbstractStorageReadOnly):
    """ ReadOnly storage over http GET
    config:
        semaphore: int
        allow_hosts: list
        return_status: bool, method get returns tuple (CODE, VALUE)
        prefix: url prefix
        template: url template
        format: [json|str|bytes]
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
        self.session = client.ClientSession(loop=self.loop)

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

    async def _get(self, key):
        url = self.raw_key(key)
        async with self._semaphore:
            async with self.session.get(url) as response:
                logger = self.context.logger
                if response.status == 404:
                    return response.status, None
                elif response.status >= 400:
                    if logger.getEffectiveLevel() == logging.DEBUG:
                        logger.debug(
                            'HttpStorage request to %s '
                            'returned code %s:\n%s' % (
                                url, response.status,
                                (await response.read()).decode()))
                    return response.status, None
                elif self._format in ('str', 'bytes'):
                    data = await response.read()
                else:
                    return response.status, await response.json()
                status = response.status
        if self._format == 'str':
            return status, data.decode()
        return status, data

    async def get(self, key):
        status, data = await self._get(key)
        if self._return_status:
            return status, data
        return data

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
        prefix: url prefix
        template: url template
        format: [json|str|bytes]
        set: [post|put|patch]
    """

    @property
    def method_set(self):
        return getattr(self.session, self.config.get('set', 'post'))

    async def set(self, key, value):
        url = self.raw_key(key)
        if self._format == 'json':
            data = json.dumps(value)
            headers = {'content-type': 'application/json'}
        else:
            data = value
            headers = {}
        async with self._semaphore:
            async with self.method_set(
                    url, data=data, headers=headers) as response:
                logger = self.context.logger
                if logger.getEffectiveLevel() == logging.DEBUG:
                    logger.debug(
                        'HttpStorage request to %s returned code %s:\n%s' % (
                            url, response.status,
                            (await response.read()).decode()))
                assert response.status <= 400, response.status
