import asyncio
import tempfile

from aioworkers.core.config import MergeDict
from aioworkers.storage.filesystem import HashFileSystemStorage


async def test_set_get(loop):
    key = '4423'
    data = b'234'
    with tempfile.TemporaryDirectory() as d:
        config = MergeDict(
            name='',
            path=d,
            executor=None,
        )
        storage = HashFileSystemStorage(config, loop=loop)
        await storage.set(key, data)
        d = await asyncio.gather(storage.get(key), storage.get(key), loop=loop)
        for j in d:
            assert data == j
