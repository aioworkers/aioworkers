import http.client
import io
import logging
import mimetypes
import os
import re
from abc import abstractmethod
from collections import ChainMap, OrderedDict, abc
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    Mapping,
    MutableMapping,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from aioworkers.http import URL
from aioworkers.net.uri import URI

from .. import humanize, utils
from ..utils import mapping_repr

logger = logging.getLogger(__name__)


class MergeDict(dict):
    def __init__(self, iterable=None, **kwargs):
        if iterable:
            result = {}
            result.update(iterable)
            result.update(kwargs)
            kwargs = result
        super().__init__()
        for k, v in kwargs.items():
            if isinstance(v, dict):
                self[k] = type(self)(v)
            else:
                self[k] = v

    def __repr__(self):
        r = super().__repr__()
        return type(self).__name__ + r

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item)

    def __setattr__(self, key, value):
        self[key] = value

    def __setitem__(self, key, value):
        replace = key.endswith('!')
        if replace:
            key = key.strip('!')

        is_dict = isinstance(value, dict)

        if '.' in key and '/' not in key:
            *path, z = key.split('.')

            d = self
            for k in path:
                if k not in d or not isinstance(d[k], dict):
                    d[k] = type(self)()
                d = d[k]

            if replace and is_dict:
                d[z] = type(self)(value)
            elif replace or not is_dict or z not in d or not isinstance(d[z], dict):
                d[z] = value
            else:
                d[z].update(value)

        elif not replace and is_dict and key in self and isinstance(self[key], type(self)):
            self[key].update(value)

        else:
            if is_dict:
                value = type(self)(value)
            super().__setitem__(key, value)

    def update(self, d, *args, **kwargs):
        for k, v in d.items():
            self[k] = v

    def get(self, key, default=None):
        try:
            return self[key]
        except Exception:
            return default

    def __getitem__(self, item):
        if '.' in item and '/' not in item:
            d = self
            path = item.split('.')
            for k in path:
                d = d[k]
            return d
        else:
            return super().__getitem__(item)

    def __contains__(self, key):
        try:
            self[key]
        except Exception:
            return False
        else:
            return True

    def __call__(self, *args, **kwargs):
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def __dir__(self):
        r = list(self.keys())
        r.extend(super().__dir__())
        return r

    def copy(self):
        cls = type(self)
        return cls(self)


def merge(source: Mapping, destination: MutableMapping):
    for key, value in source.items():
        if isinstance(value, Mapping):
            node = destination.setdefault(key, {})
            merge(value, node)
        else:
            destination[key] = value
    return destination


class ConfigFileLoader:
    extensions: Tuple[str, ...] = ()
    mime_types: Tuple[str, ...] = ()

    _load: Callable

    @abstractmethod  # pragma: no cover
    def load_str(self, s):
        raise NotImplementedError

    def load_bytes(self, b):
        return self.load_str(b.decode("utf-8"))

    def load_fd(self, fd):
        return self._load(fd)

    def load_path(self, path):
        if isinstance(path, str):
            path = Path(path)
        with path.open('rt') as fd:
            return self.load_fd(fd)

    def load_url(self, url):
        from urllib.request import urlopen

        with urlopen(url) as r:
            assert r.code == 200, r.read(255).decode("utf-8")
            ct = r.headers.get("Content-Type")
            mt = ct and ct.split(";")[0]
            assert not self.mime_types or mt in self.mime_types, f"Unexpected mime_type {mt}"
            return self.load_bytes(r.read())


class YamlLoader(ConfigFileLoader):
    extensions = ('.yaml', '.yml')

    def __init__(self, *args, **kwargs):
        yaml = __import__('yaml')
        Loader = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
        setattr(self, '_load', lambda data: yaml.load(data, Loader))

    def load_str(self, s):
        return self._load(s)


class TomlLoader(ConfigFileLoader):
    extensions = (".toml",)

    _load: Callable
    _load_fd: Callable

    def __init__(self, *args, **kwargs):
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        setattr(self, '_load', tomllib.loads)
        setattr(self, '_load_fd', tomllib.load)

    def load_fd(self, fd) -> Mapping:
        return self._load_fd(fd.buffer)

    def load_str(self, s: str) -> Mapping:
        return self._load(s)


class JsonLoader(ConfigFileLoader):
    extensions = ('.json',)
    mime_types = ('application/json',)

    def __init__(self, *args, **kwargs):
        json = __import__('json')
        setattr(self, '_load', json.load)
        self._loads = json.loads

    def load_str(self, s):
        return self._loads(s)


