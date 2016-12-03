import asyncio
import tempfile

import pytest

from aioworkers.core.config import MergeDict
from aioworkers.core.context import Context
from aioworkers.storage.filesystem import \
    HashFileSystemStorage, FileSystemStorage


async def test_set_get(loop):
    key = '4423'
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

        with pytest.raises(ValueError):
            await storage.set('/abs/path', None)

        assert not await storage.get('empty value')

        await storage.set(key, data)
        d = await asyncio.gather(storage.get(key), storage.get(key), loop=loop)
        for j in d:
            assert data == j


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
