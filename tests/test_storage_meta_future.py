import pytest


@pytest.fixture
def config_yaml():
    return """
    s:
        cls: aioworkers.storage.meta.FutureStorage
        weak: false
    s1:
        cls: aioworkers.storage.meta.FutureStorage
    s2:
        cls: aioworkers.storage.meta.FutureStorage
    s3:
        cls: aioworkers.storage.meta.FutureStorage
        exists_set: true
    """


async def test_simple_dict(context):
    assert context.s


async def test_1(context):
    f1 = context.s1.get(1)
    f2 = context.s1.get(1)
    assert f1 is f2


async def test_2(context):
    f = context.s2.get(1)
    await context.s2.set(1, 1)
    assert 1 == await f


async def test_3(context):
    await context.s3.set(1, 1)
    await context.s3.set(1, 2)
