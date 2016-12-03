import pytest

from aioworkers.core.formatter import get_formatter


@pytest.mark.parametrize('formatter,data', [
    ('json', {'f': 3}),
    ('pickle', {'f': 3}),
    ('yaml', {'f': 3}),
    ('str', '123'),
])
def test_formatters(formatter, data):
    f = get_formatter(formatter)
    enc = f.encode(data)
    assert isinstance(enc, bytes)
    assert f.decode(enc) == data
