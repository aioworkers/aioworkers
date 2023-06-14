import argparse
import sys
from pathlib import Path

import pytest

from aioworkers.core import plugin as core_plugin
from aioworkers.core.plugin import (
    PluginLoader,
    ProxyPlugin,
    get_names,
    get_plugin_loaders,
    load_plugin,
    search_plugins,
)


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


def test_get_names(mocker):
    mocker.patch.object(sys, "path", [Path(__file__).parent])
    modules = get_names("test")
    assert modules


def test_load_plugin(mocker):
    pls = {__name__: PluginLoader(__name__)}
    mocker.patch.object(core_plugin, "get_plugin_loaders", lambda *a: pls)
    plugin = load_plugin(__name__)
    assert not plugin
    plugin = load_plugin(__name__, force=True)
    assert plugin
    plugin = load_plugin(__name__, force=True)
    assert plugin


def test_search_plugins(mocker):
    pls = {__name__: PluginLoader(__name__)}
    mocker.patch.object(core_plugin, "get_plugin_loaders", lambda *a: pls)
    plugins = search_plugins(force=True)
    assert len(plugins) == 1


def test_get_plugin_loaders(mocker):
    mocker.patch.object(core_plugin, "get_names", lambda *a: [__name__])
    loaders = get_plugin_loaders("pytest11")
    assert "" not in loaders
    assert __name__ in loaders
    for k, v in loaders.items():
        assert v.load()
