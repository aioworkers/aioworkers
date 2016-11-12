from pathlib import Path


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
        if item in self:
            return self[item]
        raise AttributeError(item)

    def __setattr__(self, key, value):
        self[key] = value

    def __setitem__(self, key, value):
        replace = key.endswith('!')
        if replace:
            key = key.strip('!')

        is_dict = isinstance(value, dict)

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

    def get(self, key, default=None):
        if '.' in key:
            d = self
            path = key.split('.')
            for k in path:
                try:
                    d = d[k]
                except:
                    return default
        else:
            return super().get(key, default)

    def __call__(self, *args, **kwargs):
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v


def yaml_loader(filename: Path, search_dirs=(), encoding='utf-8'):
    import yaml
    with filename.open(encoding=encoding) as f:
        return yaml.load(f)


def json_loader(filename: Path, search_dirs=(), encoding='utf-8'):
    import json
    with filename.open(encoding=encoding) as f:
        return json.load(f)


class Config:
    def __init__(self, search_dirs=()):
        self.loaders = {
            '.yaml': yaml_loader,
            '.json': json_loader,
        }
        self.search_dirs = [Path(i) for i in search_dirs]

    def load(self, *filenames):
        config = MergeDict()
        fns = []
        for fn in filenames:
            if isinstance(fn, str):
                fn = Path(fn)
            if not fn.is_absolute():
                fns.append(fn)
                continue
            loader = self.loaders[fn.suffix]
            c = loader(fn, search_dirs=self.search_dirs)
            if c:
                config(c)
        for d in self.search_dirs:
            for fn in fns:
                f = d / fn
                if not f.exists():
                    continue
                loader = self.loaders[fn.suffix]
                c = loader(f, search_dirs=self.search_dirs)
                if c:
                    config(c)
        return config
