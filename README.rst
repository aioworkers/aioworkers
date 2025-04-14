aioworkers
==========

.. image:: https://img.shields.io/pypi/v/aioworkers.svg
  :target: https://pypi.org/project/aioworkers

.. image:: https://github.com/aioworkers/aioworkers/workflows/Tests/badge.svg
  :target: https://github.com/aioworkers/aioworkers/actions?query=workflow%3ATests

.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v0.json
  :target: https://github.com/charliermarsh/ruff
  :alt: Code style: ruff

.. image:: https://img.shields.io/badge/types-Mypy-blue.svg
  :target: https://github.com/python/mypy
  :alt: Code style: Mypy

.. image:: https://readthedocs.org/projects/aioworkers/badge/?version=latest
  :target: https://aioworkers.readthedocs.io/en/latest/?badge=latest
  :alt: Documentation Status

.. image:: https://img.shields.io/pypi/pyversions/aioworkers.svg
  :target: https://pypi.org/project/aioworkers
  :alt: Python versions

.. image:: https://img.shields.io/pypi/dm/aioworkers.svg
  :target: https://pypistats.org/packages/aioworkers

.. image:: https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg
  :alt: Hatch project
  :target: https://github.com/pypa/hatch


Easy configurable workers based on asyncio


* Free software: Apache Software License 2.0
* Required: Python >=3.9, optional
  `pyyaml <https://pypi.python.org/pypi/pyyaml>`_,
  `uvloop <https://pypi.python.org/pypi/uvloop>`_,
  `httptools <https://pypi.python.org/pypi/httptools>`_,
  `yarl <https://pypi.python.org/pypi/yarl>`_,
  `crontab <https://pypi.python.org/pypi/crontab>`_,
  `setproctitle <https://pypi.python.org/pypi/setproctitle>`_,
  `msgpack <https://pypi.python.org/pypi/msgpack>`_,
  `bson <https://pypi.python.org/pypi/bson>`_,
  `jupyter <https://pypi.python.org/pypi/jupyter>`_.
* Documentation: https://aioworkers.readthedocs.io.


Features
--------

* Specify abstract class for communication between components
* Configuration subsystem


Development
-----------

Check code:

.. code-block:: shell

    hatch run lint:all


Format code:

.. code-block:: shell

    hatch run lint:fmt


Run tests:

.. code-block:: shell

    hatch run pytest


Run tests with coverage:

.. code-block:: shell

    hatch run cov
