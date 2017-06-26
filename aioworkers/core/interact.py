import asyncio
import concurrent.futures
from functools import partial
from threading import Thread

from IPython import embed


def _await(coro, context):
    f = concurrent.futures.Future()
    async def wrap(coro):
        try:
            result = await coro
        except Exception as e:
            f.set_exception(e)
        else:
            f.set_result(result)
    context.loop.call_soon_threadsafe(
        context.loop.create_task, wrap(coro)
    )
    return f.result()


def _shell(context):
    await = partial(_await, context=context)
    embed()


def shell(run):
    f = concurrent.futures.Future()

    def _thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        run(loop=loop, future=f)

    thread = Thread(target=_thread)
    thread.start()
    context = f.result()
    _shell(context)
    context.loop.stop()
    thread.join()
