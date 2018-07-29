import asyncio
import io
import logging
from functools import partial

from ...http import URL

logger = logging.getLogger(__name__)


class Protocol(asyncio.Protocol):
    def __init__(self, server):
        self._server = server

    @classmethod
    def factory(cls, **kwargs):
        return partial(cls, **kwargs)

    def connection_made(self, transport):
        self._transport = transport
        self._parser = self._server.parser_factory(self)
        self._headers = []
        self._body = None

    def data_received(self, data):
        try:
            self._parser.feed_data(data)
        except Exception:
            self._server.request_factory(
                transport=self._transport, url=None, method=None,
            ).response(status=500)

    def on_url(self, url: bytes):
        self._url = URL(url.decode())

    def on_header(self, name: bytes, value: bytes):
        self._headers.append((name.decode(), value.decode()))

    def on_headers_complete(self):
        self._transport.pause_reading()
        request = self._server.request_factory(
            url=self._url,
            method=self._parser.get_method().decode(),
            headers=self._headers,
            transport=self._transport,
        )
        self._server._loop.create_task(self._server.handler(request))

    def on_body(self, body: bytes):
        self._body = io.BytesIO(body)

    def on_message_begin(self):
        pass  # logger.info('on_message_begin')

    def on_message_complete(self):
        pass  # logger.info('on_message_complete')

    def on_chunk_header(self):
        pass  # logger.info('on_chunk_header')

    def on_chunk_complete(self):
        pass  # logger.info('on_chunk_complete')
