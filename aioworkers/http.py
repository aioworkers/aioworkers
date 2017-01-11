import asyncio

from aiohttp import web

from .app import BaseApplication


class Application(BaseApplication, web.Application):
    def __init__(self, *, config, context, **kwargs):
        if kwargs.get('loop') is None:
            kwargs['loop'] = asyncio.get_event_loop()
        web.Application.__init__(self, **kwargs)
        BaseApplication.__init__(
            self, config=config, context=context, **kwargs)

    def run_forever(self, **kwargs):
        web.run_app(self, **kwargs)
