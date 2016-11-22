import asyncio
from abc import ABC


class AbstractEntity(ABC):
    def __init__(self, config, *, context=None, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self._context = context
        self._config = config

    async def init(self):
        pass

    @property
    def loop(self):
        return self._loop

    @property
    def config(self):
        return self._config

    @property
    def context(self):
        return self._context


class AbstractNamedEntity(AbstractEntity):
    def __init__(self, config, *, context=None, loop=None):
        super().__init__(config, context=context, loop=loop)
        self._name = config.name

    @property
    def name(self):
        return self._name
