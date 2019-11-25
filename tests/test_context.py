import pytest

from aioworkers.core.config import Config, MergeDict
from aioworkers.core.context import (Context, EntityContextProcessor,
                                     GroupResolver, Octopus, Signal)


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
    f.s = 'w'
    assert callable(f['s.upper'])
    assert f['s.upper']() == 'W'

    f[None] = True
    assert not f[None]


def test_octopus_iter():
    f = Octopus()
    f.r = 1
    assert f['r'] == 1
    f['g'] = 2
    assert f.g == 2
    f['y.t'] = 3
    assert f.y.t == 3
    f['d.w.f'] = 4
    assert list(f.find_iter(int))
    f['d.f'] = f
    assert list(f.find_iter(int))


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
    conf = Config()
    conf.update(MergeDict({
        'q.cls': 'aioworkers.queue.timeout.TimestampQueue',
        'f.e': 1,
    }))
    c = Context(conf, loop=loop)
    await c.init()
    await c.start()
    assert c.config.f.e == 1
    with pytest.raises(AttributeError):
        c.r
    with pytest.raises(KeyError):
        c['r']

    async def handler(context):
        pass
    c.on_stop.append(handler)

    async def handler():
        raise ValueError
    c.on_stop.append(handler)
    c.on_stop.append(handler())

    c.on_stop.append(1)

    await c.stop()


def test_group_resolver():
    gr = GroupResolver()
    assert not gr.match(['1'])
    assert gr.match(None)

    gr = GroupResolver(all_groups=True)
    assert gr.match(['1'])
    assert gr.match(None)

    gr = GroupResolver(default=False)
    assert not gr.match(['1'])
    assert not gr.match(None)

    gr = GroupResolver(exclude=['1'])
    assert not gr.match(['1'])
    assert not gr.match(['1', '2'])
    assert gr.match(None)

    gr = GroupResolver(exclude=['1'], all_groups=True)
    assert not gr.match(['1'])
    assert not gr.match(['1', '2'])
    assert gr.match(None)

    gr = GroupResolver(include=['1'])
    assert gr.match(['1'])
    assert gr.match(None)


async def test_signal(loop):
    gr = GroupResolver()
    context = Context({}, loop=loop, group_resolver=gr)
    s = Signal(context)
    s.append(1, ('1',))
    s.append(1)
    await s.send(gr)
    await s.send(GroupResolver(all_groups=True))


async def test_func(loop):
    config = MergeDict(
        now={
            'func': 'time.monotonic',
        }
    )
    context = Context(config, loop=loop)
    async with context:
        assert isinstance(context.now, float)


def test_create_entity():
    with pytest.raises(ValueError):
        EntityContextProcessor(None, 'x', {'cls': 'time.time'})
    with pytest.raises(TypeError):
        EntityContextProcessor(None, 'x', {'cls': 'aioworkers.humanize.size'})
