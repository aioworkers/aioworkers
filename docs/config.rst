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
   
  config = Config()
  config.load('/path/to/config.yaml')


Access to fields config:

.. code-block:: python

  >>> conf.a.b.c
  1
  >>> conf['a']['b']['c']
  1
  >>> conf['a.b.c']
  1

Overriding
~~~~~~~~~~

.. code-block:: python

  config = Config()
  config.load('/path/to/config.yaml',
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

Advanced confugure
------------------

.. code-block:: yaml

  env:
    logging.root.level: LOG_LEVEL  # replace value to value of environment variable (if set)
  
  logging:
    version: 1
    disable_existing_loggers: false
    root:
      level: ERROR
      handlers: [console]
    handlers:
      console:
        level: INFO
        class: logging.StreamHandler
