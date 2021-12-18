import pytest

from aioworkers.core.config import Config
from aioworkers.core.context import Context


async def test_autorun(loop):
    config = Config(
        a=dict(
            cls='aioworkers.worker.subprocess.Subprocess',
            autorun=True,
            sleep=1,
            cmd='echo',
        )
    )
    async with Context(config, loop=loop) as context:
        await context.a._future
        assert not context.a.running()
        assert context.a._started_at


async def test_daemon(loop):
    config = Config(
        a=dict(
            cls='aioworkers.worker.subprocess.Subprocess',
            autorun=True,
            daemon=True,
            cmd='echo',
        )
    )
    async with Context(config, loop=loop):
        pass


@pytest.mark.parametrize('cmd', ['time.time', ['time.time']])
async def test_aioworkers(loop, cmd):
    config = Config(
        a=dict(
            cls='aioworkers.worker.subprocess.Subprocess',
            autorun=True,
            aioworkers=cmd,
        )
    )
    async with Context(config, loop=loop):
        pass
