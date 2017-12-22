import hashlib
import os
import pathlib
import shutil
import tempfile
from functools import partial
from pathlib import Path, PurePath

from . import base, StorageError
from .. import utils, humanize
from ..core.base import AbstractNestedEntity
from ..core.formatter import FormattedEntity


def async_method(self, method: str, sync_obj=None):
    if sync_obj is None:
        sync_obj = self
    m = getattr(sync_obj, method)

    def wrap(*args, **kwargs):
        return self.storage.run_in_executor(m, *args, **kwargs)
    return wrap


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


class AsyncFile:
    def __init__(self, fd, storage=None):
        self.fd = fd
        self.storage = storage
        for i in ('write', 'read', 'close'):
            setattr(self, i, async_method(self, i, fd))


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
        storage = path.storage
        await storage.wait_free_space()
        if 'w' in self.mode or '+' in self.mode:
            await path.parent.mkdir(parents=True, exist_ok=True)
        fd = await storage.run_in_executor(self._constructor)
        self.af = AsyncFile(fd, storage)
        return self.af

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.af.close()
        self.af = None
        await self.path.storage.next_space_waiter()


class AsyncPath(PurePath):
    def __new__(cls, *args, storage=None):
        if cls is AsyncPath:
            cls = AsyncWindowsPath if os.name == 'nt' else AsyncPosixPath
        self = cls._from_parts(args, init=False)
        if not self._flavour.is_supported:
            raise NotImplementedError("cannot instantiate %r on your system"
                                      % (cls.__name__,))
        if storage is None:
            for i in args:
                if isinstance(i, AsyncPath):
                    storage = i.storage
                    break
        self._init(storage=storage)
        return self

    def _init(self, storage=None):
        self.storage = storage
        if not storage:
            return
        self.path = Path(self)
        for i in (
            'write_bytes', 'read_bytes',
            'write_text', 'read_text',
            'exists', 'mkdir', 'stat',
        ):
            setattr(self, i, async_method(self, i, self.path))

    def _make_child(self, args):
        k = super()._make_child(args)
        k._init(self.storage)
        return k

    @classmethod
    def _from_parts(cls, args, init=True):
        self = object.__new__(cls)
        drv, root, parts = self._parse_args(args)
        self._drv = drv
        self._root = root
        self._parts = parts
        if init:
            storage = None
            for t in args:
                if isinstance(t, AsyncPath):
                    storage = t.storage
                    break
            self._init(storage=storage)
        return self

    def open(self, *args, **kwargs):
        return AsyncFileContextManager(
            self, self.path.open, *args, **kwargs)

    @property
    def parent(self):
        p = super().parent
        p._init(self.storage)
        return p

    @property
    def normpath(self):
        return type(self)(
            os.path.normpath(str(self)),
            storage=self.storage)


class AsyncPosixPath(AsyncPath, pathlib.PurePosixPath):
    pass


class AsyncWindowsPath(AsyncPath, pathlib.PureWindowsPath):
    pass


class FileSystemStorage(
        AbstractNestedEntity,
        FormattedEntity,
        base.AbstractStorage):

    PARAM_LIMIT_FREE_SPACE = 'limit_free_space'
    PARAM_EXECUTOR = 'executor'

    def init(self):
        self._space_waiters = []

        ex = self._config.get(self.PARAM_EXECUTOR)
        if isinstance(ex, int):
            cls = utils.import_name('concurrent.futures.ThreadPoolExecutor')
            ex = cls(max_workers=ex)
        elif isinstance(ex, str):
            ex = self._context[ex]
        self._executor = ex

        self._limit = self._config.get(self.PARAM_LIMIT_FREE_SPACE)
        if isinstance(self._limit, int):
            self._limit = self._limit << 20  # int in MB
        elif isinstance(self._limit, str):
            self._limit = humanize.parse_size(self._limit)

        self._path = AsyncPath(self.config.path, storage=self)
        self._tmp = self.config.get('tmp') or self.config.path

        return super().init()

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

    @property
    def executor(self):
        return self._executor

    def run_in_executor(self, f, *args, **kwargs):
        if kwargs:
            f = partial(f, **kwargs)
        return self.loop.run_in_executor(self._executor, f, *args)

    def disk_usage(self):
        def disk_usage(path):
            try:
                return shutil.disk_usage(path)
            except FileNotFoundError:
                os.makedirs(path, exist_ok=True)
            return shutil.disk_usage(path)

        return self.loop.run_in_executor(
            self._executor, disk_usage, self._config.path)

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
            d.mkdir(parents=True)
        if value is not None:
            with tempfile.NamedTemporaryFile(
                    dir=self._tmp,
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
                    dir=self._tmp) as f:
                shutil.move(str(key), f.name)

    def path_transform(self, rel_path: str):
        return rel_path

    def raw_key(self, *key):
        rel = os.path.normpath(str(PurePath(*flat(key))))
        path = self._path.joinpath(self.path_transform(rel)).normpath
        if path.relative_to(self._path) == '.':
            raise ValueError('Access denied: %s' % path)
        return path

    async def set(self, key, value):
        if value is not None:
            value = self.encode(value)
            await self.wait_free_space(len(value))
        k = self.raw_key(key).path
        try:
            await self.loop.run_in_executor(
                self.executor, self._write, k, value)
        except OSError as e:
            raise StorageError(str(e)) from e
        await self.next_space_waiter()

    @utils.method_replicate_result(key=lambda self, k: k)
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
            return self.loop.run_in_executor(
                self._executor, self._copy, key_source,
                storage_dest, key_dest, shutil.copy)
        return super().copy(key_source, storage_dest, key_dest)

    def move(self, key_source, storage_dest, key_dest):
        if isinstance(storage_dest, FileSystemStorage):
            return self.loop.run_in_executor(
                self._executor, self._copy, key_source,
                storage_dest, key_dest, shutil.move)
        return super().move(key_source, storage_dest, key_dest)

    def __repr__(self):
        cls = type(self)
        props = [('path', self._path)]
        if self.config.get('executor'):
            props.append(('c', self.config.executor))
        return '<{}.{} {}>'.format(
            cls.__module__, cls.__qualname__,
            ' '.join(map('{0[0]}={0[1]}'.format, props)))


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
