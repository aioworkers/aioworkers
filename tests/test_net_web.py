import socket

import pytest

from aioworkers.storage import StorageError


@pytest.fixture
def aioworkers(aioworkers):
    aioworkers.plugins.append("aioworkers.net.web")
    return aioworkers


@pytest.fixture
def config_yaml(unused_tcp_port_factory):
    return """
    http.port: {port}
    web.resources:
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
    """.format(port=unused_tcp_port_factory())


@pytest.fixture
def config(config):
    config.update(bin_data=b"qwerty")
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
        await context.storage.set(url / 'api/not/found/%aa', b'123')  # 404


@pytest.mark.parametrize(
    "connection,smsg",
    [
        ("close", "GET /api/str HTTP/1.0\r\n\r\n"),
        ("keep-alive", "GET /api/str HTTP/1.0\r\nConnection: keep-alive\r\n\r\n"),
        ("keep-alive", "GET /api/str HTTP/1.1\r\nConnection: keep-alive\r\n\r\n"),
        ("keep-alive", "GET /api/str HTTP/1.1\r\n\r\n"),
    ],
)
async def test_keep_alive(context, event_loop, connection, smsg):
    http_version = "1.0" if "1.0" in smsg else "1.1"
    msg = smsg.encode("utf-8")
    r = f"HTTP/{http_version} 200 OK\r\nServer: aioworkers\r\n"
    conn = socket.create_connection((None, context.config.http.port))

    for _ in range(4 if connection == "keep-alive" else 1):
        conn.send(msg)
        response = b""
        while b"asdf" not in response:
            response += await event_loop.run_in_executor(None, conn.recv, 1024)
        assert response.decode("utf-8").startswith(r)
        assert "keep-alive" not in smsg or b"keep-alive" in response

    await event_loop.run_in_executor(None, conn.close)


async def test_parse_error(context, event_loop):
    conn = socket.create_connection((None, context.config.http.port))
    conn.send(b"GET/api/str HTTP/1.1\r\n\r\n")
    r = "HTTP/1.1 500 Expected space after method\r\nServer: aioworkers\r\n"
    response = await event_loop.run_in_executor(None, conn.recv, 1024)
    assert response.decode("utf-8").startswith(r)
    await event_loop.run_in_executor(None, conn.close)
