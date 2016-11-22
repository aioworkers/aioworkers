from aioworkers.core.config import MergeDict
from aioworkers.storage.http import HostStorage


async def test_set_get(loop):
    key = 'https://github.com/aamalev/aioworkers'
    data = b'aioworkers'
    config = MergeDict(
        name='',
        semaphore=1,
    )
    storage = HostStorage(config, loop=loop)
    await storage.init()
    assert data in await storage.get(key)
