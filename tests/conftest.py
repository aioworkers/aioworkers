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