TValueMatcher = TypeVar('TValueMatcher', bound='ValueMatcher')


class ValueMatcher:
    fn = None  # type: Callable

    def __init__(self, value: Any):
        self._value = value

    @classmethod
    @abstractmethod  # pragma: no cover
    def match(cls: Type[TValueMatcher], value: Any) -> TValueMatcher:
        raise NotImplementedError

    @abstractmethod  # pragma: no cover
    def get_value(self):
        raise NotImplementedError


class IntValueMatcher(ValueMatcher):
    fn = int  # type: ignore

    @classmethod
    def match(cls, value):
        try:
            return cls(cls.fn(value.strip()))
        except ValueError:
            pass

    def get_value(self):
        return self._value


class BooleanValueMatcher(IntValueMatcher):
    true = frozenset({'1', 'true', 'on'})
    false = frozenset({'0', 'false', 'off'})

    @classmethod
    def fn(cls, value):
        if isinstance(value, bool):
            return value
        elif not isinstance(value, str):
            return bool(value)
        elif not value:
            raise ValueError(value)
        v = value.strip()[:5].lower()
        if v in cls.true:
            return True
        elif v in cls.false:
            return False
        else:
            raise ValueError(value)


class FloatValueMatcher(IntValueMatcher):
    fn = float  # type: ignore


class MultilineValueMatcher(ValueMatcher):
    re = re.compile(r'(\r\n)|(\n\r)|\r|\n')

    @classmethod
    def match(cls, value):
        result = cls.re.split(value)
        if len(result) > 1:
            return cls(result)

    def get_value(self):
        return [i for i in self._value if i]


class ListValueMatcher(ValueMatcher):
    @classmethod
    def match(cls, value):
        if value.startswith('[') and value.endswith(']'):
            return cls(value[1:-1])

    def get_value(self):
        if self._value:
            return self._value.split(',')
        else:
            return []


class StringReplaceLoader(ConfigFileLoader):
    matchers = (
        IntValueMatcher,
        BooleanValueMatcher,
        FloatValueMatcher,
        MultilineValueMatcher,
        ListValueMatcher,
    )

    def _replace(self, d, iterfunc=lambda d: d.items()):
        for k, v in iterfunc(d):
            if isinstance(v, dict):
                self._replace(v)
            elif isinstance(v, list):
                self._replace(v, enumerate)
            elif isinstance(v, str):
                for matcher in self.matchers:
                    m = matcher.match(v)
                    if m is not None:
                        v = m.get_value()
                        if isinstance(v, list):
                            self._replace(v, enumerate)
                        d[k] = v
                        break


class IniLoader(StringReplaceLoader):
    extensions = ('.ini',)

    def __init__(self, *args, **kwargs):
        self._configparser = __import__('configparser')

    def new_configparser(self, **kwargs):  # type: ignore
        kwargs.setdefault('allow_no_value', True)
        return self._configparser.ConfigParser(**kwargs)

    def load_fd(self, fd):
        config = self.new_configparser()
        config.read_file(fd)
        return self._convert(config)

    def load_path(self, path):
        config = self.new_configparser()
        config.read(str(path))
        return self._convert(config)

    def load_str(self, string):
        config = self.new_configparser()
        config.read_string(string)
        return self._convert(config)

    def _convert(self, config):
        c = {}
        for i in config.sections():
            d = dict(config[i])
            self._replace(d)
            c[i] = d
        return c


class Registry(dict):
    def __call__(self, cls):
        for ext in cls.extensions:
            if not isinstance(ext, str):
                raise ValueError(f"Extension expect string, given {ext!r}")
            elif ext in self:
                raise ValueError(f"Duplicate extension {ext}")
            self[ext] = cls
        for mime in cls.mime_types:
            if not isinstance(mime, str):
                raise ValueError(f"MimeType expect string, given {mime!r}")
            elif mime in self:
                raise ValueError(f"Duplicate MimeType {mime}")
            self[mime] = cls

    def get(self, key):
        if key not in self:
            raise LookupError(key)
        loader = self[key]
        return loader()


registry = Registry()
registry(YamlLoader)
registry(JsonLoader)
registry(IniLoader)
registry(TomlLoader)


extractors: Mapping[str, Callable] = {
    'get_int': int,
    'get_float': float,
    'get_bool': BooleanValueMatcher.fn,
    'get_duration': humanize.parse_duration,
    'get_size': humanize.parse_size,
    'get_url': URL,
    'get_uri': URI,
    'get_path': Path,
    'get_obj': utils.import_name,
}


