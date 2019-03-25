import pytest

from aioworkers.core.base import AbstractNestedEntity
from aioworkers.queue.base import PriorityQueue, Queue


@pytest.fixture
def config_yaml():
    return """
    p:
      cls: aioworkers.core.base.AbstractNestedEntity
      p:
        cls:
      x:
        cls: aioworkers.queue.base.Queue
      child:
        cls: aioworkers.queue.base.PriorityQueue
    """


async def test_nested(context):
    assert isinstance(context.p.p, AbstractNestedEntity)
    assert isinstance(context.p.x, Queue)
    assert isinstance(context.p.a, PriorityQueue)
