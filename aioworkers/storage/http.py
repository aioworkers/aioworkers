import asyncio
import json
import logging
from collections import Mapping

from aiohttp import client
from yarl import URL

from . import base


class RoStorage(base.AbstractStorageReadOnly):
    """ ReadOnly storage over http GET
    config:
        semaphore: int
        allow_hosts: list
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
        self.session = client.ClientSession(loop=self.loop)

    async def stop(self):
        self.session.close()

    def _make_url(self, key):
        if self._prefix:
            url = self._prefix / key
        elif self._template and isinstance(key, Mapping):
            url = URL(self._template.format_map(key))
        elif self._template and isinstance(key, (list, tuple)):
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

    async def get(self, key):
        url = self._make_url(key)
        async with self._semaphore:
            async with self.session.get(url) as response:
                logger = self.context.logger
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
                elif self._format in ('str', 'bytes'):
                    data = await response.read()
                else:
                    return await response.json()
        if self._format == 'str':
            return data.decode()
        return data


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
        url = self._make_url(key)
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