TValueExtractor = TypeVar('TValueExtractor', bound='ValueExtractor')


class ValueExtractor(abc.Mapping):
    def __init__(
        self,
        mapping: Union[TValueExtractor, Mapping, None] = None,
        **kwargs,
    ):
        if isinstance(mapping, ValueExtractor):
            self._val: Mapping = mapping._val
        elif kwargs:
            self._val = kwargs
        else:
            assert isinstance(mapping, Mapping)
            self._val = mapping
        self._setattr = False

    @classmethod
    def _mapping_factory(
        cls: Type[TValueExtractor],
        *mappings: Mapping,
    ) -> TValueExtractor:
        maps: Dict[int, Mapping] = OrderedDict()
        for m in mappings:
            if isinstance(m, ValueExtractor):
                m = m._val
            if isinstance(m, ChainMap):
                for m in m.maps:
                    maps[id(m)] = m
            elif not isinstance(m, Mapping):
                raise ValueError(m)
            else:
                maps[id(m)] = m
        return ValueExtractor(ChainMap(*maps.values()))  # type: ignore

    def __setattr__(self, key, value):
        if not self.__dict__.get('_setattr', True):
            raise RuntimeError('Set attribute not supported')
        super().__setattr__(key, value)

    def new_child(
        self: TValueExtractor,
        *mappings: Mapping,
        **kwargs,
    ) -> TValueExtractor:
        return self._mapping_factory(*mappings, kwargs, self._val)

    def new_parent(
        self: TValueExtractor,
        *mappings: Mapping,
        **kwargs,
    ) -> TValueExtractor:
        return self._mapping_factory(self._val, *mappings, kwargs)

    def __getitem__(self, item: str) -> Any:
        try:
            v = self._val[item]
        except KeyError:
            raise KeyError(item)
        if isinstance(v, Mapping):
            return self._mapping_factory(v)
        return v

    def get(self, item, default=None):
        v = self._val.get(item, default)
        if v is default:
            return v
        elif isinstance(v, Mapping):
            return self._mapping_factory(v)
        return v

    def __contains__(self, item):
        return item in self._val

    def __getattr__(self, item):
        if item.startswith('_'):
            raise AttributeError(item)
        elif item not in extractors:
            try:
                v = self._val[item]
            except KeyError:
                raise AttributeError(item)
            if not isinstance(v, Mapping):
                return v
            return self._mapping_factory(v)
        converter = extractors[item]

        def extractor(key, default=..., *, null=False):
            if default is not ...:
                val = self._val.get(key, default)
            elif null:
                val = self._val.get(key)
            else:
                try:
                    val = self._val[key]
                except KeyError:
                    raise KeyError(key)
            if val is None and null:
                return val
            return converter(val)

        return extractor

    def __len__(self) -> int:
        return len(self._val)

    def __iter__(self) -> Iterator:
        if isinstance(self._val, ChainMap):
            maps = iter(reversed(self._val.maps))
            stack = []
            keys: Set[str] = set()
            for m in maps:
                if isinstance(m, MergeDict):
                    keys.update(m)
                    yield from m
                    break
                else:
                    stack.append(m)
            stack.extend(maps)
            for m in stack:
                for k in m:
                    if k not in keys:
                        yield k
                        keys.add(k)
        else:
            yield from self._val

    def __setstate__(self, state: dict):
        self.__init__(state)  # type: ignore

    def __getstate__(self) -> dict:
        return dict(self._val)

    def __repr__(self):
        return mapping_repr(self._val)


