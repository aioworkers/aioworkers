import pytest
import yarl

from aioworkers.http import _URL as URL


def test_repr():
    url = URL('/api/')
    assert repr(url) == "URL('/api/')"


def test_div_err():
    url = URL('/api/')
    with pytest.raises(TypeError):
        assert url / 1


@pytest.mark.parametrize(
    'a',
    [
        '/api/',
        '/api',
        '/api/..',
        'http://aioworkers/api/',
        'http://aioworkers/api',
    ],
)
def test_yarl_compat(a):
    assert str(URL(a) / '1') == str(yarl.URL(a) / '1')
