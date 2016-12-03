from .base import AbstractEntity


class StringFormatter:
    @staticmethod
    def decode(b):
        return b.decode()

    @staticmethod
    def encode(b):
        return b.encode()


class PickleFormatter:
    def __init__(self):
        import pickle
        self._loads = pickle.loads
        self._dumps = pickle.dumps

    def decode(self, b):
        return self._loads(b)

    def encode(self, b):
        return self._dumps(b)


class JsonFormatter:
    def __init__(self):
        import json
        self._loads = json.loads
        self._dumps = json.dumps

    def decode(self, b):
        return self._loads(b.decode())

    def encode(self, b):
        return self._dumps(b).encode()


class YamlFormatter(JsonFormatter):
    def __init__(self):
        import yaml
        self._loads = yaml.load
        self._dumps = yaml.dump


class AsIsFormatter:
    @staticmethod
    def decode(b):
        return b

    @staticmethod
    def encode(b):
        return b


def get_formatter(name):
    if name == 'str':
        return StringFormatter
    elif name == 'pickle':
        return PickleFormatter()
    elif name == 'json':
        return JsonFormatter()
    elif name == 'yaml':
        return YamlFormatter()
    else:
        return AsIsFormatter


class FormattedEntity(AbstractEntity):
    async def init(self):
        await super().init()
        self._formatter = get_formatter(self.config.get('format'))

    def decode(self, b):
        return self._formatter.decode(b)

    def encode(self, b):
        return self._formatter.encode(b)
