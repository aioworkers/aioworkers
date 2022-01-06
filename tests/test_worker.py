import asyncio

import pytest

from aioworkers.core.config import Config
from aioworkers.core.context import Context
from aioworkers.worker.base import Worker


async def test_autorun(loop):
    config = Config(w=dict(cls='aioworkers.worker.base.Worker', autorun=True))
    async with Context(config, loop=loop) as context:
        worker = context.w
        await worker._future
        assert worker._started_at
        assert not worker.running()


async def test_coro_run(loop, mocker):
    f = loop.create_future()

    async def myrun(*args, **kwargs):
        f.set_result(10)

    mocker.patch(
        'aioworkers.worker.base.import_name',
        lambda x: myrun,
    )

    config = Config(
        w=dict(
            cls='aioworkers.worker.base.Worker',
            autorun=True,
            run='mocked.run',
        )
    )
    async with Context(config, loop=loop) as context:
        worker = context.w
        assert worker._started_at
        await worker._future
        assert worker._stopped_at
        assert f.result() == 10


async def test_stop(loop):
    config = Config(
        w=dict(
            cls='aioworkers.worker.base.Worker',
            autorun=True,
            persist=True,
            sleep=0.01,
            sleep_start=0.01,
        )
    )
    async with Context(config, loop=loop) as context:
        worker = context.w
        await asyncio.sleep(0.1)
        await worker.stop()
        assert not worker.running()
        assert isinstance(await worker.status(), dict)


async def test_crontab(loop):
    config = Config(
        w=dict(
            cls='aioworkers.worker.base.Worker',
            persist=True,
            crontab='*/1 * * * *',
        )
    )
    async with Context(config, loop=loop) as context:
        worker = context.w
        await asyncio.sleep(0.1)
        await worker.stop()
        assert not worker.running()


async def test_set_context(loop):
    worker = Worker()
    config = Config(name='')
    context = Context(loop=loop)
    worker.set_config(config)
    worker.set_context(context)
    with pytest.raises(RuntimeError):
        worker.set_context(context)
