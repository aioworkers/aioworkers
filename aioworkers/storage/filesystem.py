import hashlib
import os

from ..core.formatter import FormattedEntity
from . import base
from .. import utils


class FileSystemStorage(FormattedEntity, base.AbstractStorage):
    @property
    def executor(self):
        return self._context[self._config.get('executor')]

    def _write(self, key, value):
        d = os.path.dirname(key)
        if not os.path.exists(d):
            os.makedirs(d)
        with open(key, 'wb') as f:
            f.write(self.encode(value))

    def _read(self, key):
        if not os.path.exists(key):
            return
        with open(key, 'rb') as f:
            return self.decode(f.read())

    def _make_key(self, key):
        if os.path.isabs(key):
            raise ValueError(key)
        return os.path.join(self._config.path, key)

    async def set(self, key, value):
        k = self._make_key(key)
        await self.loop.run_in_executor(
            self.executor, self._write, k, value)

    @utils.method_replicate_result(key=lambda self, k: k)
    async def get(self, key):
        k = self._make_key(key)
        return await self.loop.run_in_executor(
            self.executor, self._read, k)


class HashFileSystemStorage(FileSystemStorage):
    def _make_key(self, key):
        hash = hashlib.md5()
        hash.update(key.encode())
        d = hash.hexdigest()
        k = os.path.join(d[:2], d[2:4], d)
        return super()._make_key(k)
