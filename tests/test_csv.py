import os
import tempfile

import pytest


@pytest.fixture
def csv_file():
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile1:
        tmpfile1.write(b'name,uid\nx,3\nf,4')
        tmpfile1.flush()
    yield tmpfile1
    os.unlink(tmpfile1.name)


@pytest.fixture
def config_yaml(csv_file):
    return """
    reader:
        cls: aioworkers.queue.csv.DictReader
        file: {}
    """.format(csv_file.name)


async def test_dictreader(context):
    reader = context.reader
    assert {'name': 'x', 'uid': '3'} == await reader.get()
    assert {'name': 'f', 'uid': '4'} == await reader.get()
