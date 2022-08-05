Entity
======

Entity is a primitive described in config:

.. code-block:: yaml

  myentity:
      cls: mymodule.MyEntity
      timeout: 60

Class of entity must be inherited from aioworkers.core.base.AbstractEntity:

.. code-block:: python

  class Connect(AbstractEntity):
      async def init(self):
          await super().init()
          print(self.config.timeout)


Life cycle
----------

1. create
2. set_config & set_context
3. initialize
4. connect (optional)
5. start (optional)
6. stop (optional)
7. disconnect (optional)
8. cleanup (optional)


Create
~~~~~~
Perform __init__ from AbstractEntity. Normally, do not override the method __init__.


Initialization
~~~~~~~~~~~~~~
Perform coroutine init. This method is designed to initialize the encapsulating components of entity.
Designed to check links with other entity and set signals.


Connect/disconnect
~~~~~~~~~~
Perform before starting and after stopping the application,
to do this, connect/disconnect should be added to the signals.


Start/stop
~~~~~~~~~~
Performing when the application is started or stopped,
for this, the start/stop should be added to the signals.

Implementation Entity
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

  class MyEntity(aioworkers.core.base.AbstractEntity):
      async def init(self):
          await super().init()
          groups = self.config.get('groups')
          self.context.on_connect.append(self.connect, groups)
          self.context.on_start.append(self.start, groups)
          self.context.on_stop.append(self.stop, groups)
          self.context.on_disconnect.append(self.disconnect, groups)

      async def connect(self):
          self.pool = create_engine(
              host=self.config.host,
              port=self.config.port,
          )

      async def diconnect(self):
          self.pool.close()
          await self.pool.wait_closed()


Implementation Connector
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

  class Connector(aioworkers.core.base.AbstractConnector):
      async def connect(self):
          self.pool = create_engine(
              host=self.config.host,
              port=self.config.port,
          )

      async def disconnect(self):
          self.pool.close()
          await self.pool.wait_closed()


Implementation Worker
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

  class MyWorker(aioworkers.worker.base.Worker):
      async def run(self):
          print(self.context.myconnector.pool)
          print(self.context.myentity.pool)
          await asyncio.sleep(30)
