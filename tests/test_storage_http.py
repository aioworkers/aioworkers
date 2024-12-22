import pytest

try:
    from aiohttp import web
except ImportError:
    web = None

from aioworkers.core.config import Config
from aioworkers.core.context import Context
from aioworkers.net.uri import URL
from aioworkers.storage import StorageError
from aioworkers.storage.http import Storage


@pytest.mark.skipif(web is None, reason="Need aiohttp")
async def test_set_get(event_loop, aiohttp_client):
    async def _handler(request):
        return web.json_response(["Python"])

    app = web.Application()
    app.router.add_get('/test/1', _handler)
    client = await aiohttp_client(app)
    url = client.make_url('/')

    data = 'Python'
    config = Config(
        storage=dict(
            cls='aioworkers.storage.http.Storage',
            prefix=str(url),
            headers=[['A', 'b']],
            format='json',
            conn_timeout=1,
        )
    )

    async with Context(config=config, loop=event_loop) as context:
        storage = context.storage
        assert data in await storage.get('test/1')
        with pytest.raises(StorageError):
            await storage.set('test/1', data)


async def test_format(event_loop):
    config = Config(
        storage=dict(
            cls='aioworkers.storage.http.Storage',
            format='bytes',
        )
    )
    async with Context(config=config, loop=event_loop) as context:
        storage = context.storage
        assert isinstance(storage.raw_key('test'), URL)
        assert isinstance(storage.raw_key(URL('test')), URL)


async def test_reset(event_loop):
    config = Config(
        storage=dict(
            cls='aioworkers.storage.http.Storage',
            format='bytes',
        )
    )
    async with Context(config=config, loop=event_loop) as context:
        storage: Storage = context.storage
        await storage.reset_session()
        await storage.reset_session(conn_timeout=2)
