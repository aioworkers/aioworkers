import pytest

from aioworkers.core.config import MergeDict
from aioworkers.core.context import Context
from aioworkers.storage.http import Storage


async def test_set_get(loop):
    key = 'https://github.com/aamalev/aioworkers'
    data = 'aioworkers'
    config = MergeDict(
        name='',
        semaphore=1,
        format='str',
    )
    context = Context(config=config, loop=loop)
    await context.init()
    storage = Storage(config, context=context, loop=loop)
    await storage.init()
    assert data in await storage.get(key)
    with pytest.raises(AssertionError):
        await storage.set(key, data)
