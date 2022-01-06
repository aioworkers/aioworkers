Support asgi
============

Supported run:

* asgi on aioworkers
* aioworkers over asgi


asgi on aioworkers
------------------

my_app.py:

.. code-block:: python

  from fastapi import FastAPI


  app = FastAPI()


  @app.get("/s")
  def a(op: int):
      return {'op': op}


conf.yaml:

.. code-block:: yaml

  http:
    port: 8080
    handler: my_app:app


run:

.. code-block:: shell

  aioworkers aioworkers.net.web -c conf.yaml


aioworkers over asgi
--------------------

.. code-block:: python

  from aioworkers.net.web.asgi import AsgiMiddleware
  from aioworkers.storage.filesystem import FileSystemStorage


  async def asgi_app(scope, receive, send):
      assert scope["type"] == "http"
      ctx = scope['extensions']['aioworkers']['context']
      content = await ctx.storage.get(scope['path'].lstrip('/'))

      if content is None:
          await send({
              "type": "http.response.start",
              "status": 404,
          })
      else:
          await send({
              "type": "http.response.start",
              "status": 200,
              "headers": [
                  [b"content-type", b"text/plain"],
              ]
          })
      await send({
          "type": "http.response.body",
          "body": content or b"",
      })

  asgi_app = AsgiMiddleware(
      app=asgi_app,  # wrap you asgi application
      plugin=__name__,  # you main plugin for aioworkers
  )

  # For example context with storage
  asgi_app.context.storage = FileSystemStorage(path='.')
