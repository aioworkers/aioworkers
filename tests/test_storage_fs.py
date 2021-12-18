import asyncio
import tempfile
from pathlib import PurePath
from unittest import mock

import pytest

from aioworkers.core.context import Context
from aioworkers.storage.base import FieldStorageMixin
from aioworkers.storage.filesystem import AsyncPath, FileSystemStorage


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def config_yaml(tmp_dir):
    return """
    storage:
      cls: aioworkers.storage.filesystem.FileSystemStorage
      executor: null
      path: {path}
    field:
      cls: tests.test_storage_fs.Store
      executor: null
      format: json
      path: {path}
    hstore:
      cls: aioworkers.storage.filesystem.HashFileSystemStorage
      path: {path}
      format: pickle
    future:
      cls: aioworkers.storage.meta.FutureStorage
    exec1:
      cls: aioworkers.storage.filesystem.FileSystemStorage
      path: {path}
      executor: 1
    exec_ext:
      cls: aioworkers.storage.filesystem.FileSystemStorage
      path: {path}
      executor: executor
    executor: null
    """.format(
        path=tmp_dir
    )


async def test_set_get(context):
    key = ('4423', '123')
    data = b'234'
    storage = context.storage
    assert repr(storage)

    await storage.set(('empty', 'value', '1'), None)
    assert not await storage.get('empty value 2')

    await storage.set(key, data)
    await storage.set(key, None)  # del file
    assert not await storage.get(key)

    await storage.set(key[0], None)  # del dir

    await storage.set(key, data)
    d = await asyncio.gather(
        storage.get(key), storage.get(key),
        loop=context.loop)
    for j in d:
        assert data == j


async def test_key(context):
    storage = context.storage

    assert str(storage.raw_key(('1', '3', ('4',)))).endswith('1/3/4')
    assert str(storage.raw_key((PurePath('1'), '3', ('4',)))).endswith('1/3/4')

    with pytest.raises(TypeError):
        storage.raw_key(1)

    with pytest.raises(ValueError):
        storage.raw_key('../..')

    with pytest.raises(ValueError):
        storage.raw_key('/abs/path')

    with pytest.raises(ValueError):
        storage.raw_key(PurePath('/abs/path'))


async def test_copy(context):
    storage = context.storage
    key1 = '1'
    key2 = '2'
    key3 = '3'
    key4 = ('4', '5')
    data = b'234'

    await storage.set(key1, data)
    await storage.copy(key1, storage, key3)
    assert data == await storage.get(key3)
    await storage.copy(key2, storage, key3)
    await storage.move(key2, storage, key4)
    assert not await storage.get(key4)

    fstor = context.future
    await storage.copy(key2, fstor, key3)
    await storage.move(key2, fstor, key4)


async def test_freespace(context, loop):
    storage = context.storage
    key1 = '1'
    key2 = '2'
    data = b'000'

    assert await storage.get_free_space()

    with mock.patch.object(
        storage, 'get_free_space',
        asyncio.coroutine(lambda: 1)
    ):
        assert 1 == await storage.get_free_space()
        storage.config._val.limit_free_space = 2
        f = asyncio.ensure_future(storage.set(key1, data), loop=loop)
        await asyncio.sleep(0, loop=loop)
    await storage.set(key2, data)
    await storage.set(key1, None)
    assert not storage._space_waiters
    await f


async def test_pickle(context):
    storage = context.hstore
    key = '4423'
    data = {'f': 3}
    await storage.init()
    await storage.set(key, data)
    assert data == await storage.get(key)


async def test_chunk(context):
    storage = context.storage
    key4 = ('4', '5')
    data = b'234'

    async with storage.open(key4, 'wb') as f:
        await f.write(data)
    assert data == await storage.get(key4)


class Store(FieldStorageMixin, FileSystemStorage):
    pass


async def test_field_storage(context):
    key = ('5', '6')
    data = {'f': 3, 'g': 4, 'h': 5}
    fields = ['f', 'g']
    storage = context.field
    await storage.set(key, data)
    assert data == await storage.get(key)
    assert 5 == await storage.get(key, field='h')
    await storage.set(key, 6, field='h')
    assert {'f': 3, 'g': 4} == await storage.get(key, fields=fields)
    await storage.set(key, {'z': 1, 'y': 6}, fields=['z'])
    assert {'f': 3, 'g': 4, 'h': 6, 'z': 1} == await storage.get(key)
    await storage.set(key, None)


async def test_fd(context):
    storage = context.storage
    k = storage.raw_key('1')
    assert isinstance(k / '2', AsyncPath)
    assert isinstance('2' / k, AsyncPath)
    assert isinstance(AsyncPath(k), AsyncPath)
    assert isinstance(k.parent, AsyncPath)
    assert k.parent.storage

    async with k.open('w') as f:
        await f.write('123')

    assert '123' == await k.read_text()

    assert b'123' == await storage.get('1')
    await storage.set('1', None)

    f = await k.open('w')
    async with f:
        await f.write('123')

    f = await k.open()
    async for line in f:
        assert line == '123'
    await f.close()

    async with k.open() as f:
        async for line in f:
            assert line == '123'

    await storage.set('1', None)


async def test_nested(context):
    storage = context.storage
    await storage.set('a/2', b'0')
    assert b'0' == await storage.a.get('2')
    assert b'0' == await storage['b', '../a'].get('2')
    assert b'0' == await context['storage.a'].get('2')

    with pytest.raises(AttributeError):
        print(storage._folder)


storage = FileSystemStorage()


async def test_obj(context):
    await context.storage.a.set('b', b'0')
    assert b'0' == await context.storage.a.get('b')


async def test_fs_glob(context):
    s = context.storage
    await s.set('1', b'1')
    assert await s.length()
    assert ['1'] == list(map(str, await s.list()))


async def test_asyncpath_glob(context):
    s = context.storage
    await s.set('1/2', b'1')
    k = s.raw_key('1')
    async for p in k.glob('*'):
        assert type(k) is type(p)
        assert p.name == '2'


async def test_async_path(tmp_dir):
    d = AsyncPath(tmp_dir)
    f = d / '1'
    await f.write_text('123')
    assert '123' == await f.read_text()


async def test_standalone(tmp_dir):
    s = FileSystemStorage(path=tmp_dir, format='json')
    await s.set('a', 1)
    assert 1 == await s.get('a')
    c = Context()
    c.storage = s
    assert s.context is c
    async with c:
        assert 1 == await c.storage.get('a')
