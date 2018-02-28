from aioworkers.core.config import MergeDict
from aioworkers.core.context import Context
from aioworkers.worker.updater import BaseUpdater


async def test_1(loop):
    config = MergeDict(
        name='',
        autorun=False,
        cmd='',
    )
    context = Context(config, loop=loop)
    worker = BaseUpdater(config, context=context, loop=loop)
    await worker.init()
