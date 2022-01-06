from typing import Awaitable, Callable, Mapping

from aioworkers.net.server import SocketServer
from aioworkers.net.uri import URL

from . import access_logger
from .protocol import Protocol


class WebServer(SocketServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._servers = []

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
        self.context.on_start.append(self.start)
        self.context.on_stop.append(self.stop)
        self.url = URL('http://{host}:{port}/'.format_map(self.config))

    async def start(self):
        factory = Protocol.factory(server=self)
        for sock in self._sockets:
            server = await self.loop.create_server(factory, sock=sock)
            self._servers.append(server)

    async def stop(self):
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
