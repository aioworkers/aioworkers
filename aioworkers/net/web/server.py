import logging

from ...core.base import AbstractNamedEntity
from ...http import URL
from . import access_logger
from .exceptions import HttpException
from .protocol import Protocol

logger = logging.getLogger(__name__)


class WebServer(AbstractNamedEntity):
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
        self._server = await self.loop.create_server(
            factory, self.config.host, self.config.get_int('port'))

    async def stop(self):
        self._server.close()
        await self._server.wait_closed()

    async def handler(self, request):
        try:
            result = await self._handler(request)
            request.response(result)
        except HttpException as e:
            request.response(e, status=500)
            logger.exception('Server error:')
        except Exception:
            request.response(b'Internal error', status=500)
            logger.exception('Server error:')
        else:
            access_logger.info(
                "Received request %s %s",
                request.method,
                request.url,
            )
        request.transport.close()
