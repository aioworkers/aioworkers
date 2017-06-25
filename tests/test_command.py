from aioworkers.core.command import run
from aioworkers.core.config import MergeDict
from aioworkers.core.context import Context


async def coro(context):
    return context.a.b


def test_run(loop):
    config = MergeDict()
    config['a.b'] = 2
    with Context(config, loop=loop) as ctx:
        run('time.time', ctx)
        assert run('a.b', ctx) == 2
        assert run('tests.test_command.coro', ctx) == 2
