import os

import aioredis

from aioworkers.app import Application


class Application(Application):
    async def init(self):
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        self['redis_pool'] = await aioredis.create_pool((redis_host, 6379), loop=self.loop)
