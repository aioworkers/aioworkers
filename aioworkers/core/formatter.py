from abc import abstractmethod

from .base import AbstractEntity


class BaseFormatter:
    name = NotImplemented

    @abstractmethod  # pragma: no cover
    def decode(self, value):
        raise NotImplementedError

    @abstractmethod  # pragma: no cover
    def encode(self, value):
        raise NotImplementedError


class AsIsFormatter(BaseFormatter):
    @staticmethod
    def decode(b):
        return b

    @staticmethod
    def encode(b):
        return b


class ChainFormatter(BaseFormatter):
    def __init__(self, formatters):
        f = tuple(formatters)
        self._f = f
        self._r = tuple(reversed(f))

    def decode(self, b):
        for f in self._r:
            b = f.decode(b)
        return b

    def encode(self, b):
        for f in self._f:
            b = f.encode(b)
        return b


class Registry(dict):
    def __call__(self, cls):
        name = cls.name
        if not isinstance(name, str):
            raise ValueError('Expected type string instead %r' % name)
        elif name in self:
            raise ValueError('Duplicate name: %s' % name)
        self[name] = cls

    def get(self, name):
        if not name or name == 'bytes':
            return AsIsFormatter
        elif not isinstance(name, str):
            pass
        elif name in self:
            return self[name]()
        elif ':' in name:
            name = name.split(':')
        elif '|' in name:
            name = name.split('|')

        if isinstance(name, list):
            return ChainFormatter(self.get(i.strip()) for i in name)
        else:
            raise KeyError(name)


class StringFormatter(BaseFormatter):
    name = 'str'

    @staticmethod
    def decode(b):
        return b.decode()

    @staticmethod
    def encode(b):
        return b.encode()


class PickleFormatter(BaseFormatter):
    name = 'pickle'

    def __init__(self):
        import pickle
        self._loads = pickle.loads
        self._dumps = pickle.dumps

    def decode(self, b):
        return self._loads(b)

    def encode(self, b):
        return self._dumps(b)


class JsonFormatter(BaseFormatter):
    name = 'json'

    def __init__(self):
        import json
        self._loads = json.loads
        self._dumps = json.dumps

    def decode(self, b):
        return self._loads(b.decode())

    def encode(self, b):
        return self._dumps(b).encode()


class YamlFormatter(JsonFormatter):
    name = 'yaml'

    def __init__(self):
        import yaml
        self._loads = yaml.load
        self._dumps = yaml.dump


registry = Registry()
registry(StringFormatter)
registry(PickleFormatter)
registry(JsonFormatter)
registry(YamlFormatter)


class FormattedEntity(AbstractEntity):
    async def init(self):
        await super().init()
        self._formatter = registry.get(self.config.get('format'))

    def decode(self, b):
        return self._formatter.decode(b)

    def encode(self, b):
        return self._formatter.encode(b)
