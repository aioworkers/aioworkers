import sys

import pytest

from aioworkers.core.plugin import ProxyPlugin, search_plugins


class plugin:
    configs = ('a',)


@pytest.mark.parametrize('name', [__name__, 'tests'])
def test_proxy_plugin(name, mocker):
    del sys.modules[name]
    assert name not in sys.modules
    p, = search_plugins(name)
    assert isinstance(p, ProxyPlugin)
    assert p.get_config() == {}
    p.add_arguments(mocker.Mock())
    p.parse_known_args()
