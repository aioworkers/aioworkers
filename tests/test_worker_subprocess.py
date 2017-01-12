from aioworkers.core.config import MergeDict
from aioworkers.core.context import Context
from aioworkers.worker.subprocess import Subprocess


async def test_autorun(loop):
    config = MergeDict(
        autorun=True,
        cmd='echo',
    )
    context = Context(config, loop=loop)
    worker = Subprocess(config, context=context, loop=loop)
    await worker.init()
    await worker._future
    assert worker._started_at
    assert not worker.running()
