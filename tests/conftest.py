import pytest


@pytest.fixture
def make_coro():
    def make_coro(result=None):
        async def coro(*args, **kwargs):
            return result
        return coro
    return make_coro
