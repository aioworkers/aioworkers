"""DEPRECATED module"""
import asyncio


class BaseApplication:
    def __init__(self, config, *, context, **kwargs):
        self.config = config
        self.context = context

    @classmethod
    async def prepare(cls, kwargs):
        return kwargs

    async def init(self):
        pass

    @classmethod
    async def factory(cls, **kwargs):
        kwargs = await cls.prepare(kwargs)
        app = cls(**kwargs)
        await app.init()
        return app


class Application(BaseApplication, dict):
    def __init__(self, config, *, loop, context, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        self.loop = loop
        self.on_startup = []
        self.on_shutdown = []
        super().__init__(config=config, context=context)

    def run_forever(self, print=print, **kwargs):
        loop = self.loop

        print("======== Running aioworkers ========\n"
              "(Press CTRL+C to quit)")

        try:
            if self.on_startup:
                on_startup = [coro(self) for coro in self.on_startup]
                loop.run_until_complete(asyncio.wait(on_startup))

            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            if self.on_shutdown:
                on_shutdown = [coro(self) for coro in self.on_shutdown]
                loop.run_until_complete(asyncio.wait(on_shutdown))
        loop.close()
