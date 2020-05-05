import asyncio
import time

from aioworkers.queue.timeout import TimestampQueue, UniqueQueue


async def test_put():
    q = TimestampQueue()
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


async def test_put_unique():
    q = UniqueQueue()
    await q.put(1, 1)
    await q.put(1, 2)
    await q.put(1, 3)
    await q.put(2, 3)
    await q.put(2, 2)
    await q.put(2, 1)
    assert 2 == await q.get()
    assert 1 == await q.get()
    assert not q


async def test_timestamp_score():
    q = TimestampQueue()
    await q.put(1)
    a, ts = await q.get(score=True)
    assert a == 1
    assert ts <= time.time()


async def test_timestamp_await():
    q = TimestampQueue()
    f = q.get(score=True)
    t0 = time.time()
    await q.put(1)
    a, ts = await f
    assert a == 1
    assert t0 <= ts <= time.time()


async def test_uniq_score():
    q = UniqueQueue()
    await q.put(1)
    a, ts = await q.get(score=True)
    assert a == 1
    assert ts <= time.time()


async def test_stop():
    q = TimestampQueue()
    q.get()
    await q.put(1, 1)
    q.cleanup()
