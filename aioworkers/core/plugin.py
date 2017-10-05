import logging
import sys
from itertools import chain
from pathlib import Path


logger = logging.getLogger(__name__)


def load_plugin(module: str):
    if module in sys.modules:
        return
    try:
        m = __import__(module, fromlist=['plugin'])
    except ImportError:
        return
    if not hasattr(m, 'plugin'):
        return
    plugin = m.plugin
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
    def get_config(self):
        return {}


class ProxyPlugin(Plugin):
    def __init__(self, original):
        self._original = original

    def get_config(self):
        if hasattr(self._original, 'get_config'):
            return self._original.get_config()
        return {}
