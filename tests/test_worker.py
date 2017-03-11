import asyncio

import pytest

from aioworkers.core.config import MergeDict
from aioworkers.core.context import Context
from aioworkers.worker.base import Worker


async def test_autorun(loop):
    config = MergeDict(name='', autorun=True)
    context = Context(config, loop=loop)
    worker = Worker(config, context=context, loop=loop)
    await worker.init()
    await context.start()
    await worker._future
    assert worker._started_at
    assert not worker.running()


async def test_coro_run(loop, mocker):
    f = loop.create_future()
    async def myrun(*args, **kwargs):
        f.set_result(10)

    config = MergeDict(
        name='',
        autorun=True,
        run='mocked.run',
    )
    context = Context(config, loop=loop)
    worker = Worker(config, context=context, loop=loop)
    mocker.patch('aioworkers.worker.base.import_name',
                 lambda x: myrun)
    await worker.init()
    await context.start()
    assert worker._started_at
    await worker._future
    assert worker._stopped_at
    assert f.result() == 10


async def test_stop(loop, mocker):
    config = MergeDict(
        name='',
        autorun=True,
        persist=True,
        sleep=0.01,
        sleep_start=0.01,
    )
    context = Context(config, loop=loop)
    worker = Worker(config, context=context, loop=loop)
    await worker.init()
    await context.start()
    await asyncio.sleep(0.1, loop=loop)
    await worker.stop()
    assert not worker.running()
    assert isinstance(await worker.status(), dict)


async def test_crontab(loop, mocker):
    config = MergeDict(
        name='',
        autorun=True,
        persist=True,
        crontab='*/1 * * * *',
    )
    context = Context(config, loop=loop)
    worker = Worker(config, context=context, loop=loop)
    await worker.init()
    await context.start()
    await asyncio.sleep(0.1, loop=loop)
    await worker.stop()
    assert not worker.running()
