import pytest
from aiohttp import web

from aioworkers.core.config import Config
from aioworkers.core.context import Context
from aioworkers.net.uri import URL
from aioworkers.storage import StorageError


async def test_set_get(loop, aiohttp_client):
    app = web.Application()
    app.router.add_get(
        '/test/1',
        lambda x: web.json_response(["Python"]),
    )
    client = await aiohttp_client(app)
    url = client.make_url('/')

    data = 'Python'
    config = Config(
        storage=dict(
            cls='aioworkers.storage.http.Storage',
            prefix=str(url),
            headers=[['A', 'b']],
            format='json',
        )
    )

    async with Context(config=config, loop=loop) as context:
        storage = context.storage
        assert data in await storage.get('test/1')
        with pytest.raises(StorageError):
            await storage.set('test/1', data)


async def test_format(loop):
    config = Config(
        storage=dict(
            cls='aioworkers.storage.http.Storage',
            format='bytes',
        )
    )
    async with Context(config=config, loop=loop) as context:
        storage = context.storage
        assert isinstance(storage.raw_key('test'), URL)
