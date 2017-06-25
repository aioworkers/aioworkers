import pytest

from aioworkers.core.command import run, CommandNotFound
from aioworkers.core.config import MergeDict
from aioworkers.core.context import Context


async def coro(context, j: int=5):
    return context.a.b


def test_run(loop):
    config = MergeDict()
    config['a.b'] = 2
    config['c'] = 'a.b'
    config['d'] = 's'
    with Context(config, loop=loop) as ctx:
        run('time.time', ctx)
        assert run('a.b', ctx) == 2
        assert run('c', ctx) == 2
        assert run('tests.test_command.coro', ctx) == 2
        assert run('d', ctx) == 's'
        with pytest.raises(CommandNotFound):
            run('not found', ctx)
        with pytest.raises(CommandNotFound):
            run('time.time2', ctx)
