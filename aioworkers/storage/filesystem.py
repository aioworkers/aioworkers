import hashlib
import os
import pathlib
import shutil
import sys
import tempfile
from abc import abstractmethod
from functools import partial
from pathlib import Path, PurePath
from typing import Mapping, Optional, Union

from .. import humanize
from ..core.base import AbstractNestedEntity, ExecutorEntity
from ..core.formatter import FormattedEntity
from . import StorageError, base

__all__ = (
    'AsyncPath',
    'FileSystemStorage',
    'HashFileSystemStorage',
    'NestedFileSystemStorage',
)


def flat(parts):
    if isinstance(parts, str):
        if os.path.isabs(parts):
            raise ValueError('Path must be relative. [{}]'.format(parts))
        yield parts
    elif isinstance(parts, PurePath):
        if parts.is_absolute():
            raise ValueError('Path must be relative. [{}]'.format(parts))
        yield parts
    elif isinstance(parts, (list, tuple)):
        for p in parts:
            yield from flat(p)
    else:
        raise TypeError(f"Key must be relative path [str or Path]. But {parts}")


class AbstractFileSystem(
    ExecutorEntity,
):
    @abstractmethod
    async def next_space_waiter(self):
        pass  # no cov

    @abstractmethod
    async def wait_free_space(self, size: Optional[int] = None):
        pass  # no cov


class AsyncFile:
    def __init__(self, fd, fs: AbstractFileSystem):
        self.fd = fd
        self.fs = fs
        self._closed = False

    async def read(self, *args, **kwargs):
        return await self.fs.run_in_executor(
            self.fd.read,
            *args,
            **kwargs,
        )

    async def write(self, *args, **kwargs):
        return await self.fs.run_in_executor(self.fd.write, *args, **kwargs)

    async def __aenter__(self):
        assert not self._closed
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        assert not self._closed
        await self.fs.run_in_executor(self.fd.close)
        await self.fs.next_space_waiter()

    def __aiter__(self):
        return self

    async def __anext__(self):
        result = await self.fs.run_in_executor(next, self.fd, None)
        if result is None:
            raise StopAsyncIteration()
        else:
            return result


class AsyncFileContextManager:
    def __init__(self, path, *args, **kwargs):
        self.path = path
        self.af = None
        if 'mode' in kwargs:
            self.mode = kwargs['mode']
        elif len(args) > 1:
            self.mode = args[1]
        else:
            self.mode = 'r'
        self._constructor = partial(*args, **kwargs)

    async def __aenter__(self):
        assert self.af is None, "File already opened"
        path = self.path
        fs = path.fs
        await fs.wait_free_space()
        if 'w' in self.mode or '+' in self.mode:
            await path.parent.mkdir(parents=True, exist_ok=True)
        fd = await fs.run_in_executor(self._constructor)
        self.af = AsyncFile(fd, fs)
        return self.af

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        assert self.af is not None, "File not opened"
        await self.af.close()
        self.af = None

    def __await__(self):
        return self.__aenter__().__await__()


class AsyncGlob:
    def __init__(self, path, pattern):
        self._factory = type(path)
        self._iter = path.path.glob(pattern)
        self.fs = path.fs

    def __aiter__(self):
        return self

    async def __anext__(self):
        result = await self.fs.run_in_executor(next, self._iter, None)
        if result is None:
            raise StopAsyncIteration()
        else:
            return self._factory(result, fs=self.fs)


