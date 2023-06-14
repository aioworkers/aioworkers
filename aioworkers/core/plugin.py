import functools
import logging
import sys
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Dict, Iterable, Mapping, Optional, Sequence, Union

from . import config, formatter

logger = logging.getLogger(__name__)

if sys.version_info < (3, 8):  # no cov
    from pkg_resources import EntryPoint, iter_entry_points
else:
    from importlib.metadata import EntryPoint, entry_points

    def iter_entry_points(group: str, name: Optional[str] = None):
        assert not name
        eps = entry_points()
        if sys.version_info < (3, 10):
            group_eps = eps.get(group, ())
        else:  # no cov
            group_eps = eps.select(group=group)
        for entry_point in group_eps:
            yield entry_point


def load_plugin(
    module: str,
    force: bool = False,
    *,
    cache: Dict = {},
) -> Optional['Plugin']:
    if module in cache:
        return cache[module]
    elif force:
        pass
    elif module in sys.modules:
        return None

    loaders = get_plugin_loaders()
    pl = loaders.get(module) or PluginLoader(module)
    plugin = pl.load()
    cache[module] = plugin
    return plugin


@functools.lru_cache(None)
def get_names(group="aioworkers") -> Iterable[str]:
    dedup = set()
    for s in sys.path:
        path = Path(s)
        if not path.is_dir():
            continue
        for i in path.glob(f"{group}_*"):
            name = i.name
            if name not in dedup and "-" not in name:
                dedup.add(name)
                yield name


@functools.lru_cache(None)
def search_plugins(*modules: str, force=False):
    result = []
    pls = get_plugin_loaders()
    if not modules:
        modules = tuple(pls)
    for module in modules:
        if not force and module in sys.modules:
            continue
        pl = pls.get(module) or PluginLoader(module)
        plugin = pl.load()
        if not plugin:
            continue
        elif pl.entry_point is None:
            logger.info("Loaded plugin %s", module)
        else:
            logger.info("Loaded plugin %s", pl.entry_point)
        result.append(plugin)
    return result


class Plugin:
    formatters: Sequence[formatter.BaseFormatter] = ()
    config_loaders: Sequence[config.ConfigFileLoader] = ()
    configs: Sequence[Union[str, PurePath]] = ()

    def __init__(self):
        for f in self.formatters:
            formatter.registry(f)
        for cl in self.config_loaders:
            config.registry(cl)

    def get_config(self):
        return {}

    def add_arguments(self, parser):
        pass

    def parse_known_args(self, args, namespace):
        """argparse method"""
        return namespace, args


class ProxyPlugin(Plugin):
    def __init__(self, original):
        self._original = original
        for i in (
            'formatters',
            'config_loaders',
            'configs',
            'get_config',
            'add_arguments',
        ):
            v = getattr(original, i, None)
            if v:
                setattr(self, i, v)

        p = None
        if hasattr(self._original, '__file__'):
            p = self._original.__file__
        elif hasattr(self._original, '__module__'):
            mod = sys.modules[self._original.__module__]
            p = mod.__file__
        if not self.configs and p is not None:
            path = Path(p)
            if path.name == '__init__.py':
                self.configs = tuple(path.parent.glob('plugin*'))
        super().__init__()


@dataclass
class PluginLoader:
    module: str
    entry_point: Optional[EntryPoint] = None

    @classmethod
    def from_entry_point(cls, ep: EntryPoint) -> "PluginLoader":
        if sys.version_info < (3, 8):  # no cov for 3.8
            module = ep.module_name
        elif sys.version_info < (3, 9):
            m = ep.pattern.match(ep.value)
            assert m is not None, f"Not valid value of EntryPoint {ep.value}"
            module = m.group("module")
        else:  # no cov for 3.8
            module = ep.module
        return cls(module, ep)

    def load(self) -> Optional[Plugin]:
        if self.entry_point is None:
            try:
                m = __import__(self.module, fromlist=['plugin'])
            except ImportError:
                return None
            else:
                plugin = getattr(m, 'plugin', m)
        else:
            plugin = self.entry_point.load()
        if callable(plugin):
            plugin = plugin()
        if not isinstance(plugin, Plugin):
            plugin = ProxyPlugin(plugin)
        return plugin


@functools.lru_cache(None)
def get_plugin_loaders(group="aioworkers") -> Mapping[str, PluginLoader]:
    modules_with_ep = set()
    result = {}
    for ep in iter_entry_points(group):
        pl = PluginLoader.from_entry_point(ep)
        modules_with_ep.add(pl.module.split(".", 1)[0])
        result[pl.module] = pl
    for module in get_names(group):
        if module not in modules_with_ep:
            result[module] = PluginLoader(module)
    return result
