import importlib
import logging
import re
from pathlib import Path


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
            if type(v) is dict:
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

        is_dict = type(value) is dict or \
                  isinstance(value, MergeDict)

        if '.' in key:
            *path, z = key.split('.')

            d = self
            for k in path:
                if k not in d or not isinstance(d[k], dict):
                    d[k] = type(self)()
                d = d[k]

            if replace and is_dict:
                d[z] = type(self)(value)
            elif replace or not is_dict or \
                    z not in d or not isinstance(d[z], dict):
                d[z] = value
            else:
                d[z].update(value)

        elif not replace and is_dict and \
                key in self and isinstance(self[key], type(self)):
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
        except:
            return default

    def __getitem__(self, item):
        if '.' in item:
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
        except KeyError:
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


class ConfigFileLoader:
    extensions = ()

    def load_fd(self, fd):
        raise NotImplementedError

    def load_path(self, path):
        raise NotImplementedError


class YamlLoader(ConfigFileLoader):
    extensions = ('.yaml', '.yml')

    def __init__(self, *args, **kwargs):
        self._yaml = importlib.import_module('yaml')

    def load_fd(self, fd):
        return self._yaml.load(fd)


class JsonLoader(ConfigFileLoader):
    extensions = ('.json',)

    def __init__(self, *args, **kwargs):
        self._json = importlib.import_module('json')

    def load_fd(self, fd):
        return self._json.load(fd)


class ValueMatcher:
    def __init__(self, value):
        self._value = value

    @classmethod
    def match(cls, value):
        raise NotImplementedError

    def get_value(self):
        raise NotImplementedError


class IntValueMatcher(ValueMatcher):
    re = re.compile(r'\d+$')
    fn = int

    @classmethod
    def match(cls, value):
        if cls.re.match(value):
            return cls(value)

    def get_value(self):
        return self.fn(self._value)


class FloatValueMatcher(IntValueMatcher):
    re = re.compile(r'\d+\.\d+$')
    fn = float


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
        return self._value.split(',')


class IniLoader(ConfigFileLoader):
    extensions = ('.ini',)
    matchers = (
        IntValueMatcher, FloatValueMatcher,
        MultilineValueMatcher, ListValueMatcher,
    )

    def __init__(self, *args, **kwargs):
        self._configparser = importlib.import_module('configparser')

    def new_configparser(self, **kwargs) -> 'configparser.ConfigParser':
        kwargs.setdefault('allow_no_value', True)
        return self._configparser.ConfigParser(**kwargs)

    def load_fd(self, fd):
        config = self.new_configparser()
        config.read_file(fd)
        return self._convert(config)

    def load_path(self, path):
        config = self.new_configparser()
        config.read(path)
        return self._convert(config)

    def load_str(self, string):
        config = self.new_configparser()
        config.read_string(string)
        return self._convert(config)

    def _replace(self, d, iterfunc=lambda d: d.items()):
        for k, v in iterfunc(d):
            if not v:
                continue
            for matcher in self.matchers:
                m = matcher.match(v)
                if m is not None:
                    v = m.get_value()
                    if isinstance(v, list):
                        self._replace(v, enumerate)
                    d[k] = v
                    break

    def _convert(self, config):
        c = {}
        for i in config.sections():
            d = dict(config[i])
            self._replace(d)
            c[i] = d
        return c


class Config:
    loaders = (
        YamlLoader, JsonLoader, IniLoader,
    )

    def __init__(self, search_dirs=()):
        loaders = {}
        for l in self.loaders:
            ins = l()
            for ext in l.extensions:
                loaders[ext] = ins
        self._loaders = loaders
        self.search_dirs = []
        for i in search_dirs:
            if not isinstance(i, Path):
                i = Path(i)
            self.search_dirs.append(i)
        self.files = []

    def load_conf(self, path, fd, config):
        loader = self._loaders[path.suffix]
        with fd:
            c = loader.load_fd(fd)
        l = 'Config found: {}'.format(path.absolute())
        self.files.append(path)
        logger.info(l)
        if c:
            config(c)
        return config

    def load(self, *filenames, base=None):
        if base is None:
            config = MergeDict()
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
                self.load_conf(fn, fn.open(encoding='utf-8'), config)
            elif hasattr(fn, 'read') and hasattr(fn, 'name'):
                self.load_conf(Path(fn.name), fn, config)
            else:
                raise ValueError(fn)
        for d in self.search_dirs:
            for fn in fns:
                if not Path(d, fn).exists():
                    continue
                f = Path(d, fn)
                self.load_conf(f, f.open(encoding='utf-8'), config)
        return config
