from aioworkers.core.config import MergeDict
from aioworkers.storage.http import Storage


async def test_set_get(loop):
    key = 'https://github.com/aamalev/aioworkers'
    data = 'aioworkers'
    config = MergeDict(
        name='',
        semaphore=1,
        format='str',
    )
    storage = Storage(config, loop=loop)
    await storage.init()
    assert data in await storage.get(key)
