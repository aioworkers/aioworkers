import asyncio


class AbstractEntity:
    def __init__(self, config, *, context=None, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self.loop = loop
        self._context = context
        self._config = config


class AbstractNamedEntity(AbstractEntity):
    def __init__(self, config, *, context=None, loop=None):
        super().__init__(config, context=context, loop=loop)
        self._name = config.name

    @property
    def name(self):
        return self._name
