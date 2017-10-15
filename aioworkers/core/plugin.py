import logging
import sys
from itertools import chain
from pathlib import Path

from . import formatter, config


logger = logging.getLogger(__name__)


def load_plugin(module: str):
    if module in sys.modules:
        return
    try:
        m = __import__(module, fromlist=['plugin'])
    except ImportError:
        return
    if hasattr(m, 'plugin'):
        plugin = m.plugin
    else:
        plugin = m
    if callable(plugin):
        plugin = plugin()
    if isinstance(plugin, Plugin):
        return plugin
    return ProxyPlugin(plugin)


def get_names():
    for path in sys.path:
        path = Path(path)
        if not path.is_dir():
            continue
        for i in path.glob('aioworkers*'):
            yield i.with_suffix('').name


def search_plugins(*modules):
    result = []
    for name in chain(get_names(), modules):
        plugin = load_plugin(name)
        if plugin:
            logger.info('Loaded plugin {} from {}'.format(plugin, name))
            result.append(plugin)
    return result


class Plugin:
    formatters = ()
    config_loaders = ()

    def __init__(self):
        for f in self.formatters:
            formatter.registry(f)
        for cl in self.config_loaders:
            config.registry(cl)

    def get_config(self):
        return {}


class ProxyPlugin(Plugin):
    def __init__(self, original):
        self._original = original
        for i in ('formatters', 'config_loaders'):
            setattr(self, i, getattr(original, i, ()))
        super().__init__()

    def get_config(self):
        if hasattr(self._original, 'get_config'):
            return self._original.get_config()
        return {}
