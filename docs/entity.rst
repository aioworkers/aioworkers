Entity
======

Entity is a primitive described in config:

.. code-block:: yaml

  w:
      cls: connect.Connect
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
2. initialize
3. start (optional)
4. stop (optional)


Create
~~~~~~
Perform __init__ from AbstractEntity. Normally, do not override the method __init__.


Initialization
~~~~~~~~~~~~~~
Perform coroutine init. This method is designed to initialize the encapsulating components of entity.
Designed to check links with other entity and set signals.


Start/stop
~~~~~~~~~~
Performing when the application is started or stopped,
for this, the start/stop should be added to the signals.


Implementation
~~~~~~~~~~~~~~

.. code-block:: python

  class Connect(AbstractEntity):
      async def init(self):
          await super().init()
          self.context.on_start.append(self.start)
          self.context.on_stop.append(self.stop)

      async def start(self):
          self.pool = create_engine(
              host=self.config.host,
              port=self.config.port,
          )

      async def stop(self):
          self.pool.close()
          await self.pool.wait_closed()
