import argparse
import sys

import pytest

from aioworkers.core import plugin as core_plugin
from aioworkers.core.plugin import ProxyPlugin, get_plugin_loaders, search_plugins


class plugin:
    configs = ('a',)


@pytest.mark.parametrize('name', [__name__, 'tests'])
def test_proxy_plugin(name, mocker):
    del sys.modules[name]
    assert name not in sys.modules
    (p,) = search_plugins(name)
    assert isinstance(p, ProxyPlugin)
    assert p.get_config() == {}
    p.add_arguments(mocker.Mock())
    p.parse_known_args(args=[], namespace=argparse.Namespace())


def test_search_plugins(mocker):
    mocker.patch.object(core_plugin, "get_names", lambda *a: [__name__])
    plugins = search_plugins()
    assert len(plugins) == 1


def test_get_plugin_loaders(mocker):
    mocker.patch.object(core_plugin, "get_names", lambda *a: [__name__])
    get_plugin_loaders()
    loaders = get_plugin_loaders("pytest11")
    assert "" not in loaders
    assert __name__ in loaders
    for k, v in loaders.items():
        assert v.load()