class Config(ValueExtractor):
    def __init__(self, search_dirs=(), **kwargs):
        self.env = ValueExtractor(os.environ)
        self._env = {}
        self.logging = {}
        self.search_dirs = []
        for i in search_dirs:
            if not isinstance(i, Path):
                i = Path(i)
            self.search_dirs.append(i)
        self.uris = []
        super().__init__(MergeDict())
        self.update(kwargs)

    def load_conf(self, fd, *, path=None, mime_type=None, response=None):
        if isinstance(response, http.client.HTTPResponse):
            url = URL(response.geturl())
            self.uris.append(url)
            mime_type = response.headers.get('Content-Type')
            if mime_type:
                mime_type = mime_type.split(';')[0].strip()
            logger.info('Config found: {} [{}]'.format(url, mime_type))
        if path:
            loader = registry.get(path.suffix)
            path = path.absolute()
            self.uris.append(path)
            logger.info('Config found: {}'.format(path))
        elif mime_type in registry:
            loader = registry.get(mime_type)
        elif mimetypes.guess_extension(mime_type) in registry:
            loader = registry.get(mimetypes.guess_extension(mime_type))
        elif not mime_type:
            raise LookupError('Not found mime_type %s' % mime_type)
        else:
            raise NotImplementedError
        if response is not None:
            return loader.load_bytes(response.read())
        elif fd is None:
            return loader.load_path(path)
        with fd:
            return loader.load_fd(fd)

    def _update_logging(self, conf):
        label = 'logging'
        if label in conf:
            merge(conf.pop(label), self.logging)
        parts = []
        for k in list(conf):
            if k.startswith(label):
                parts.append((k[8:], conf.pop(k)))
        for k, v in parts:
            dest = self.logging
            if '.' not in k:
                pass
            elif k.startswith("loggers"):
                k = k[len("loggers.") :]
                dest = dest["loggers"]
                if not isinstance(v, Mapping):
                    logger, k = k.rsplit('.', 1)
                    dest.setdefault(logger, {})[k] = v
                    continue
            else:
                *p, k = k.split('.')
                for i in p:
                    dest = dest.setdefault(i, {})
            if isinstance(v, Mapping):
                merge(v, dest.setdefault(k, {}))
            else:
                dest[k] = v

    def _from_env(self, c):
        def flater(d, prefix=''):
            for k, v in d.items():
                if prefix:
                    k = '.'.join([prefix, k])
                if isinstance(v, Mapping):
                    flater(v, k)
                else:
                    self._env[k] = v

        if 'env' in c:
            flater(c.pop('env'))
        for k in [i for i in c if i.startswith('env.')]:
            d = c.pop(k)
            key = k[4:]
            if isinstance(d, Mapping):
                flater(d, key)
            else:
                self._env[key] = d
        return {k: os.environ[name] for k, name in self._env.items() if name in os.environ}

    def _update(self, conf: MergeDict, data: dict) -> None:
        self._update_logging(data)
        env_map = self._from_env(data)
        conf(data)
        self._update_logging(env_map)
        conf(env_map)

    def load(self, *filenames, base=None):
        if base is None:
            assert isinstance(self._val, MergeDict)
            config = self._val
        else:
            config = base
        fns = []
        for fn in filenames:
            if isinstance(fn, str):
                fn = Path(fn)
            if isinstance(fn, Path):
                if not fn.is_absolute():
                    fns.append(fn)
                    continue
                c = self.load_conf(None, path=fn)
            elif isinstance(fn, http.client.HTTPResponse):
                c = self.load_conf(fn, response=fn)
            elif isinstance(fn, (io.TextIOWrapper, io.BufferedReader)):
                c = self.load_conf(fn, path=Path(fn.name))
            else:
                raise ValueError(fn)
            if c:
                self._update(config, c)
        for d in self.search_dirs:
            for fn in fns:
                if not Path(d, fn).exists():
                    continue
                f = Path(d, fn)
                c = self.load_conf(None, path=f)
                if c:
                    self._update(config, c)
        return config

    def update(self, *mappings, **kwargs):
        if kwargs:
            mappings += (kwargs,)
        for d in mappings:
            if isinstance(d, ValueExtractor):
                d = d.__getstate__()
            assert isinstance(self._val, MergeDict)
            self._update(self._val, d)

    def load_plugins(self, *modules, force=True):
        from . import plugin

        plugins = plugin.search_plugins(*modules, force=force)
        for p in plugins:
            self.load(*p.configs)
            self.update(p.get_config())
        return plugins

    def __len__(self) -> int:
        return len(self._val) + 1

    def __iter__(self) -> Iterator:
        yield 'logging'
        yield from self._val

    def __getitem__(self, item):
        if item == 'logging':
            return self.logging
        try:
            return super().__getitem__(item)
        except KeyError:
            raise KeyError(item)

    def __contains__(self, item):
        if item == 'logging':
            return True
        else:
            return super().__contains__(item)

    def __setstate__(self, state: dict):
        self.__init__(**state)  # type: ignore

    def __getstate__(self) -> dict:
        state = super().__getstate__()
        if self.logging:
            state['logging'] = self.logging
        return state

    def __repr__(self):
        return mapping_repr(self._val, logging=self.logging)
