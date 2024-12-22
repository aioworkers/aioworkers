from typing import Any, TypeVar

from aioworkers.core.config import MergeDict
from aioworkers.queue.base import Queue, ScoreQueue, ScoreQueueMixin

TScoreQueue = TypeVar("TScoreQueue", bound=ScoreQueueMixin)


async def test_queue():
    q = Queue({})
    await q.init()
    await q.put(2)
    assert 2 == await q.get()


async def test_score_base():
    q: Any = ScoreQueue({})
    await q.init()
    await q.put(2, 3)
    assert 2 == await q.get()
    await q.put(2, 3)
    assert (2, 3) == await q.get(score=True)
    assert not q


async def test_score_time():
    q: Any = ScoreQueue(
        MergeDict(
            default_score="time.time",
        ),
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
