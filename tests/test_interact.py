import asyncio

from aioworkers.core import interact


async def test_shell(mocker, loop):
    def MockThread(target):
        target()
        return mocker.Mock()
    context = mocker.Mock(loop=loop)

    mocker.patch.object(interact, 'Thread', MockThread)
    mocker.patch.object(
        interact, '_shell',
        lambda *args, **kwargs: interact._await(asyncio.coroutine(lambda: 1),
                                                context=context))
    mocker.patch('concurrent.futures.Future.result')

    def run(future):
        future.set_result(context)

    interact.shell(run)

    await asyncio.sleep(0)
