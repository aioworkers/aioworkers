import pytest


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


async def test_web_server(context):
    url = context.http.url
    assert 1 == await context.storage.get(url / 'api')
    assert b'asdf' == await context.storage.get(url / 'api/str')
    assert b'qwerty' == await context.storage.get(url / 'api/bin')
