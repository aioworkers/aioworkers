import logging
import sys
from pathlib import Path

from . import config, formatter

logger = logging.getLogger(__name__)


def load_plugin(module: str, force=False):
    if force:
        pass
    elif module in sys.modules:
        return
    try:
        m = __import__(module, fromlist=['plugin'])
    except ImportError:
        return
    plugin = getattr(m, 'plugin', m)
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


def search_plugins(*modules, force=False):
    result = []
    if not modules:
        modules = get_names()
    for name in modules:
        plugin = load_plugin(name, force=force)
        if plugin:
            logger.info('Loaded plugin {} from {}'.format(plugin, name))
            result.append(plugin)
    return result


class Plugin:
    formatters = ()
    config_loaders = ()
    configs = ()

    def __init__(self):
        for f in self.formatters:
            formatter.registry(f)
        for cl in self.config_loaders:
            config.registry(cl)

    def get_config(self):
        return {}

    def add_arguments(self, parser):
        pass


class ProxyPlugin(Plugin):
    def __init__(self, original):
        self._original = original
        for i in (
                'formatters', 'config_loaders', 'configs',
                'get_config', 'add_arguments',
        ):
            v = getattr(original, i, None)
            if v:
                setattr(self, i, v)

        if hasattr(self._original, '__file__'):
            p = self._original.__file__
        elif hasattr(self._original, '__module__'):
            mod = sys.modules[self._original.__module__]
            p = mod.__file__
        else:
            p = None
        if not self.configs and p is not None:
            path = Path(p)
            if path.name == '__init__.py':
                self.configs = tuple(path.parent.glob('plugin*'))
        super().__init__()
