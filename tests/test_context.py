import asyncio

import pytest

from aioworkers.core.config import Config, MergeDict
from aioworkers.core.context import (
    Context,
    EntityContextProcessor,
    GroupResolver,
    Octopus,
    Signal,
)
from aioworkers.queue.timeout import TimestampQueue


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
    assert f.extended_repr(header=True)
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


async def test_context_items(event_loop):
    f = Context({}, loop=event_loop)
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


async def test_context_create(event_loop):
    conf = Config()
    conf.update(
        MergeDict(
            {
                'q.cls': 'aioworkers.queue.timeout.TimestampQueue',
                'f.e': 1,
            }
        )
    )
    c = Context(conf, loop=event_loop)
    await c.init()
    assert c.config.f.e == 1
    with pytest.raises(AttributeError):
        c.r
    with pytest.raises(KeyError):
        c['r']

    async def handler_empty(context):
        pass

    c.on_connect.append(handler_empty)

    async def handler_sleep_2():
        await asyncio.sleep(2)

    c.on_connect.append(handler_sleep_2)

    def handler_sync():
        raise ValueError

    c.on_connect.append(handler_sync)

    async def handler_raise_value():
        raise ValueError

    c.on_connect.append(handler_raise_value)
    c.on_connect.append(handler_raise_value())

    with pytest.raises((ValueError, TimeoutError)):
        await c.on_connect.send(c._group_resolver, timeout=0.1)

    def handler_sync():
        raise ValueError

    c.on_stop.append(handler_sync)
    c.on_stop.append(1)

    # raise from sync handler
    with pytest.raises(ValueError):
        c.on_stop.send(c._group_resolver, coroutine=False)


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


async def test_signal(event_loop):
    gr = GroupResolver()
    context = Context({}, loop=event_loop, group_resolver=gr)
    s = Signal(context)
    s.append(1, ('1',))
    s.append(1)
    await s.send(gr)
    await s.send(GroupResolver(all_groups=True))


async def test_func(event_loop):
    config = MergeDict(
        now={
            'func': 'time.monotonic',
        }
    )
    context = Context(config, loop=event_loop)
    async with context:
        assert isinstance(context.now, float)


def test_create_entity():
    with pytest.raises((ValueError, TypeError)):
        EntityContextProcessor(None, 'x', {'cls': 'time.time'})
    with pytest.raises(TypeError):
        EntityContextProcessor(None, 'x', {'cls': 'aioworkers.humanize.size'})


async def test_precreate_entity():
    async with Context(queue=TimestampQueue()) as ctx:
        assert isinstance(ctx.queue, TimestampQueue)


async def test_get_object():
    async with Context(
        {
            "a": 1,
            "x": {
                "y": {
                    "groups": ["a"],
                }
            },
        },
        q=TimestampQueue(),
    ) as ctx:
        assert ctx.get_object(".q") is not None

        assert ctx.get_object(".a")

        with pytest.raises(RuntimeError):
            assert ctx.get_object(".x.y")

        with pytest.raises(KeyError):
            assert ctx.get_object(".x.x")

        assert pytest is ctx.get_object("pytest")
