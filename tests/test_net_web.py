import pytest

from aioworkers.storage import StorageError


@pytest.fixture
def aioworkers(aioworkers):
    aioworkers.plugins.append('aioworkers.net.web')
    return aioworkers


@pytest.fixture
def config_yaml(unused_port):
    return """
    http.port: {port}
    app.resources:
        /api:
            get: .data
        /api/str:
            get: .str_data
        /api/bin:
            get: .bin_data
            post: tests.test_net_web.handler_post
    data: 1
    str_data: asdf
    storage.cls: aioworkers.storage.http.Storage
    """.format(
        port=unused_port()
    )


@pytest.fixture
def config(config):
    config.update(bin_data=b'qwerty')
    return config


async def handler_post(request, context):
    body = await request.read()
    return {'body': body.decode()}


@pytest.mark.timeout(5)
async def test_web_server(context):
    url = context.http.url
    assert 1 == await context.storage.get(url / 'api')
    assert 'asdf' == await context.storage.get(url / 'api/str')
    with pytest.raises(StorageError):
        await context.storage.set(url / 'api/str', b'123')  # 405
    assert b'qwerty' == await context.storage.get(url / 'api/bin')
    d = await context.storage.set(url / 'api/bin', b'123')
    assert d == {'body': '123'}
    with pytest.raises(StorageError):
        await context.storage.set(url / 'api/not/found', b'123')  # 404
