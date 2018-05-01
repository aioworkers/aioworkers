import asyncio

from aioworkers.core import interact


async def coro_1():
    return 1


async def coro_2():
    raise RuntimeError


async def test_await(mocker, loop):
    mocker.patch('concurrent.futures.Future.result')
    fs = set()
    context = mocker.Mock()
    context.loop.call_soon_threadsafe = lambda f, arg: fs.add(arg)
    interact._await(coro_1(), context)
    interact._await(coro_2(), context)
    await asyncio.wait(fs, loop=loop)


async def test_shell(mocker, loop):
    def MockThread(target):
        target()
        return mocker.Mock()
    context = mocker.Mock(loop=loop)
    fs = set()

    mocker.patch.object(interact, 'Thread', MockThread)
    mocker.patch.object(loop, 'call_soon_threadsafe', lambda f, arg: fs.add(arg))
    mocker.patch('concurrent.futures.Future.result')
    mocker.patch('IPython.terminal.embed.InteractiveShellEmbed')

    def run(future):
        future.set_result(context)

    interact.shell(run)


async def test_kernel(mocker, loop):
    mocker.patch('ipykernel.kernelapp.IPKernelApp')

    def run(future):
        future.set_result(1)

    interact.kernel(run)
