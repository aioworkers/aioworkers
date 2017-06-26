import asyncio

from aioworkers.core import interact


async def test_shell(mocker, loop):
    def MockThread(target):
        target()
        return mocker.Mock()

    mocker.patch('asyncio.new_event_loop', lambda: loop)
    mocker.patch('asyncio.set_event_loop')
    mocker.patch.object(interact, 'Thread', MockThread)
    mocker.patch.object(interact, 'embed')
    mocker.patch('concurrent.futures.Future.result')
    interact.shell(mocker.Mock)

    context = mocker.Mock(loop=loop)
    interact._await(1, context)
    await asyncio.sleep(0)
