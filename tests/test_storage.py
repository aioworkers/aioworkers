import asyncio
import tempfile
from pathlib import PurePath
from unittest import mock

import pytest

from aioworkers.core.config import MergeDict
from aioworkers.core.context import Context
from aioworkers.storage.filesystem import \
    HashFileSystemStorage, FileSystemStorage
from aioworkers.storage.meta import FutureStorage


async def test_set_get(loop):
    key = ('4423', '123')
    data = b'234'
    with tempfile.TemporaryDirectory() as d:
        config = MergeDict(
            name='',
            path=d,
            executor=None,
        )
        context = Context({}, loop=loop)
        storage = FileSystemStorage(config, context=context, loop=loop)
        await storage.init()

        await storage.set(('empty', 'value', '1'), None)
        assert not await storage.get('empty value 2')

        await storage.set(key, data)
        await storage.set(key, None)
        await storage.set(key, data)
        d = await asyncio.gather(storage.get(key), storage.get(key), loop=loop)
        for j in d:
            assert data == j


async def test_key(loop):
    with tempfile.TemporaryDirectory() as d:
        config = MergeDict(
            name='',
            path=d,
            executor=None,
        )
        context = Context({}, loop=loop)
        storage = FileSystemStorage(config, context=context, loop=loop)
        await storage.init()

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


async def test_copy(loop):
    key1 = '1'
    key2 = '2'
    key3 = '3'
    key4 = ('4', '5')
    data = b'234'
    with tempfile.TemporaryDirectory() as d:
        config = MergeDict(
            name='',
            path=d,
            executor=None,
        )
        context = Context({}, loop=loop)
        storage = FileSystemStorage(config, context=context, loop=loop)
        await storage.init()

        await storage.set(key1, data)
        await storage.copy(key1, storage, key3)
        assert data == await storage.get(key3)
        await storage.copy(key2, storage, key3)
        await storage.move(key2, storage, key4)
        assert not await storage.get(key4)

        fstor = FutureStorage(mock.Mock(name=''), loop=loop)
        await fstor.init()
        await storage.copy(key2, fstor, key3)
        await storage.move(key2, fstor, key4)


async def test_freespace(loop):
    key1 = '1'
    key2 = '2'
    data = b'000'
    with tempfile.TemporaryDirectory() as d:
        config = MergeDict(
            name='',
            path=d,
            executor=None,
        )
        context = Context({}, loop=loop)
        storage = FileSystemStorage(config, context=context, loop=loop)
        await storage.init()

        with mock.patch.object(storage, 'get_free_space', asyncio.coroutine(lambda: 1)):
            assert 1 == await storage.get_free_space()
            storage.config.limit_free_space = 2
            f = asyncio.ensure_future(storage.set(key1, data), loop=loop)
            await asyncio.sleep(0, loop=loop)
        await storage.set(key2, data)
        await storage.set(key1, None)
        assert not storage._space_waiters
        await f


async def test_pickle(loop):
    key = '4423'
    data = {'f': 3}
    with tempfile.TemporaryDirectory() as d:
        config = MergeDict(
            name='',
            path=d,
            format='pickle',
            executor=None,
        )
        context = Context({}, loop=loop)
        storage = HashFileSystemStorage(config, context=context, loop=loop)
        await storage.init()
        await storage.set(key, data)
        assert data == await storage.get(key)


async def test_chunk(loop):
    key4 = ('4', '5')
    data = b'234'
    with tempfile.TemporaryDirectory() as d:
        config = MergeDict(
            name='',
            path=d,
            executor=None,
        )
        context = Context({}, loop=loop)
        storage = FileSystemStorage(config, context=context, loop=loop)
        await storage.init()

        f = await storage._open(key4, 'wb')
        await storage._write_chunk(f, data)
        await storage._close(f)
        assert data == await storage.get(key4)
