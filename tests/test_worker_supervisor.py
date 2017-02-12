from aioworkers.core.config import MergeDict
from aioworkers.core.context import Context
from aioworkers.worker.supervisor import Supervisor


async def test_autorun(loop):
    config = MergeDict(
        name='',
        autorun=True,
        children=1,
        child={
            'cls': 'aioworkers.worker.base.Worker',
        },
    )
    context = Context(config, loop=loop)
    worker = Supervisor(config, context=context, loop=loop)
    await worker.init()
    await context.start()
    await worker._future
    assert worker._started_at
    assert not worker.running()
    await worker.stop()
    assert await worker.status()
