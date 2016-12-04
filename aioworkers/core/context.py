import asyncio
from collections import Mapping

from .base import AbstractEntity
from ..core.loader import load_entities
from ..utils import import_name


class Context(AbstractEntity, Mapping):
    async def init(self):
        self._entities = {}
        self._on_stop = []

        await load_entities(
            self.config, context=self, loop=self.loop,
            entities=self._entities)

        inits = []
        for i in self._entities.values():
            inits.append(i.init())
            if hasattr(i, 'stop'):
                self._on_stop.append(i.stop())
        if inits:
            await asyncio.wait(inits, loop=self.loop)

    async def stop(self):
        if self._on_stop:
            await asyncio.wait(self._on_stop, loop=self.loop)

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
