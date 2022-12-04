Link
=======

For entity relationships with typing, use Link.

Tree in conf:

.. code-block:: yaml

  worker:
    cls: mymodule.MyWorker
    storage: .storages.my_subdir.subdir

  storages:
    cls: aioworkers.storage.filesystem.FileSystemStorage
    path: /tmp/


.. code-block:: python

  from aioworkers.core.base import link
  from aioworkers.storage.filesystem import FileSystemStorage

  class MyWorker(aioworkers.worker.base.Worker):
     storage: FileSystemStorage = link()

     async def run(*args, **kwargs):
         await self.storage.set('key', 'val')


Thus self.storage is property link to .storages.my_subdir.subdir
