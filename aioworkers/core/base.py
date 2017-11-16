import asyncio
from abc import ABC
from copy import deepcopy


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


class AbstractNestedEntity(AbstractEntity):
    def __init__(self, config, *, context=None, loop=None):
        super().__init__(config, context=context, loop=loop)
        self._children = {}

    def factory(self, item, config=None):
        if item in self._children:
            return self._children[item]
        cls = type(self)
        if config is None:
            config = deepcopy(self.config)
        config.name += '.%s' % item
        instance = cls(config, context=self.context, loop=self.loop)
        self._children[item] = instance
        return instance

    def __getattr__(self, item):
        if item.startswith('_'):
            raise AttributeError(item)
        return self.factory(item)

    def __getitem__(self, item):
        return self.factory(item)
