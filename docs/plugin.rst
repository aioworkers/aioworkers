Plugin
======

The package supports plugins. Automatically load plugins from modules whose name starts with "aioworkers".

The module can be written by defining the plugin class in the module:

.. code-block:: python

   class plugin(aioworkers.core.plugin.Plugin):
       def get_config(self):
           return {}

Loading:

.. code-block:: shell

    aioworkers mymodule


The plugin is also considered to be a module whose functions are defined according
to the interface of the base class Plugin.
If in module not defined get_config search config files by mask plugin*.
