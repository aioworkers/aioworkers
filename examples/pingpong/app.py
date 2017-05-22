import os
import asyncio

import aioredis

from aioworkers.app import Application


class Application(Application):
    async def init(self):
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        self['redis_pool'] = await aioredis.create_pool((redis_host, 6379), loop=self.loop)


async def run(worker, *args, **kwargs):
    worker.logger.info(args)
    await asyncio.sleep(1)
    return worker.name


async def start(worker, *args, **kwargs):
    worker.logger.info('Start')
    with await worker.context.app['redis_pool'] as redis:
        await redis.lpush(worker.context.config.queues.ping.key, 'start')
