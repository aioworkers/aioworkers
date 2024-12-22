import os
from abc import abstractmethod
from typing import Any, Callable, List, Protocol, Tuple, Type, TypeVar, Union

from ..utils import import_name
from .base import AbstractEntity


class BaseFormatter:
    name: str = NotImplemented
    mimetypes: Tuple[str, ...] = ()

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


TBaseFormatter = TypeVar('TBaseFormatter', bound=BaseFormatter)


class PFormatter(Protocol):
    def encode(self, value: Any) -> Any: ...
    def decode(self, value: Any) -> Any: ...


class PTypesFormatter(PFormatter):
    mimetypes: Tuple[str, ...]


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

    def get(self, name: str) -> BaseFormatter:  # type: ignore
        key: Union[str, List[str]] = name
        if not name or name == "bytes":
            return AsIsFormatter()
        elif not isinstance(name, str):
            pass
        elif name in self:
            return self[name]()
        elif ':' in name:
            key = name.split(":")
        elif '|' in name:
            key = name.split("|")
        else:
            a = self
            while a._parent is not None:
                a = a._parent
                if name in a:
                    return a[name]()
            raise KeyError(name)

        if isinstance(key, list):
            return ChainFormatter(self.get(i.strip()) for i in key)
        else:
            raise KeyError(name)


class StringFormatter(BaseFormatter):
    name = 'str'
    mimetypes = (
        'text/plain',
        'text/plain; charset=utf-8',
    )

    def decode(self, b):
        return b.decode("utf-8")

    def encode(self, b):
        return b.encode("utf-8")


class FromStringFormatter(BaseFormatter):
    name = 'from_str'

    @staticmethod
    def decode(b):
        return b.encode("utf-8")

    @staticmethod
    def encode(b):
        return b.decode("utf-8")


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
    linesep = os.linesep.encode("utf-8")  # type: ignore


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
    mimetypes = ('application/json',)
    converters: List[Tuple[float, Union[Type, str], Callable]] = [
        (0, 'aioworkers.core.config.ValueExtractor', dict),
    ]
    _dumps: Callable
    _loads: Callable

    def __init__(self):
        import json

        convs: List[Tuple[float, Type, Callable]] = []
        for score, klass, conv in self.converters:
            if isinstance(klass, str):
                klass = import_name(klass)
            assert isinstance(klass, type)
            convs.append((score, klass, conv))

        class Encoder(json.JSONEncoder):
            def default(self, o):
                for _score, klass, conv in convs:
                    if isinstance(o, klass):
                        return conv(o)
                return super().default(o)

        self._encoder = Encoder
        setattr(self, "_loads", json.loads)  # noqa: B010
        setattr(self, "_dumps", json.dumps)  # noqa: B010

    def decode(self, b):
        return self._loads(b.decode("utf-8"))

    def encode(self, b):
        return self._dumps(b, cls=self._encoder).encode("utf-8")

    @classmethod
    def add_converter(cls, klass, conv, score=0):
        """Add converter
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
    mimetypes = ('application/x-yaml',)

    def __init__(self):
        import yaml

        Loader = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
        setattr(self, "_loads", lambda x: yaml.load(x, Loader))  # noqa: B010
        setattr(self, "_dumps", yaml.dump)  # noqa: B010

    def encode(self, b):
        return self._dumps(b).encode("utf-8")


class ZLibFormatter(BaseFormatter):
    name = 'zlib'

    def __init__(self):
        zlib = __import__('zlib')
        setattr(self, "decode", zlib.decompress)  # noqa: B010
        setattr(self, "encode", zlib.compress)  # noqa: B010


class LzmaFormatter(BaseFormatter):
    name = 'lzma'

    def __init__(self):
        lzma = __import__('lzma')
        FILTER_LZMA2 = lzma.FILTER_LZMA2
        filters = [{'id': FILTER_LZMA2}]
        FORMAT_RAW = lzma.FORMAT_RAW
        setattr(  # noqa: B010
            self,
            'encode',
            lambda v: lzma.compress(
                v,
                format=FORMAT_RAW,
                filters=filters,
            ),
        )
        setattr(  # noqa: B010
            self,
            'decode',
            lambda v: lzma.decompress(
                v,
                format=FORMAT_RAW,
                filters=filters,
            ),
        )


class MsgPackFormatter(BaseFormatter):
    name = 'msgpack'

    def __init__(self):
        msgpack = __import__('msgpack')
        setattr(self, "decode", msgpack.loads)  # noqa: B010
        setattr(self, "encode", msgpack.dumps)  # noqa: B010


class BsonFormatter(BaseFormatter):
    name = 'bson'

    def __init__(self):
        bson = __import__('bson')
        setattr(self, "decode", bson.loads)  # noqa: B010
        setattr(self, "encode", bson.dumps)  # noqa: B010


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
registry(MsgPackFormatter)
registry(BsonFormatter)


class FormattedEntity(AbstractEntity):
    registry = registry

    def __init__(self, *args, **kwargs):
        self._formatter: BaseFormatter = self.registry.get(kwargs.get("format") or "")
        super().__init__(*args, **kwargs)

    def set_config(self, config):
        super().set_config(config)
        self._formatter = self.registry.get(self.config.get("format") or "")

    def decode(self, b):
        return self._formatter.decode(b)

    def encode(self, b):
        return self._formatter.encode(b)
