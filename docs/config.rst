Configuration
=============

A simple configuration file looks like this:

.. code-block:: yaml

  http:
    port: 1234

  a:
    b:
      c: 1

Loading a configuration file:

.. code-block:: python

  from aioworkers.core.config import Config
   
  conf = Config().load('/path/to/config.yaml')


Access to fields config:

.. code-block:: python

  >>> conf.a.b.c
  1
  >>> conf['a']['b']['c']
  1
  >>> conf['a.b.c']
  1

Overriding
----------

.. code-block:: python

  conf = Config().load('/path/to/config.yaml',
                       '/path/to/override.yaml',
                       ...
                       'override.yaml')

Override contains:

.. code-block:: yaml

  a.b.c: 2

or:

.. code-block:: yaml

  a.b:
    c: 2