class AsyncPath(PurePath):
    fs: AbstractFileSystem

    def __new__(cls, *args, fs: Optional[AbstractFileSystem] = None):
        if cls is AsyncPath:
            cls = AsyncWindowsPath if os.name == "nt" else AsyncPosixPath
        self = cls._from_parts(args, init=False)
        if not self._flavour.is_supported:
            raise NotImplementedError(f"cannot instantiate {cls.__name__} on your system")
        if fs is None:
            for i in args:
                if isinstance(i, AsyncPath):
                    fs = i.fs
                    break
        self._init(fs=fs)
        return self

    def _init(self, fs=None):
        if fs:
            self.fs = fs
        else:
            self.fs = _UnlimitedFileSystem()
        self.path = Path(self)

    async def exists(self) -> bool:
        return await self.fs.run_in_executor(self.path.exists)

    async def mkdir(self, *args, **kwargs):
        return await self.fs.run_in_executor(self.path.mkdir, *args, **kwargs)

    async def rmdir(self):
        return await self.fs.run_in_executor(self.path.rmdir)

    async def rmtree(self, ignore_errors: bool = False, onerror=None):
        return await self.fs.run_in_executor(shutil.rmtree, self.path, ignore_errors=ignore_errors, onerror=onerror)

    async def stat(self) -> os.stat_result:
        return await self.fs.run_in_executor(self.path.stat)

    async def is_dir(self) -> bool:
        return await self.fs.run_in_executor(self.path.is_dir)

    async def is_file(self) -> bool:
        return await self.fs.run_in_executor(self.path.is_file)

    async def unlink(self, missing_ok=False):
        return await self.fs.run_in_executor(self.path.unlink, missing_ok=missing_ok)

    async def read_text(self, *args, **kwargs) -> str:
        return await self.fs.run_in_executor(
            self.path.read_text,
            *args,
            **kwargs,
        )

    async def write_text(self, *args, **kwargs):
        return await self.fs.run_in_executor(
            self.path.write_text,
            *args,
            **kwargs,
        )

    async def read_bytes(self, *args, **kwargs) -> bytes:
        return await self.fs.run_in_executor(
            self.path.read_bytes,
            *args,
            **kwargs,
        )

    async def write_bytes(self, *args, **kwargs):
        return await self.fs.run_in_executor(self.path.write_bytes, *args, **kwargs)

    def _make_child(self, args):
        k = super()._make_child(args)  # type: ignore
        k._init(self.fs)
        return k

    @classmethod
    def _from_parts(cls, args, init=True):
        self = object.__new__(cls)
        drv, root, parts = self._parse_args(args)  # type: ignore
        self._drv = drv  # type: ignore
        self._root = root  # type: ignore
        self._parts = parts  # type: ignore
        if init:
            fs = None
            for t in args:
                if isinstance(t, AsyncPath):
                    fs = t.fs
                    break
            self._init(fs=fs)
        return self

    def open(self, *args, **kwargs):
        return AsyncFileContextManager(
            self,
            self.path.open,
            *args,
            **kwargs,
        )

    @property
    def parent(self):
        p = super().parent
        p._init(self.fs)
        return p

    @property
    def normpath(self):
        return type(self)(
            os.path.normpath(str(self)),
            fs=self.fs,
        )

    def glob(self, pattern):
        return AsyncGlob(self, pattern)

    def with_suffix(self, suffix: str):
        result = super().with_suffix(suffix)
        result._init(self.fs)
        return result

    def with_name(self, name: str):
        result = super().with_name(name)
        result._init(self.fs)
        return result

    if sys.version_info >= (3, 9):  # no cov

        def with_stem(self, stem: str):
            result = super().with_stem(stem)
            result._init(self.fs)
            return result


class AsyncPosixPath(AsyncPath, pathlib.PurePosixPath):
    pass


class AsyncWindowsPath(AsyncPath, pathlib.PureWindowsPath):
    pass


class _UnlimitedFileSystem(AbstractFileSystem):
    async def next_space_waiter(self):
        pass

    async def wait_free_space(self, size: Optional[int] = None):
        pass


