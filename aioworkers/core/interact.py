import asyncio
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


def shell(run):
    from IPython.terminal.embed import InteractiveShellEmbed
    shell = InteractiveShellEmbed.instance()
    _f = concurrent.futures.Future()

    def _thread():
        context = _f.result()
        locals()['await'] = partial(_await, context=context)
        shell(
            header='Welcome to interactive mode of aioworkers. \n'
                   'You available the main context and '
                   'the await function to perform coroutine.')
        return locals()['await'](asyncio.coroutine(context.loop.stop)())

    thread = Thread(target=_thread)
    thread.start()
    run(future=_f)


def kernel(run):
    from ipykernel import kernelapp
    from tornado import ioloop

    io_loop = ioloop.IOLoop.current()
    io_loop.start = lambda: None  # without run_forever

    kernelapp._ctrl_c_message = 'IPKernelApp running'

    app = kernelapp.IPKernelApp.instance()
    app.initialize(['aioworkers'])
    namespace = {}
    app.kernel.user_ns = namespace

    class PseudoFuture:
        def set_result(self, value):
            namespace['context'] = value
            app.start()

    run(future=PseudoFuture())
