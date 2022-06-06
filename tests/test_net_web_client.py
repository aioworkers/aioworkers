import pytest
from aiohttp import web


@pytest.fixture
def config_yaml():
    return """
    storage:
        cls: aioworkers.storage.http.Storage
        headers:
          A: b
    """


@pytest.mark.timeout(5)
async def test_web_client(context, aiohttp_client):
    async def _handler(request):
        return web.json_response(["Python"])

    app = web.Application()
    app.router.add_get('/test/1', _handler)
    client = await aiohttp_client(app)
    url = client.make_url('/test/1')
    async with context.storage.session.request(url) as response:
        assert response.status
        assert response.reason
        assert response.headers
        data = await response.read()
        assert isinstance(data, bytes)
    assert response.isclosed()
    async with context.storage.session.request(url / '2') as response:
        assert response.status
        assert response.reason
        assert response.headers
        data = await response.read()
        assert isinstance(data, bytes)
