import uuid

import aioredis
import pytest
import time

from aioworkers.core.config import MergeDict
from aioworkers.redis import \
    RedisQueue, RedisZQueue, RedisStorage, TimestampZQueue


async def test_queue(loop):
    config = MergeDict(key=str(uuid.uuid4()))
    config['app.redis_pool'] = await aioredis.create_pool(
        ('localhost', 6379), loop=loop)
    context = config
    q = RedisQueue(config, context=context, loop=loop)
    await q.init()
    await q.put(3)
    assert 1 == await q.length()
    assert [b'3'] == await q.list()
    assert b'3' == await q.get()
    await q.put(3)
    assert 1 == await q.length()
    await q.clear()
    assert not await q.length()


async def test_queue_json(loop):
    config = MergeDict(
        key=str(uuid.uuid4()),
        format='json',
    )
    config['app.redis_pool'] = await aioredis.create_pool(
        ('localhost', 6379), loop=loop)
    context = config
    q = RedisQueue(config, context=context, loop=loop)
    await q.init()
    await q.put({'f': 3})
    assert 1 == await q.length()
    assert [{'f': 3}] == await q.list()
    assert {'f': 3} == await q.get()
    await q.put({'f': 3})
    assert 1 == await q.length()
    await q.clear()
    assert not await q.length()


async def test_zqueue(loop, mocker):
    config = MergeDict(
        key=str(uuid.uuid4()),
        format='str',
        timeout=0,
    )
    config['app.redis_pool'] = await aioredis.create_pool(
        ('localhost', 6379), loop=loop)
    context = config
    q = RedisZQueue(config, context=context, loop=loop)
    await q.init()
    await q.put((4, 'a'))
    await q.put((3, 'c'))
    await q.put((2, 'b'))
    await q.put((1, 'a'))
    assert 3 == await q.length()
    assert ['a', 'b', 'c'] == await q.list()
    assert 3 == await q.length()
    assert 'a' == await q.get()
    assert ['b', 'c'] == await q.list()
    assert 2 == await q.length()
    assert 'b' == await q.get()
    assert ['c'] == await q.list()
    assert 1 == await q.length()
    assert 'c' == await q.get()
    assert [] == await q.list()
    assert not await q.length()

    with pytest.raises(TypeError):
        with mocker.patch('asyncio.sleep'):
            await q.get()


async def test_ts_zqueue(loop, mocker):
    config = MergeDict(
        key=str(uuid.uuid4()),
        format='str',
        timeout=10,
    )
    config['app.redis_pool'] = await aioredis.create_pool(
        ('localhost', 6379), loop=loop)
    context = config
    q = TimestampZQueue(config, context=context, loop=loop)
    await q.init()
    await q.put((time.time() + 4, 'c'))
    await q.put((4, 'a'))
    assert 2 == await q.length()
    assert ['a', 'c'] == await q.list()
    assert 'a' == await q.get()
    assert 1 == await q.length()
    assert ['c'] == await q.list()

    with pytest.raises(TypeError):
        with mocker.patch('asyncio.sleep'):
            await q.get()


async def test_storage(loop):
    config = MergeDict(
        name='1',
        prefix=str(uuid.uuid4()),
        format='json',
    )
    config['app.redis_pool'] = await aioredis.create_pool(
        ('localhost', 6379), loop=loop)
    context = config
    q = RedisStorage(config, context=context, loop=loop)
    await q.init()
    await q.set('g', {'f': 3})
    assert {'f': 3} == await q.get('g')
