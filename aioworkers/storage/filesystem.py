import hashlib
import os
import shutil
import tempfile
from pathlib import Path, PurePath

from . import base, StorageError
from .. import utils
from ..core.formatter import FormattedEntity


class FileSystemStorage(FormattedEntity, base.AbstractStorage):
    PARAM_LIMIT_FREE_SPACE = 'limit_free_space'
    PARAM_EXECUTOR = 'executor'

    def init(self):
        self._space_waiters = []
        return super().init()

    @property
    def executor(self):
        return self._context[self._config.get(self.PARAM_EXECUTOR)]

    def disk_usage(self):
        return self.loop.run_in_executor(
            self.executor, shutil.disk_usage, self._config.path)

    async def get_free_space(self):
        du = await self.disk_usage()
        return du.free

    async def _wait_free_space(self, size=None):
        limit = self._config.get(self.PARAM_LIMIT_FREE_SPACE)
        if limit:
            limit <<= 20
        else:
            return
        free = await self.get_free_space()
        if size is None or free < size + limit:
            f = self.loop.create_future()
            self._space_waiters.append((f, size))
            await f

    async def _next_space_waiter(self):
        limit = self._config.get(self.PARAM_LIMIT_FREE_SPACE)
        if limit:
            limit <<= 20
        else:
            return
        free = await self.get_free_space()
        for fsize in self._space_waiters:
            f, size = fsize
            if free > (size or 0) + limit:
                f.set_result(None)
                to_del = fsize
                break
        else:
            return
        self._space_waiters.remove(to_del)

    def _write(self, key: Path, value):
        d = key.parent
        if d.exists():
            pass
        elif value is None:
            return
        else:
            d.mkdir(parents=True)
        if value is not None:
            with tempfile.NamedTemporaryFile(
                    dir=self.config.get('tmp') or self.config.path,
                    delete=False) as f:
                source = f.name
                f.write(value)
            shutil.move(source, str(key))
        elif not key.exists():
            pass
        elif key.is_dir():
            shutil.rmtree(str(key))
        else:
            with tempfile.NamedTemporaryFile(
                    dir=self.config.get('tmp') or self.config.path) as f:
                shutil.move(str(key), f.name)

    def _write_chunk(self, f, data):
        return self.loop.run_in_executor(
            self.executor, f.write, data)

    async def _open(self, key, mode='rb'):
        path = self.raw_key(key)
        await self._wait_free_space()

        def file_open(path: Path, mode):
            if 'w' in mode or '+' in mode:
                d = path.parent
                d.mkdir(parents=True, exist_ok=True)
            return path.open(mode)

        return await self.loop.run_in_executor(
            self.executor, file_open, path, mode)

    async def _close(self, f):
        await self.loop.run_in_executor(
            self.executor, f.close)
        await self._next_space_waiter()

    def _read(self, key):
        if not key.exists():
            return
        with key.open('rb') as f:
            return self.decode(f.read())

    def path_transform(self, rel_path: str):
        return rel_path

    def raw_key(self, *key):
        def flat(parts):
            if isinstance(parts, str):
                if os.path.isabs(parts):
                    raise ValueError('Path must be relative. '
                                     '[{}]'.format(parts))
                yield parts
            elif isinstance(parts, PurePath):
                if parts.is_absolute():
                    raise ValueError('Path must be relative. '
                                     '[{}]'.format(parts))
                yield parts
            elif isinstance(parts, (list, tuple)):
                for p in parts:
                    yield from flat(p)
            else:
                raise TypeError(
                    'Key must be relative path [str or Path]. '
                    'But {}'.format(parts))
        rel = os.path.normpath(str(PurePath(*flat(key))))

        base = self._config.path
        path = Path(os.path.normpath(
            os.path.join(
                base, self.path_transform(rel))))

        if path.relative_to(PurePath(base)) == '.':
            raise ValueError('Access denied: %s' % path)
        return path

    async def set(self, key, value):
        if value is not None:
            value = self.encode(value)
            await self._wait_free_space(len(value))
        k = self.raw_key(key)
        try:
            await self.loop.run_in_executor(
                self.executor, self._write, k, value)
        except OSError as e:
            raise StorageError(str(e)) from e
        await self._next_space_waiter()

    @utils.method_replicate_result(key=lambda self, k: k)
    async def get(self, key):
        k = self.raw_key(key)
        return await self.loop.run_in_executor(
            self.executor, self._read, k)

    def _copy(self, key_source, storage_dest, key_dest, copy_func):
        s = self.raw_key(key_source)
        d = storage_dest.raw_key(key_dest)
        target_dir = d.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        if s.exists():
            copy_func(str(s), str(d))
        elif not d.exists():
            return False
        else:
            d.unlink()
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
    def path_transform(self, rel_path: str):
        return os.path.join(rel_path[:2], rel_path[2:4], rel_path)


class HashFileSystemStorage(NestedFileSystemStorage):
    def path_transform(self, rel_path: str):
        ext = os.path.splitext(rel_path)[-1]
        hash = hashlib.md5()
        hash.update(rel_path.encode())
        d = hash.hexdigest() + ext
        return super().path_transform(d)
