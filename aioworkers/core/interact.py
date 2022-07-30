import asyncio
import concurrent.futures
from functools import partial
from threading import Thread
from typing import Dict


def _await(coro, context):
    f: concurrent.futures.Future = concurrent.futures.Future()

    async def wrap(coro):
        try:
            result = await coro
        except Exception as e:
            f.set_exception(e)
        else:
            f.set_result(result)

    context.loop.call_soon_threadsafe(
        context.loop.create_task,
        wrap(coro),
    )
    return f.result()


def shell(run):
    import prompt_toolkit

    if int(prompt_toolkit.__version__.split('.', 1)[0]) < 3:
        from IPython.terminal.embed import InteractiveShellEmbed

        shell = InteractiveShellEmbed.instance()
        _f: concurrent.futures.Future = concurrent.futures.Future()

        def _thread():
            context = _f.result()
            locals()['await'] = partial(_await, context=context)
            shell(
                header=(
                    'Welcome to interactive mode of aioworkers. \n'
                    'You available the main context and '
                    'the await function to perform coroutine.'
                )
            )
            return locals()['await'](asyncio.coroutine(context.loop.stop)())

        thread = Thread(target=_thread)
        thread.start()
        run(future=_f)
    else:
        from IPython import embed

        class PseudoFuture:
            def set_result(self, context):
                embed(using='asyncio')
                context.loop.stop()

        run(future=PseudoFuture())


def kernel(run):
    from ipykernel import kernelapp
    from tornado import ioloop

    io_loop = ioloop.IOLoop.current()
    setattr(io_loop, 'start', lambda: None)  # without run_forever

    kernelapp._ctrl_c_message = 'IPKernelApp running'

    app = kernelapp.IPKernelApp.instance()
    app.initialize(['aioworkers'])
    namespace: Dict = {}
    app.kernel.user_ns = namespace

    class PseudoFuture:
        def set_result(self, value):
            namespace['context'] = value
            app.start()

    run(future=PseudoFuture())
