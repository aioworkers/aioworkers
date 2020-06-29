from asyncio import Queue

from aioworkers.core.context import Context
from aioworkers.net.web.asgi import AsgiMiddleware


async def app(scope, receive, send):
    assert scope['type'] == 'http'
    await send({
        "type": "http.response.start",
        "status": 404,
    })


async def test_lifespan():
    q = Queue()
    q.put_nowait({'type': 'lifespan.startup'})
    q.put_nowait({'type': 'lifespan.shutdown'})
    a = AsgiMiddleware(app, plugin=__name__)
    await a({'type': 'lifespan'}, q.get, q.put)
    assert {
        'type': 'lifespan.startup.complete',
    } == await q.get()
    assert {
        'type': 'lifespan.shutdown.complete',
    } == await q.get()


async def test_http():
    q = Queue()
    a = AsgiMiddleware(app, context=Context())
    await a({'type': 'http'}, q.get, q.put)
    assert {
        "type": "http.response.start",
        "status": 404,
    } == await q.get()
