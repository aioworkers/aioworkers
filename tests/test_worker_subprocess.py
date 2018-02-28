import pytest

from aioworkers import utils
from aioworkers.core.config import MergeDict
from aioworkers.core.context import Context
from aioworkers.worker.subprocess import Subprocess


async def test_autorun(loop):
    config = MergeDict(
        cls=utils.import_uri(Subprocess),
        autorun=True,
        sleep=1,
        cmd='echo',
    )
    async with Context(dict(a=config), loop=loop) as context:
        await context.a._future
        assert not context.a.running()
        assert context.a._started_at


async def test_daemon(loop):
    config = MergeDict(
        cls=utils.import_uri(Subprocess),
        autorun=True,
        daemon=True,
        cmd='echo',
    )
    async with Context(dict(a=config), loop=loop) as context:
        pass


@pytest.mark.parametrize('cmd', ['time.time', ['time.time']])
async def test_aioworkers(loop, cmd):
    config = MergeDict(
        cls=utils.import_uri(Subprocess),
        autorun=True,
        aioworkers=cmd,
    )
    async with Context(dict(a=config), loop=loop) as context:
        pass
