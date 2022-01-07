from unittest import mock

from aioworkers.net.web.exceptions import HttpException
from aioworkers.net.web.request import Request


async def test_content_length():
    r = Request(
        {"headers": [(b"Content-Length", b"1")]},
        receive=mock.Mock(),
        send=mock.Mock(),
        context=mock.Mock(),
        app=mock.Mock(),
    )
    assert r.content_length == 1


async def test_method():
    r = Request(
        {"method": "GET"},
        receive=mock.Mock(),
        send=mock.Mock(),
        context=mock.Mock(),
        app=mock.Mock(),
    )
    assert r.method == "GET"


async def test_url():
    r = Request(
        {
            "scheme": "http",
            "path": "/api",
            "query_string": b"a=yes",
        },
        receive=mock.Mock(),
        send=mock.Mock(),
        context=mock.Mock(),
        app=mock.Mock(),
    )
    assert r.url.query.get("a") == "yes"


async def test_response_simple():
    r = Request(
        {},
        receive=mock.Mock(),
        send=mock.Mock(),
        context=mock.Mock(),
        app=mock.Mock(),
    )
    assert r.response()
    assert not r.response()


async def test_response_headers():
    r = Request(
        {},
        receive=mock.Mock(),
        send=mock.Mock(),
        context=mock.Mock(),
        app=mock.Mock(),
    )
    assert r.response(headers=[("H", "V")])


async def test_response_exception():
    r = Request(
        {},
        receive=mock.Mock(),
        send=mock.Mock(),
        context=mock.Mock(),
        app=mock.Mock(),
    )
    assert r.response(HttpException())
