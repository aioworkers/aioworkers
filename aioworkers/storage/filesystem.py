import hashlib
import os
import shutil

from ..core.formatter import FormattedEntity
from . import base
from .. import utils


class FileSystemStorage(FormattedEntity, base.AbstractStorage):
    @property
    def executor(self):
        return self._context[self._config.get('executor')]

    def _write(self, key, value):
        d = os.path.dirname(key)
        if os.path.exists(d):
            pass
        elif value is None:
            return
        else:
            os.makedirs(d)
        if value is None:
            os.remove(key)
        else:
            with open(key, 'wb') as f:
                f.write(self.encode(value))

    def _write_chunk(self, f, data):
        return self.loop.run_in_executor(
            self.executor, f.write, data)

    def _open(self, key, mode='rb'):
        path = self.raw_key(key)

        def file_open(path, mode):
            if 'w' in mode or '+' in mode:
                d = os.path.dirname(path)
                if not os.path.exists(d):
                    os.makedirs(d)
            return open(path, mode)

        return self.loop.run_in_executor(
            self.executor, file_open, path, mode)

    def _close(self, f):
        return self.loop.run_in_executor(
            self.executor, f.close)

    def _read(self, key):
        if not os.path.exists(key):
            return
        with open(key, 'rb') as f:
            return self.decode(f.read())

    def raw_key(self, key):
        if os.path.isabs(key):
            raise ValueError(key)
        return os.path.join(self._config.path, key)

    async def set(self, key, value):
        k = self.raw_key(key)
        await self.loop.run_in_executor(
            self.executor, self._write, k, value)

    @utils.method_replicate_result(key=lambda self, k: k)
    async def get(self, key):
        k = self.raw_key(key)
        return await self.loop.run_in_executor(
            self.executor, self._read, k)

    def _copy(self, key_source, storage_dest, key_dest, copy_func):
        s = self.raw_key(key_source)
        d = storage_dest.raw_key(key_dest)
        target_dir = os.path.dirname(d)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        if os.path.exists(s):
            copy_func(s, d)
        elif not os.path.exists(d):
            return False
        else:
            os.remove(d)
            return True

    def copy(self, key_source, storage_dest, key_dest):
        if isinstance(storage_dest, FileSystemStorage):
            return self.loop.run_in_executor(
                self.executor, self._copy, key_source,
                storage_dest, key_dest, shutil.copy)
        return super().copy(key_source, storage_dest, key_dest)

    def move(self, key_source, storage_dest, key_dest):
        if isinstance(storage_dest, FileSystemStorage):
            return self.loop.run_in_executor(
                self.executor, self._copy, key_source,
                storage_dest, key_dest, shutil.move)
        return super().move(key_source, storage_dest, key_dest)


class NestedFileSystemStorage(FileSystemStorage):
    def _nested(self, key):
        return os.path.join(key[:2], key[2:4], key)

    def raw_key(self, key):
        return super().raw_key(self._nested(key))


class HashFileSystemStorage(NestedFileSystemStorage):
    def raw_key(self, key):
        ext = os.path.splitext(key)[-1]
        hash = hashlib.md5()
        hash.update(key.encode())
        d = hash.hexdigest() + ext
        return super().raw_key(d)
