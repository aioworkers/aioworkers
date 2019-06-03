from argparse import Namespace

import pytest

from aioworkers.core.command import CommandNotFound, run


@pytest.fixture
def config_yaml():
    return """
    a.b: 2
    c: a.b
    d: s
    """


async def coro(context):
    return context.config.a.b


def test_run(context):
    ns = Namespace()
    run('time.time', context, ns=ns, argv=[])
    assert run('a.b', context, ns=ns, argv=[]) == 2
    assert run('c', context, ns=ns, argv=[]) == 2
    assert run('tests.test_command.coro', context, ns=ns, argv=[]) == 2
    assert run('d', context, ns=ns, argv=[]) == 's'
    with pytest.raises(CommandNotFound):
        run('not found', context, ns=ns, argv=[])
    with pytest.raises(CommandNotFound):
        run('time.time2', context, ns=ns, argv=[])
