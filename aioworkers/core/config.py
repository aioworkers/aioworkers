from pathlib import Path
import logging

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


def yaml_loader(fd=None, filename=None, search_dirs=(), encoding='utf-8'):
    import yaml
    if fd is not None:
        return yaml.load(fd)


def json_loader(fd=None, filename=None, search_dirs=(), encoding='utf-8'):
    import json
    if fd is not None:
        return json.load(fd)


def ini_loader(fd=None, filename=None, search_dirs=(), encoding='utf-8'):
    import configparser
    config = configparser.ConfigParser(allow_no_value=True)
    if fd is not None:
        config.read_file(fd)
    else:
        return
    c = {}
    for i in config.sections():
        c[i] = dict(config[i])
    return c


class Config:
    def __init__(self, search_dirs=()):
        self.loaders = {
            '.yaml': yaml_loader,
            '.yml': yaml_loader,
            '.json': json_loader,
            '.ini': ini_loader,
        }
        self.search_dirs = []
        for i in search_dirs:
            if not isinstance(i, Path):
                i = Path(i)
            self.search_dirs.append(i)
        self.files = []

    def load_conf(self, path, fd, config):
        loader = self.loaders[path.suffix]
        with fd:
            c = loader(fd, search_dirs=self.search_dirs)
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
