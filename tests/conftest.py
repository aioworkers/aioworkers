import pytest

from aioworkers.core.config import Config
from aioworkers.core.context import Context


@pytest.fixture
def config():
    c = Config()
    return c


@pytest.fixture
def context(loop, config):
    with Context(config, loop=loop) as ctx:
        yield ctx


@pytest.fixture
def make_coro():
    def make_coro(result=None):
        async def coro(*args, **kwargs):
            return result
        return coro
    return make_coro
