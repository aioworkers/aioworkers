from abc import ABC, abstractmethod

from copy import deepcopy
from functools import partial


class AbstractEntity(ABC):
    def __init__(self, config=None, *, context=None, loop=None):
        self._config = None
        self._context = None
        self._loop = None
        if config is not None:
            self.set_config(config)
        if context is not None:
            self.set_context(context)
        if loop is not None:
            self._loop = loop

    @property
    def config(self):
        return self._config

    def set_config(self, config):
        if self._config is not None:
            raise RuntimeError('Config already set')
        self._config = config

    @property
    def context(self):
        return self._context

    def set_context(self, context):
        if self._context is not None:
            raise RuntimeError('Context already set')
        self._context = context
        self._loop = context.loop

    async def init(self):
        pass

    @property
    def loop(self):
        return self._loop


class AbstractNamedEntity(AbstractEntity):
    def set_config(self, config):
        super().set_config(config)
        self._name = config.name

    @property
    def name(self):
        return self._name


class AbstractNestedEntity(AbstractEntity):
    def __init__(self, config=None, *, context=None, loop=None):
        super().__init__(config, context=context, loop=loop)
        self._children = {}

    def factory(self, item, config=None):
        if item in self._children:
            return self._children[item]
        instance = self._children[item] = type(self)()
        if config is None and self._config is not None:
            config = deepcopy(self._config)
        if config is not None:
            config.name += '.%s' % item
            instance.set_config(config)
        if self._context is not None:
            instance.set_context(self._context)
        return instance

    def __getattr__(self, item):
        if item.startswith('_'):
            raise AttributeError(item)
        return self.factory(item)

    def __getitem__(self, item):
        return self.factory(item)


class AbstractReader(AbstractEntity):
    @abstractmethod  # pragma: no cover
    async def get(self):
        raise NotImplementedError()


class AbstractWriter(AbstractEntity):
    @abstractmethod  # pragma: no cover
    async def put(self, value):
        raise NotImplementedError()


class ExecutorEntity(AbstractEntity):
    PARAM_EXECUTOR = 'executor'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._executor = None

    def _create_executor(self):
        if self._config is None or self._context is None:
            return
        ex = self._config.get(self.PARAM_EXECUTOR)
        if isinstance(ex, int):
            from concurrent.futures import ThreadPoolExecutor
            ex = ThreadPoolExecutor(max_workers=ex)
        elif isinstance(ex, str):
            ex = self._context[ex]
        self._executor = ex

    def set_config(self, config):
        super().set_config(config)
        self._create_executor()

    def set_context(self, context):
        super().set_context(context)
        self._create_executor()

    def run_in_executor(self, f, *args, **kwargs):
        if kwargs:
            f = partial(f, **kwargs)
        return self.loop.run_in_executor(self._executor, f, *args)

    @property
    def executor(self):
        return self._executor
