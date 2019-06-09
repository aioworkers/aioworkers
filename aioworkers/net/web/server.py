from ...core.base import AbstractNamedEntity
from ...http import URL
from ..server import SocketServer
from . import access_logger
from .exceptions import HttpException
from .protocol import Protocol


class WebServer(SocketServer, AbstractNamedEntity):
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
            self.config.get('parser', 'httptools.HttpRequestParser'))
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

    async def handler(self, request):
        try:
            result = await self._handler(request)
            request.response(result)
        except HttpException as e:
            request.response(e, status=500)
            self.logger.exception('Server error:')
        except Exception:
            request.response(b'Internal error', status=500)
            self.logger.exception('Server error:')
        else:
            access_logger.info(
                "Received request %s %s",
                request.method,
                request.url,
            )
        request.transport.close()
