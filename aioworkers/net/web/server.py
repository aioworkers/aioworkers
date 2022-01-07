import time
from email.utils import formatdate
from typing import Awaitable, Callable, Dict, Mapping

from aioworkers.core.config import ValueExtractor
from aioworkers.net.server import SocketServer
from aioworkers.net.uri import URL
from aioworkers.worker.base import Worker

from . import access_logger
from .protocol import Protocol


class WebServer(SocketServer, Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._servers = []
        self.headers: Dict[bytes, bytes] = {}

    def set_config(self, config: ValueExtractor):
        config = config.new_parent(
            sleep=1,
            autorun=True,
            persist=True,
        )
        super().set_config(config)

    async def init(self):
        await super().init()
        self._handler = self.context.get_object(
            self.config.get('handler', '.app.handler'))
        self.request_factory = self.context.get_object(
            self.config.get('request', 'aioworkers.net.web.request.Request'))
        self.parser_factory = self.context.get_object(
            self.config.get('parser', 'httptools.HttpRequestParser')
        )
        self.parser_url = self.context.get_object(
            self.config.get('parser_url', 'httptools.parse_url')
        )
        self.url = URL('http://{host}:{port}/'.format_map(self.config))

    async def start(self):
        await super().start()
        factory = Protocol.factory(server=self)
        for sock in self._sockets:
            server = await self.loop.create_server(factory, sock=sock)
            self._servers.append(server)

    async def stop(self, force=True):
        await super().stop(force=force)
        while self._servers:
            server = self._servers.pop()
            server.close()
            await server.wait_closed()

    async def handler(
        self,
        scope: Mapping,
        receive: Callable[[], Awaitable],
        send: Callable[[Mapping], Awaitable],
    ):
        try:
            await self._handler(scope, receive, send)
        except Exception:
            await send(
                {
                    'type': 'http.response.start',
                    'status': 500,
                    'reason': 'Internal error',
                }
            )
            await send(
                {
                    'type': 'http.response.body',
                }
            )
            self.logger.exception('Server error:')
        else:
            access_logger.info(
                "Received request %s %s?%s",
                scope['method'],
                scope['path'],
                scope['query_string'].decode(),
            )

    async def run(self, value=None):  # type: ignore
        self.headers[b'Date'] = formatdate(time.time(), usegmt=True).encode()
