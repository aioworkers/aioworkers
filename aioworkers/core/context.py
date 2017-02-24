import asyncio
import logging
from collections import Mapping

from .base import AbstractEntity
from ..core.loader import load_entities
from ..utils import import_name


class Context(AbstractEntity, Mapping):
    def __init__(self, *args, **kwargs):
        self._entities = {}
        self.on_start = []
        self.on_stop = []
        self.logger = logging.getLogger('aioworkers')
        super().__init__(*args, **kwargs)

    async def init(self):
        await load_entities(
            self.config, context=self, loop=self.loop,
            entities=self._entities)

        inits = []
        for i in self._entities.values():
            inits.append(i.init())
            if hasattr(i, 'stop'):
                self.on_stop.append(i.stop())
        await self.wait_all(inits)

    async def wait_all(self, coros):
        if not coros:
            return
        d, p = await asyncio.wait(coros, loop=self.loop)
        assert not p
        for f in d:
            if f.exception():
                self.logger.exception('ERROR', exc_info=f.exception())

    async def start(self):
        await self.wait_all(self.on_start)

    async def stop(self):
        await self.wait_all(self.on_stop)

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

    def __dir__(self):
        r = list(self.config)
        r.extend(super().__dir__())
        return r

    def __getattr__(self, item):
        try:
            return self._config[item]
        except KeyError:
            raise AttributeError(item)

    def __iter__(self):
        pass

    def __len__(self):
        pass
