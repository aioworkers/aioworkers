import logging
from abc import abstractmethod
from typing import Any, FrozenSet, Mapping, Sequence, Union

from ..core.base import ExecutorEntity, LoggingEntity
from ..core.formatter import FormattedEntity
from ..http import URL
from ..net.web.client import Session
from . import StorageError, base


class StorageConnectionError(StorageError):
    pass


class StorageDataFormatError(StorageError):
    pass


class AbstractHttpStorage(
    FormattedEntity,
    LoggingEntity,
    base.AbstractStorageReadOnly,
):
    """ReadOnly storage over http GET
    config:
        conn_limit: int = 1
        conn_timeout: float
        read_timeout: float
        allow_hosts: list
        return_status: bool, method get returns tuple (CODE, VALUE)
        prefix: url prefix
        headers: Mapping or None
        template: url template
        format: [json|str|bytes], default json
    """

    def __init__(self, *args, **kwargs):
        self.session = None
        super().__init__(*args, **kwargs)

    async def init(self):
        self._prefix = self.config.get('prefix')
        self._template = self.config.get('template')
        if self._prefix:
            self._prefix = URL(self._prefix)
        self._allow_hosts = self.config.get('allow_hosts')
        self._format = self.config.get('format', 'json')
        self._return_status = self.config.get('return_status', False)

        headers = self.config.get('headers')
        self.session_params = {}
        if headers:
            self.session_params['headers'] = headers
        for param in ('conn_timeout', 'read_timeout'):
            if param in self.config:
                self.session_params[param] = self.config[param]
        self.session = await self.session_factory(**self.session_params)
        self.context.on_stop.append(self.stop)

    @abstractmethod
    async def session_factory(self, **kwargs):
        pass

    async def reset_session(self, **kwargs):
        if self.session is not None:
            await self.session.close()
        if kwargs:
            kwargs = {**self.session_params, **kwargs}
        else:
            kwargs = self.session_params
        self.session = await self.session_factory(**kwargs)

    async def stop(self):
        await self.session.close()

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

    async def request(
        self,
        url: Union[str, URL],
        raise_for_status: FrozenSet[int] = frozenset(),
        **kwargs,
    ):
        async with self.session.request(url, **kwargs) as response:
            data = await response.read()
        try:
            formatter = self.registry.get(response.headers['Content-Type'])
        except KeyError:
            formatter = self
        result = formatter.decode(data)
        if response.status in raise_for_status:
            raise StorageError(f'Exception by status {response.status}')
        if self._return_status:
            return response.status, result
        else:
            return result

    def get(self, key):
        url = self.raw_key(key)
        return self.request(url)

    async def copy(self, key_source, storage_dest, key_dest):
        """Return True if data are copied
        * optimized for http->fs copy
        * not supported return_status
        """
        from aioworkers.storage.filesystem import FileSystemStorage

        if not isinstance(storage_dest, FileSystemStorage):
            return super().copy(key_source, storage_dest, key_dest)
        url = self.raw_key(key_source)
        async with self.session(url, method='get') as response:
            if response.status == 404:
                return
            elif response.status >= 400:
                if self.logger.getEffectiveLevel() == logging.DEBUG:
                    self.logger.debug(
                        'HttpStorage request to %s '
                        'returned code %s:\n%s'
                        % (
                            url,
                            response.status,
                            (await response.read()).decode(),
                        )
                    )
                return
            async with storage_dest.raw_key(key_dest).open('wb') as f:
                async for chunk in response.content.iter_any():
                    await f.write(chunk)
                return True


class RoStorage(ExecutorEntity, AbstractHttpStorage):
    def set_config(self, config):
        cfg = config.new_parent(executor=config.get_int('conn_limit', 1))
        super().set_config(cfg)

    async def session_factory(self, **kwargs):
        return Session.from_entity(self, **kwargs)

    async def request(self, url, **kwargs):
        try:
            return await super().request(url, **kwargs)
        except StorageError:
            raise
        except Exception as e:
            raise StorageError() from e


class Storage(RoStorage, base.AbstractStorageWriteOnly):
    """RW storage over http
    config:
        conn_limit: int
        allow_hosts: list
        return_status: bool, method get returns tuple (CODE, VALUE)
        prefix: url prefix
        template: url template
        headers: Mapping or None
        format: [json|str|bytes], default json
        set: [post|put|patch], default post
    """

    def set(
        self,
        key: Any,
        value: Any,
        *,
        raise_for_status: FrozenSet[int] = frozenset([404, 405]),
    ):
        url = self.raw_key(key)
        data = self.encode(value)
        headers = {}
        if self._formatter.mimetypes:
            headers['Content-Type'] = self._formatter.mimetypes[0]

        return self.request(
            url,
            method=self.config.get('set', 'post'),
            data=data,
            headers=headers,
            raise_for_status=raise_for_status,
        )
