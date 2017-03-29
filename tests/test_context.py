import pytest

from aioworkers.core.config import MergeDict
from aioworkers.core.context import Octopus, Context


def test_octopus():
    f = Octopus()
    f.r = 1
    assert f['r'] == 1
    f['g'] = 2
    assert f.g == 2
    f['y.t'] = 3
    assert f.y.t == 3
    f['d.w.f'] = 4
    assert dir(f)
    assert repr(f)
    assert f.__repr__(header=True)
    assert f.items()

    f[None] = True
    assert not f[None]


async def test_context_items(loop):
    f = Context({}, loop=loop)
    f.r = 1
    assert f['r'] == 1
    f['g'] = 2
    assert f.g == 2
    f['y.t'] = 3
    assert f.y.t == 3
    f['d.w.f'] = 4
    assert dir(f)
    assert repr(f)
    await f.stop()


async def test_context_create(loop):
    c = Context(MergeDict({
        'q.cls': 'aioworkers.queue.timeout.TimestampQueue',
        'f.e': 1,
        'app.cls': 'aioworkers.app.Application',
    }), loop=loop)
    await c.init()
    await c.start()
    assert c.f.e == 1
    with pytest.raises(AttributeError):
        c.r
    with pytest.raises(KeyError):
        c['r']
    c[{'func': 'time.time'}]

    async def handler(app):
        pass
    c.on_stop.append(handler)

    async def handler(context):
        pass
    c.on_stop.append(handler)

    async def handler():
        raise ValueError
    c.on_stop.append(handler)
    c.on_stop.append(handler())

    c.on_stop.append(1)

    await c.stop()
