import asyncio
import concurrent.futures
from functools import partial
from threading import Thread

from IPython.terminal.embed import InteractiveShellEmbed

_shell = InteractiveShellEmbed.instance()


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


def shell(run):
    _f = concurrent.futures.Future()

    def _thread():
        context = _f.result()
        await = partial(_await, context=context)
        _shell(
            header='Welcome to interactive mode of aioworkers. \n'
                   'You available the main context and '
                   'the await function to perform coroutine.')
        return await(asyncio.coroutine(context.loop.stop)())

    thread = Thread(target=_thread)
    thread.start()
    run(future=_f)
