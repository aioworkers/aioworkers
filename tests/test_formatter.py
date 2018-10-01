import pytest

from aioworkers.core.formatter import BaseFormatter, StringFormatter, registry


class RtsFormatter(StringFormatter):
    name = 'rts'

    def encode(self, b):
        return super().decode(b)

    def decode(self, b):
        return super().encode(b)


registry(RtsFormatter)


@pytest.mark.parametrize('formatter,data', [
    ('json', {'f': 3}),
    ('pickle', {'f': 3}),
    ('yaml', {'f': 3}),
    ('str', '123'),
    ('newline|str', '123'),
    ('str|bnewline', '123'),
    ('str|zlib', '123'),
    ('str|lzma', '123'),
])
def test_formatters(formatter, data):
    f = registry.get(formatter)
    enc = f.encode(data)
    assert isinstance(enc, bytes)
    assert f.decode(enc) == data


@pytest.mark.parametrize('f', [
    ['str', 'rts'],
    'str:rts',
    'str|rts',
    'str|from_str:str|from_str',
])
def test_chain(f):
    f = registry.get(f)
    a = '1'
    assert f.encode(a) == a
    assert f.decode(a) == a


def test_registry():
    with pytest.raises(ValueError):
        registry(RtsFormatter)
    with pytest.raises(ValueError):
        registry(BaseFormatter)
    with pytest.raises(KeyError):
        registry.get(1)
