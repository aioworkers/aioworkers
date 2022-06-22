from aioworkers.core.config import MergeDict
from aioworkers.queue.base import Queue, ScoreQueue


async def test_queue(event_loop):
    q = Queue({}, loop=event_loop)
    await q.init()
    await q.put(2)
    assert 2 == await q.get()


async def test_score_base(event_loop):
    q = ScoreQueue({}, loop=event_loop)
    await q.init()
    await q.put(2, 3)
    assert 2 == await q.get()
    await q.put(2, 3)
    assert (2, 3) == await q.get(score=True)
    assert not q


async def test_score_time(event_loop):
    q = ScoreQueue(
        MergeDict(
            default_score='time.time',
        ),
        loop=event_loop,
    )
    await q.init()
    await q.put(2)
    assert 2 == await q.get()
    await q.put(3)
    await q.put(4)
    a1, t1 = await q.get(score=True)
    a2, t2 = await q.get(score=True)
    assert a1 == 3
    assert a2 == 4
    assert t1 <= t2
    assert not q
