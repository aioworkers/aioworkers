import asyncio


async def run(worker, *args, **kwargs):
    await asyncio.sleep(1)
    worker.logger.info(args)
    return 'pong'
