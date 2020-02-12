Plugin
======

The package supports plugins. Automatically load plugins from modules whose name starts with "aioworkers".

The module can be written by defining the plugin class in the module:

.. code-block:: python

   class plugin(aioworkers.core.plugin.Plugin):
       configs = ('/path/to/config.yaml',)

       def get_config(self):
           return {}

       def add_arguments(self, parser):
           pass

       def parse_known_args(self, args, namespace):
           return namespace, args


or module/package contains:

.. code-block:: python

   configs = ('/path/to/config.yaml',)

   def get_config():
       return {}


Run my module as plugin:

.. code-block:: shell

    aioworkers mymodule


If in module not defined get_config search config files by mask plugin*.
