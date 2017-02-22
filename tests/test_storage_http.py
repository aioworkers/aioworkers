import pytest
from yarl import URL

from aioworkers.core.config import MergeDict
from aioworkers.core.context import Context
from aioworkers.storage import StorageError
from aioworkers.storage.http import Storage


async def test_set_get(loop):
    data = 'Python'
    config = MergeDict(
        name='',
        prefix='https://api.github.com/',
        semaphore=1,
        format='json',
    )
    context = Context(config=config, loop=loop)
    await context.init()
    storage = Storage(config, context=context, loop=loop)
    await storage.init()
    assert data in await storage.get('repos/aamalev/aioworkers/languages')
    with pytest.raises(StorageError):
        await storage.set('user/repos', data)
    await storage.stop()


async def test_format(loop):
    config = MergeDict(
        name='',
        semaphore=1,
        format='bytes',
    )
    context = Context(config=config, loop=loop)
    await context.init()
    storage = Storage(config, context=context, loop=loop)
    await storage.init()
    assert isinstance(storage.raw_key('test'), URL)
    await storage.stop()
