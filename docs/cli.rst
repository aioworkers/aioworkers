Command line interface
======================

The package has a command interface.

.. code-block:: shell

    aioworkers [command [command]] [--**options]

Options:

--port -p: http port

--host: listen host

+g ++groups: run groups

-g --groups: run all exclude groups

-i --interact: interactive mode

-l --logging: log level

-c --config: configs


Command:

Dotted path to context member, module, function or coroutine.
If command is module run it as plugin.


Configs:

You can specify several configuration files.
The resulting configuration will be obtained by merging.
The first configuration will be override with the second and so on.
You can specify local files, as well as files available via http
