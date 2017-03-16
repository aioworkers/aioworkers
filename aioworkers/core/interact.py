import concurrent.futures
from functools import partial
from threading import Thread


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


class Shell(Thread):
    def run(self):
        from IPython import embed

        context, = self._args
        await = partial(_await, context=context)
        embed()


def shell(context):
    thread = Shell(args=(context,))
    thread.start()
    return thread
