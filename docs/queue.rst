Queue
-----

Is entity based on aioworkers.queue.base.AbstractQueue

The simplest example demonstrating the idea (not intended for use):

.. code-block:: python

  class Queue(AbstractQueue):
      async def put(self, item):
          self._q.append(item)

      async def get(self):
          return self._q.pop(0)
