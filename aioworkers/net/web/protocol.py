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

from .headers import CONNECTION, CONTENT_LENGTH

if TYPE_CHECKING:  # pragma: no cover
    from .server import WebServer
else:
    WebServer = Any

logger = logging.getLogger(__name__)

HEADER_CONNECTION = frozenset((CONNECTION.lower(), CONNECTION))
HEADERS_LOWER: Mapping[bytes, bytes] = {
    CONNECTION.lower(): CONNECTION,
    CONTENT_LENGTH.lower(): CONTENT_LENGTH,
}


class ASGIResponseSender:
    SERVER = b"\r\nServer: aioworkers\r\n"
    KEEP_ALIVE = b"keep-alive"
    CLOSE = b"close"
    SEP = b"\r\n"
    SET = b": "
    status_reason: Mapping[int, bytes] = {
        200: b"OK",
        404: b"Not found",
        405: b"Method not allowed",
    }

    def __init__(
        self,
        transport: asyncio.Transport,
        server: WebServer,
        scope: Dict,
    ):
        self._transport = transport
        self._server = server
        self._scope = scope
        self._status: int = 200
        self._reason: bytes = b""
        self._headers: Sequence[Tuple[bytes, bytes]] = ()
        self._started: bool = False
        self._handlers = {
            "http.response.start": self._response_start,
            "http.response.body": self._response_body,
        }

    def _response_start(self, message: Mapping) -> None:
        self._status = message["status"]
        self._reason = message.get("reason", "").encode("utf-8")
        if not self._reason:
            self._reason = self.status_reason.get(self._status, self._reason)
        self._headers = message.get("headers", self._headers)

    def _response_body(self, message: Mapping) -> None:
        body = message.get("body", b"")
        more_body = message.get("more_body", False)
        close = False
        if not self._started:
            http_version: str = self._scope["http_version"]

            vec: List[bytes] = [
                b"HTTP/",
                f"{http_version} {self._status} ".encode("utf-8"),
                self._reason,
                self.SERVER,
            ]
            headers: Dict[bytes, bytes] = self._server.headers.copy()

            if more_body:
                close = True
            elif body:
                headers[CONTENT_LENGTH] = str(len(body)).encode("utf-8")
            if not close:
                for name, value in self._scope["headers"]:
                    if name in HEADER_CONNECTION:
                        if value == self.KEEP_ALIVE:
                            headers[CONNECTION] = value
                        else:
                            headers[CONNECTION] = self.CLOSE
                            close = True
                        break
                else:
                    if http_version == "1.0":
                        close = True
                    else:
                        headers.setdefault(CONTENT_LENGTH, b"0")

            for h, v in self._headers:
                headers[HEADERS_LOWER.get(h, h)] = v

            for name, value in headers.items():
                vec.extend((name, self.SET, value, self.SEP))
            vec.append(self.SEP)
            if body:
                vec.append(body)
            body = b"".join(vec)

            self._started = True

        if body:
            self._transport.write(body)

        if more_body:
            pass
        elif not close:
            self._transport.resume_reading()
        elif self._transport.can_write_eof():
            self._transport.write_eof()
        else:
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
        self._body_future = server.loop.create_future()

    @classmethod
    def factory(cls, **kwargs):
        return partial(cls, **kwargs)

    def connection_made(self, transport):
        self._transport = transport

    def data_received(self, data):
        try:
            self._parser.feed_data(data)
        except Exception as e:
            logger.exception("Request feed error")
            self._sender._response_start(
                dict(
                    status=500,
                    reason=str(e),
                )
            )
            self._sender._response_body({})
            if self._transport.can_write_eof():
                self._transport.write_eof()
            else:
                self._transport.close()

    def on_message_begin(self):
        if self._body_future.done():
            self._body_future = self._server.loop.create_future()
        self._headers = []
        self._scope = {
            "type": "http",
            "http_version": "1.1",
            "asgi": {"version": "3.0", "spec_version": "2.1"},
            "scheme": "http",
            "headers": self._headers,
        }
        self._sender = ASGIResponseSender(self._transport, self._server, self._scope)

    def on_url(self, url: bytes):
        self._scope["method"] = self._parser.get_method().decode("utf-8")
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
        self._scope["http_version"] = self._parser.get_http_version()
        self._server._loop.create_task(self._server.handler(self._scope, self._receiver, self._sender))

    def on_body(self, body: bytes):
        self._body_future.set_result(body)

    async def _receiver(self):
        return {
            "type": "http.request",
            "body": await self._body_future,
        }

    def on_message_complete(self):
        if not self._body_future.done():
            self._body_future.set_result(b"")
        self._transport.pause_reading()

    def connection_lost(self, exc):
        if exc is None:
            if not self._body_future.done():
                self._body_future.set_result(None)
            self._transport.close()
        elif not self._body_future.done():
            self._body_future.set_exception(exc)

    def on_chunk_header(self):  # no cov
        pass  # logger.info('on_chunk_header')

    def on_chunk_complete(self):  # no cov
        pass  # logger.info('on_chunk_complete')
