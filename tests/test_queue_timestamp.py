import asyncio
import time

from aioworkers.queue.timeout import TimestampQueue, UniqueQueue


async def test_put(loop):
    q = TimestampQueue({}, loop=loop)
    await q.init()
    await q.put((1, 1))
    assert 1 == await q.get()

    t = time.time()
    await q.put((t + 0.2, 2))
    await q.put((t + 0.3, 3))
    await q.put((t + 0.1, 1))
    await asyncio.sleep(0.2, loop=loop)
    assert 1 == await q.get()
    assert 2 == await q.get()
    assert 3 == await q.get()
    assert not q


async def test_put_unique(loop):
    q = UniqueQueue({}, loop=loop)
    await q.init()
    await q.put((1, 1))
    await q.put((2, 1))
    await q.put((3, 1))
    await q.put((3, 2))
    await q.put((2, 2))
    await q.put((1, 2))
    assert 2 == await q.get()
    assert 1 == await q.get()
    assert not q


async def test_stop(loop):
    q = TimestampQueue({}, loop=loop)
    await q.init()
    q.get()
    await q.put((1, 1))
    await q.stop()
