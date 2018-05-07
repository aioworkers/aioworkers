import tempfile

import pytest

from aioworkers.queue import csv


@pytest.yield_fixture
def csv_file():
    with tempfile.NamedTemporaryFile() as tmpfile1:
        tmpfile1.write(b'name,uid\nx,3\nf,4')
        tmpfile1.flush()
        yield tmpfile1


async def test_dictreader(loop, csv_file, config):
    config.update(file=csv_file.name)
    reader = csv.DictReader(config, loop=loop)
    await reader.init()
    assert {'name': 'x', 'uid': '3'} == await reader.get()
    assert {'name': 'f', 'uid': '4'} == await reader.get()
