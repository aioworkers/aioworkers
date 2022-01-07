import asyncio
import logging
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)
from urllib.parse import unquote

if TYPE_CHECKING:  # pragma: no cover
    from .server import WebServer
else:
    WebServer = Any

logger = logging.getLogger(__name__)


class ASGIResponseSender:
    status_reason: Mapping[int, str] = {
        200: "OK",
        404: "Not found",
        405: "Method not allowed",
    }

    def __init__(self, transport: asyncio.Transport, server: WebServer):
        self._transport = transport
        self._server = server
        self._status: int = 200
        self._reason: str = "OK"
        self._headers: Sequence[Tuple[bytes, bytes]] = ()
        self._started: bool = False
        self._handlers = {
            "http.response.start": self._response_start,
            "http.response.body": self._response_body,
        }

    def _response_start(self, message: Mapping) -> None:
        self._status = message["status"]
        self._reason = (
            message.get("reason") or self.status_reason.get(self._status) or ""
        )
        self._headers = message.get("headers") or ()

    def _response_head(self, content_length: Optional[int] = None) -> None:
        write = self._transport.write
        write(f"HTTP/1.1 {self._status} {self._reason}".encode())
        write(b"\r\nServer: aioworkers")
        write(b"\r\nConnection: close")
        for h, v in self._server.headers.items():
            write(b"\r\n")
            write(h)
            write(b": ")
            write(v)
        for h, v in self._headers:
            if h.lower() == b"content-length":
                content_length = 0
            write(b"\r\n")
            write(h)
            write(b": ")
            write(v)

        if content_length:
            write(b"\r\nContent-Length: ")
            write(str(content_length).encode())

        write(b"\r\n\r\n")

    def _response_body(self, message: Mapping) -> None:
        body = message.get("body")
        more_body = message.get("more_body", False)
        if not self._started:
            content_length = 0
            if body and not more_body:
                content_length = len(body)
            self._response_head(content_length)
            self._started = True

        if body:
            self._transport.write(body)

        if not more_body:
            self._transport.close()

    def __call__(self, message: Mapping) -> "ASGIResponseSender":
        message_type = message["type"]
        handler: Optional[Callable[[Mapping], None]]
        handler = self._handlers.get(message_type)
        if handler is None:
            raise RuntimeError(f"Not supported type {message_type}")
        else:
            handler(message)
        return self

    async def _await(self):
        pass

    def __await__(self):
        return self._await().__await__()


class Protocol(asyncio.Protocol):
    _transport: asyncio.Transport
    _body_future: asyncio.Future
    _sender: ASGIResponseSender
    _headers: List[Tuple[bytes, bytes]]
    _scope: Dict

    def __init__(self, server):
        self._server = server
        self._parser = server.parser_factory(self)

    @classmethod
    def factory(cls, **kwargs):
        return partial(cls, **kwargs)

    def connection_made(self, transport):
        self._transport = transport
        self._sender = ASGIResponseSender(self._transport, self._server)
        self._body_future = self._server.loop.create_future()
        self._headers = []
        self._scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.1"},
            "scheme": "http",
            "headers": self._headers,
        }

    def data_received(self, data):
        try:
            self._parser.feed_data(data)
        except Exception:
            logger.exception("Request feed error")
            self._sender._response_start(dict(status=500))
            self._sender._response_body({})

    def on_url(self, url: bytes):
        self._scope["http_version"] = self._parser.get_http_version()
        self._scope["method"] = self._parser.get_method().decode()
        parsed_url = self._server.parser_url(url)
        self._scope["raw_path"] = parsed_url.path
        path = parsed_url.path.decode("ascii")
        if "%" in path:
            path = unquote(path)
        self._scope["path"] = path
        self._scope["query_string"] = parsed_url.query or b""

    def on_header(self, name: bytes, value: bytes):
        self._headers.append((name, value))

    def on_headers_complete(self):
        self._transport.pause_reading()
        self._server._loop.create_task(
            self._server.handler(self._scope, self._receiver, self._sender)
        )

    def on_body(self, body: bytes):
        self._body_future.set_result(body)

    async def _receiver(self):
        self._transport.resume_reading()
        return {
            "type": "http.request",
            "body": await self._body_future,
        }

    def connection_lost(self, exc):
        if not self._body_future.done():
            self._body_future.set_result(b"")

    def on_message_begin(self):
        pass  # logger.info('on_message_begin')

    def on_message_complete(self):
        pass  # logger.info('on_message_complete')

    def on_chunk_header(self):
        pass  # logger.info('on_chunk_header')

    def on_chunk_complete(self):
        pass  # logger.info('on_chunk_complete')
