import os
from abc import abstractmethod

from ..utils import import_name
from .base import AbstractEntity


class BaseFormatter:
    name = NotImplemented
    mimetypes = ()

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
    _parent = None

    @classmethod
    def new(cls):
        return cls()

    def new_child(self):
        instance = self.new()
        instance._parent = self
        return instance

    def __call__(self, cls):
        name = cls.name
        if not isinstance(name, str):
            raise ValueError('Expected type string instead %r' % name)
        elif name in self:
            raise ValueError('Duplicate name: %s' % name)
        self[name] = cls
        for mime in cls.mimetypes:
            self[mime] = cls

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
        else:
            a = self
            while a._parent is not None:
                a = a._parent
                if name in a:
                    return a[name]()
            raise KeyError(name)

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


class FromStringFormatter(BaseFormatter):
    name = 'from_str'

    @staticmethod
    def decode(b):
        return b.encode()

    @staticmethod
    def encode(b):
        return b.decode()


class NewLineFormatter(BaseFormatter):
    name = 'newline'
    linesep = os.linesep  # type: str

    @staticmethod
    def decode(b):
        return b.rstrip()

    @classmethod
    def encode(cls, b):
        return b + cls.linesep


class BytesNewLineFormatter(NewLineFormatter):
    name = 'bnewline'
    linesep = os.linesep.encode()  # type: ignore


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
    mimetypes = ('application/json',)  # type: ignore
    converters = [
        (0, 'aioworkers.core.config.ValueExtractor', dict),
    ]

    def __init__(self):
        import json
        convs = []
        for score, klass, conv in self.converters:
            if isinstance(klass, str):
                klass = import_name(klass)
            convs.append((score, klass, conv))

        class Encoder(json.JSONEncoder):
            def default(self, o):
                for score, klass, conv in convs:
                    if isinstance(o, klass):
                        return conv(o)
                return super().default(o)

        self._encoder = Encoder
        self._loads = json.loads
        self._dumps = json.dumps

    def decode(self, b):
        return self._loads(b.decode())

    def encode(self, b):
        return self._dumps(b, cls=self._encoder).encode()

    @classmethod
    def add_converter(cls, klass, conv, score=0):
        """ Add converter
        :param klass: class or str
        :param conv: callable
        :param score:
        :return:
        """
        if isinstance(klass, str):
            klass = import_name(klass)
        item = klass, conv, score
        cls.converters.append(item)
        cls.converters.sort(key=lambda x: x[0])
        return cls


class YamlFormatter(JsonFormatter):
    name = 'yaml'

    def __init__(self):
        import yaml
        Loader = getattr(yaml, 'CLoader', yaml.Loader)
        self._loads = lambda x: yaml.load(x, Loader)
        self._dumps = yaml.dump

    def encode(self, b):
        return self._dumps(b).encode()


class ZLibFormatter(BaseFormatter):
    name = 'zlib'

    def __init__(self):
        zlib = __import__('zlib')
        self.decode = zlib.decompress
        self.encode = zlib.compress


class LzmaFormatter(BaseFormatter):
    name = 'lzma'

    def __init__(self):
        lzma = __import__('lzma')
        FILTER_LZMA2 = lzma.FILTER_LZMA2
        filters = [{'id': FILTER_LZMA2}]
        FORMAT_RAW = lzma.FORMAT_RAW
        self.encode = lambda v: lzma.compress(
            v, format=FORMAT_RAW, filters=filters)
        self.decode = lambda v: lzma.decompress(
            v, format=FORMAT_RAW, filters=filters)


registry = Registry()
registry(StringFormatter)
registry(FromStringFormatter)
registry(NewLineFormatter)
registry(BytesNewLineFormatter)
registry(PickleFormatter)
registry(JsonFormatter)
registry(YamlFormatter)
registry(ZLibFormatter)
registry(LzmaFormatter)


class FormattedEntity(AbstractEntity):
    registry = registry
    _formatter = None

    def set_config(self, config):
        super().set_config(config)
        self._formatter = self.registry.get(self.config.get('format'))

    def decode(self, b):
        return self._formatter.decode(b)

    def encode(self, b):
        return self._formatter.encode(b)
