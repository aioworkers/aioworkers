import functools
import logging
import typing

from aioworkers.core.plugin import search_plugins

logger = logging.getLogger(__name__)

ASGIApp = typing.Callable[..., typing.Awaitable[None]]


class AsgiMiddleware:
    def __init__(self, app: ASGIApp, plugin: str = '', context=...):
        self.app = app
        self._plugin = plugin
        if context is ...:
            from aioworkers import cli

            self.context = cli.context
        else:
            self.context = context

    async def __call__(self, scope, receive, send):
        extension = {'context': self.context}
        scope.setdefault('extensions', {}).setdefault('aioworkers', extension)
        if scope['type'] == 'lifespan':
            receive = functools.partial(
                self.lifespan,
                receive=receive,
                send=send,
            )
            try:
                await self.app(scope, receive, send)
            except Exception:
                while True:
                    msg = await receive()
                    if msg['type'] == 'lifespan.startup':
                        await send({'type': 'lifespan.startup.complete'})
                    elif msg['type'] == 'lifespan.shutdown':
                        await send({'type': 'lifespan.shutdown.complete'})
                        break
        else:
            await self.app(scope, receive, send)

    async def lifespan(self, receive, send):
        message = await receive()
        message_type = message['type']
        if message_type == 'lifespan.startup':
            try:
                await self.startup()
            except Exception:
                self.context.logger.error('Startup error')
                await send({'type': 'lifespan.startup.failed'})
        elif message_type == 'lifespan.shutdown':
            try:
                await self.shutdown()
            except Exception:
                self.context.logger.error('Shutdown error')
        return message

    async def startup(self):
        plugins = search_plugins()
        if self._plugin:
            plugins.extend(search_plugins(self._plugin, force=True))
        if self.context:
            for p in plugins:
                self.context.config.load(*p.configs)
                self.context.config.update(p.get_config())
            self.context.http = self
            await self.context.__aenter__()

    async def shutdown(self):
        if self.context:
            await self.context.__aexit__(None, None, None)
