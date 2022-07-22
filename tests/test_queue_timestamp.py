import asyncio
import time

import pytest

from aioworkers.queue.timeout import TimestampQueue, UniqueQueue


@pytest.fixture
def config_yaml():
    return """
    q:
      cls: aioworkers.queue.timeout.UniqueQueue
      maxsize: 5
    """


@pytest.mark.timeout(1)
async def test_put_simple(event_loop):
    async with TimestampQueue() as q:
        await q.put(1, 1)
        assert 1 == await q.get()

        t = time.time()
        await q.put(2, t + 0.2)
        await q.put(3, t + 0.3)
        await q.put(1, t + 0.1)
        await asyncio.sleep(0.2)
        assert 1 == await q.get()
        assert 2 == await q.get()
        assert 3 == await q.get()
        assert not q


@pytest.mark.timeout(1)
async def test_put_unique():
    async with UniqueQueue() as q:
        await q.put(1, 1)
        await q.put(1, 2)
        await q.put(1, 3)
        await q.put(2, 3)
        await q.put(2, 2)
        await q.put(2, 1)
        assert 2 == await q.get()
        assert 1 == await q.get()
        assert not q


@pytest.mark.timeout(1)
async def test_timestamp_score():
    async with TimestampQueue() as q:
        await q.put(1)
        a, ts = await q.get(score=True)
        assert a == 1
        assert ts <= time.time()


@pytest.mark.timeout(1)
async def test_timestamp_await():
    async with TimestampQueue() as q:
        f = q.get(score=True)
        t0 = time.time()
        await q.put(1)
        a, ts = await f
        assert a == 1
        assert t0 <= ts <= time.time()


@pytest.mark.timeout(1)
async def test_uniq_score():
    async with UniqueQueue() as q:
        assert q.empty()
        await q.put(1)
        assert not q.empty()
        a, ts = await q.get(score=True)
        assert a == 1
        assert ts <= time.time()


@pytest.mark.timeout(1.3)
async def test_one_second(event_loop):
    async with TimestampQueue(add_score=1) as q:
        await q.put(1)

        start = event_loop.time()
        assert 1 == await q.get()
        diff = event_loop.time() - start
        assert diff > 1


@pytest.mark.timeout(2)
async def test_timeout():
    async with TimestampQueue(add_score=1) as q:
        assert q.empty()
        await q.put(1)
        with pytest.raises(asyncio.TimeoutError):
            await q.get(timeout=0.5)


async def test_many():
    async with UniqueQueue() as q:
        limit = 99
        for _ in range(9):
            for i in range(limit):
                await q.put(i)
        assert len(q) == limit
        c = []
        while q:
            c.append(await q.get(timeout=0.5))
        assert len(c) == limit
        assert len(set(c)) == limit


async def test_with_context(context):
    v = 1
    await context.q.put(v)
    assert v == await context.q.get()


@pytest.mark.timeout(2)
async def test_maxsize(context, event_loop):
    for i in range(9):
        await context.q.put(1)
    assert not context.q.full()
    for i in range(4):
        await context.q.put(i)
    assert not context.q.full()
    f = event_loop.create_task(context.q.put(5))
    await asyncio.sleep(0.1)
    assert context.q.full()
    assert len(context.q) >= 5
    assert not f.done()
    assert 0 == await context.q.get()
    await asyncio.sleep(0.1)
    assert f.done()


@pytest.mark.timeout(2)
async def test_get(context, event_loop):
    f = event_loop.create_task(context.q.get())
    await asyncio.sleep(0.1)
    assert not f.done()
    assert not context.q.full()
    await context.q.put(1)
    await asyncio.sleep(0.1)
    assert f.done()
    assert 1 == await f


@pytest.mark.timeout(2)
async def test_get_cancel_send(context, event_loop):
    f = event_loop.create_task(context.q.get())
    await asyncio.sleep(0.1)
    assert not f.done()
    f.cancel()
    await context.q.put(1)
    await asyncio.sleep(0.1)
    assert 1 == await context.q.get()


@pytest.mark.timeout(2)
async def test_get_cancel_schedule(context, event_loop):
    f = event_loop.create_task(context.q.get())
    await asyncio.sleep(0.1)
    assert not f.done()
    f.cancel()
    await context.q.put(1, time.time() + 0.5)
    await asyncio.sleep(0.1)
    assert 1 == await context.q.get()


@pytest.mark.timeout(2)
async def test_send_score(context, event_loop):
    f = event_loop.create_task(context.q.get(score=True))
    await context.q.put(1, time.time() + 0.5)
    v, ts = await f
    assert v == 1


@pytest.mark.timeout(1)
async def test_on_time_none(context, event_loop):
    f = event_loop.create_task(context.q.get())
    for _ in range(3):
        event_loop.create_task(context.q.get())
    await context.q.put(1, time.time() + 0.2)
    v = await f
    assert v == 1


@pytest.mark.timeout(1)
async def test_on_time_send(context, event_loop):
    f1 = event_loop.create_task(context.q.get())
    await context.q.put(2, time.time() + 0.6)
    await context.q.put(1, time.time() + 0.2)
    f2 = event_loop.create_task(context.q.get())
    v = await f1
    assert v == 1
    v = await f2
    assert v == 2


@pytest.mark.timeout(2)
async def test_on_time_not_send(context, event_loop):
    try:
        await context.q.get(timeout=0.1)
    except asyncio.TimeoutError:
        pass
    await context.q.put(2, time.time() + 0.6)
    await context.q.put(1, time.time() + 0.2)
    await asyncio.sleep(0.8)
    f2 = event_loop.create_task(context.q.get())
    v = await f2
    assert v == 1


@pytest.mark.timeout(1)
async def test_cleanup(event_loop):
    async with TimestampQueue(add_score=1, maxsize=2) as q:
        event_loop.create_task(q.get())
        for v in range(3):
            event_loop.create_task(q.put(v))
        await asyncio.sleep(0.1)
        assert q.full()
        assert q._getters
        assert q._putters
    assert not q._getters
    assert not q._putters
