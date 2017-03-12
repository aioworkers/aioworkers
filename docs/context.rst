Context
=======

Context is instance witch contains links to entities to access on path.

.. code-block:: python

   await self.context.workers.worker1.stop(force=False)
   await self.context.storages.tmp_disk.set(k, v)

Create instance Context with tree entities specified in conf

Tree in conf:

.. code-block:: yaml

  workers:
    worker1:
      cls: aioworkers.worker.base.Worker
      run: mymodule.mycoro

  storages:
    tmp_disk:
      cls: aioworkers.storage.filesystem.HashFileSystemStorage
      path: /tmp/

.. code-block:: python

  from aioworkers.core.context import Context

  context = Context(conf, loop=loop)

Initialize context

.. code-block:: python

  await context.init()

Set signals

.. code-block:: python

  context.on_start.append(self.start)
  context.on_stop.append(self.stop)

Run context tree

.. code-block:: python

  await context.start()

Stop context tree

.. code-block:: python

  await context.stop()


.. automodule:: aioworkers.core.context

   Class
   -----

   Context
   ^^^^^^^

   .. autoclass:: Context
      :members:
