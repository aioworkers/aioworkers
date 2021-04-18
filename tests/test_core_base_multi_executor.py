import pytest
from datetime import timedelta


@pytest.fixture
def config_yaml(unused_port):
    return """
    e:
        cls: aioworkers.core.base.MultiExecutorEntity
        executors:
          get: 1
          put: 1
          none: none
          x: null
    """


async def test_multiexecutor(context):
    assert await context.e.run_in_executor('get', timedelta, days=1)
    assert await context.e.run_in_executor('none', timedelta, hours=2)
    assert await context.e.run_in_executor('put', timedelta, minutes=1)
    assert await context.e.run_in_executor('x', timedelta, seconds=1)
