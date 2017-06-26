from argparse import Namespace

import pytest

from aioworkers.core.command import run, CommandNotFound
from aioworkers.core.config import MergeDict
from aioworkers.core.context import Context


async def coro(context, j: int=5):
    return context.a.b


def test_run(loop):
    ns = Namespace()
    config = MergeDict()
    config['a.b'] = 2
    config['c'] = 'a.b'
    config['d'] = 's'
    with Context(config, loop=loop) as ctx:
        run('time.time', ctx, ns=ns)
        assert run('a.b', ctx, ns=ns) == 2
        assert run('c', ctx, ns=ns) == 2
        assert run('tests.test_command.coro', ctx, ns=ns) == 2
        assert run('d', ctx, ns=ns) == 's'
        with pytest.raises(CommandNotFound):
            run('not found', ctx, ns=ns)
        with pytest.raises(CommandNotFound):
            run('time.time2', ctx, ns=ns)
