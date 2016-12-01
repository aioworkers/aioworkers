from collections import Mapping

from .base import AbstractEntity
from ..utils import import_name


class Context(AbstractEntity, Mapping):
    def __getitem__(self, item):
        if item is None:
            return
        elif isinstance(item, str):
            try:
                return self._config[item]
            except:
                pass
            try:
                return import_name(item)
            except:
                pass
        elif isinstance(item, Mapping):
            if 'func' in item:
                func = import_name(item['func'])
                args = item.get('args', ())
                kwargs = item.get('kwargs', {})
                return func(*args, **kwargs)
        raise KeyError(item)

    def __getattr__(self, item):
        try:
            return self._config[item]
        except KeyError:
            raise AttributeError(item)

    def __iter__(self):
        pass

    def __len__(self):
        pass
