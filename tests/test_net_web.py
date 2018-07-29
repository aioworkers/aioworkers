import pytest


@pytest.fixture
def config(config):
    config.load_plugins('aioworkers.net.web')
    config.update({
        'app.resources': {'/api': {'get': '.data'}},
        'data': 1,
        'storage.cls': 'aioworkers.storage.http.Storage',
    })
    return config


async def test_web_server(context):
    url = context.http.url
    assert 1 == await context.storage.get(url / 'api')