class BaseFileSystemStorage(
    AbstractNestedEntity,
    AbstractFileSystem,
    FormattedEntity,
    base.AbstractStorage,
):
    PARAM_LIMIT_FREE_SPACE = 'limit_free_space'

    def __init__(self, *args, **kwargs):
        self._space_waiters = []
        path = kwargs.get("path", ".")
        self._path = AsyncPath(path, fs=self)
        self._tmp = kwargs.get("tmp") or path
        self._limit = self._get_limit_free_space(kwargs)
        super().__init__(*args, **kwargs)

    def _get_limit_free_space(self, cfg: Mapping) -> Union[int, float, None]:
        result = cfg.get(self.PARAM_LIMIT_FREE_SPACE)
        if isinstance(result, int):
            result <<= 20  # int in MB
        elif isinstance(result, float):
            result *= 2**20  # float in MB
        elif isinstance(result, str):
            result = humanize.parse_size(result)
        return result

    def set_config(self, config):
        super().set_config(config)
        self._path = AsyncPath(self.config.path, fs=self)
        self._tmp = self.config.get("tmp") or self.config.path
        self._limit = self._get_limit_free_space(self._config)

    def factory(self, item, config=None):
        path = self._path.joinpath(*flat(item)).normpath
        simple_item = path.relative_to(self._path)
        inst = super().factory(simple_item, config)
        for i in (
            '_formatter',
            '_space_waiters',
            '_executor',
            '_tmp',
            '_limit',
        ):
            setattr(inst, i, getattr(self, i))
        inst._path = path
        return inst

    def disk_usage(self):
        def disk_usage(path):
            try:
                return shutil.disk_usage(path)
            except FileNotFoundError:
                os.makedirs(path, exist_ok=True)
            return shutil.disk_usage(path)

        return self.run_in_executor(disk_usage, self._config.path)

    async def get_free_space(self):
        du = await self.disk_usage()
        return du.free

    async def wait_free_space(self, size=None):
        if not self._limit:
            return
        free = await self.get_free_space()
        if size is None or free < size + self._limit:
            f = self.loop.create_future()
            self._space_waiters.append((f, size))
            await f

    async def next_space_waiter(self):
        if not self._limit:
            return
        free = await self.get_free_space()
        for fsize in self._space_waiters:
            f, size = fsize
            if free > (size or 0) + self._limit:
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
            d.mkdir(parents=True, exist_ok=True)
        if value is not None:
            with tempfile.NamedTemporaryFile(
                dir=self._tmp,
                delete=False,
            ) as f:
                source = f.name
                f.write(value)
            shutil.move(source, str(key))
        elif not key.exists():
            pass
        elif key.is_dir():
            shutil.rmtree(str(key))
        else:
            with tempfile.NamedTemporaryFile(dir=self._tmp) as f:
                shutil.move(str(key), f.name)

    def path_transform(self, rel_path: str):
        return rel_path

    def raw_key(self, *key):
        rel = os.path.normpath(str(PurePath(*flat(key))))
        path = self._path.joinpath(self.path_transform(rel)).normpath
        path.relative_to(self._path)  # Access denied: raise ValueError
        return path

    async def set(self, key, value):
        if value is not None:
            value = self.encode(value)
            await self.wait_free_space(len(value))
        k = self.raw_key(key).path
        try:
            await self.run_in_executor(self._write, k, value)
        except OSError as e:
            raise StorageError(str(e)) from e
        await self.next_space_waiter()

    async def get(self, key):
        k = self.raw_key(key)
        if await k.exists():
            v = await k.read_bytes()
            return self.decode(v)

    def open(self, key, *args, **kwargs):
        return self.raw_key(key).open(*args, **kwargs)

    def _copy(self, key_source, storage_dest, key_dest, copy_func):
        s = self.raw_key(key_source).path
        d = storage_dest.raw_key(key_dest).path
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
            return self.run_in_executor(
                self._copy,
                key_source,
                storage_dest,
                key_dest,
                shutil.copy,
            )
        return super().copy(key_source, storage_dest, key_dest)

    def move(self, key_source, storage_dest, key_dest):
        if isinstance(storage_dest, FileSystemStorage):
            return self.run_in_executor(
                self._copy,
                key_source,
                storage_dest,
                key_dest,
                shutil.move,
            )
        return super().move(key_source, storage_dest, key_dest)

    def __repr__(self):
        cls = type(self)
        props = []
        if self.config:
            props.append(('path', self._path))
            if self.config.get('executor'):
                props.append(('c', self.config.executor))
        return '<{}.{} {}>'.format(
            cls.__module__,
            cls.__qualname__,
            ' '.join(map('{0[0]}={0[1]}'.format, props)),
        )


class FileSystemStorage(
    BaseFileSystemStorage,
    base.AbstractListedStorage,
):
    def list(self, glob='*'):
        base = self._path
        g = base.path.glob(glob)
        return self.run_in_executor(
            list,
            map(lambda x: x.relative_to(base), g),
        )

    async def length(self, glob='*'):
        return len(await self.list(glob))


class NestedFileSystemStorage(BaseFileSystemStorage):
    def path_transform(self, rel_path: str):
        return os.path.join(rel_path[:2], rel_path[2:4], rel_path)


class HashFileSystemStorage(NestedFileSystemStorage):
    def path_transform(self, rel_path: str):
        ext = os.path.splitext(rel_path)[-1]
        hash = hashlib.md5()
        hash.update(rel_path.encode("utf-8"))
        d = hash.hexdigest() + ext
        return super().path_transform(d)
