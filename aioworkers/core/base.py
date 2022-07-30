import asyncio
import logging
from abc import ABC, abstractmethod
from functools import partial
from typing import Mapping, Optional

from ..utils import import_name
from .config import ValueExtractor


class AbstractEntity(ABC):
    def __init__(self, config=None, *, context=None, **kwargs):
        self._loop = kwargs.pop('loop', None)
        self._config = ValueExtractor(kwargs)
        self._context = None
        if context is not None:
            self.set_context(context)
        if config is not None:
            self.set_config(config)

    @property
    def config(self):
        return self._config

    def set_config(self, config) -> None:
        if isinstance(config, ValueExtractor):
            pass
        elif isinstance(config, Mapping):
            config = ValueExtractor(config)
        else:
            raise TypeError('Config must be instance of ValueExtractor')
        self._config = config.new_parent(self._config)

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

    def _set_loop(self, loop):
        self._loop = loop

    @property
    def loop(self):
        return self._loop


class AbstractNamedEntity(AbstractEntity):
    def set_config(self, config) -> None:
        super().set_config(config)
        self._name = config.name

    @property
    def name(self):
        return self._name


class AbstractNestedEntity(AbstractEntity):
    cache_factory = dict
    item_factory = None

    def __init__(self, config=None, **kwargs):
        self._children = self.cache_factory()
        super().__init__(config, **kwargs)

    def set_context(self, context):
        super().set_context(context)
        for i in self._children.values():
            i.set_context(context)

    def set_config(self, config) -> None:
        super().set_config(config)
        for k, v in self._children.items():
            c = self.get_child_config(k)
            v.set_config(c)
        for k, v in self._config.items():
            if k == 'child' or k in self._children:
                continue
            elif isinstance(v, ValueExtractor):
                self.factory(k, v)

    async def init(self):
        await super().init()
        if self._children:
            await self.context.wait_all(
                [c.init() for c in self._children.values()],
            )

    def get_child_config(
        self,
        item: str,
        config: Optional[ValueExtractor] = None,
    ) -> Optional[ValueExtractor]:
        if config is not None:
            c = config
        elif self._config is None:
            return None
        else:
            c = self._config
            for i in (item, 'child'):
                ci = self._config.get(i)
                if isinstance(ci, ValueExtractor) and 'cls' in ci:
                    c = ci
                    break
        return c.new_child(
            name='{}.{}'.format(self._config.name, item),
        )

    def factory(self, item, config=None):
        instance = self._children.get(item)
        if instance is not None:
            return instance

        c = self.get_child_config(item, config)
        assert c
        str_cls = c.get('cls')
        if str_cls is None or str_cls is self._config.cls:
            cls = self.item_factory or type(self)
        else:
            cls = import_name(str_cls)
        if isinstance(c, ValueExtractor):
            c = c
        else:
            return
        instance = self._children[item] = cls(c)

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
        self._executor = None
        super().__init__(*args, **kwargs)

    @property
    def loop(self):
        if not self._loop:
            self._loop = asyncio.get_event_loop()
        return self._loop

    def executor_factory(self, *args, **kwargs):
        from concurrent.futures import ThreadPoolExecutor

        return ThreadPoolExecutor(*args, **kwargs)

    def _create_executor(self):
        if self._config is None or self._context is None:
            return
        ex = self._config.get(self.PARAM_EXECUTOR)
        if isinstance(ex, int):
            ex = self.executor_factory(max_workers=ex)
        elif isinstance(ex, str):
            ex = self._context.get(ex)
        self._executor = ex

    def set_config(self, config) -> None:
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


class MultiExecutorEntity(AbstractEntity):
    def __init__(self, *args, **kwargs):
        self._executors = {}
        super().__init__(*args, **kwargs)

    @property
    def loop(self):
        if not self._loop:
            self._loop = asyncio.get_event_loop()
        return self._loop

    def executor_factory(self, *args, **kwargs):
        from concurrent.futures import ThreadPoolExecutor

        return ThreadPoolExecutor(*args, **kwargs)

    async def init(self):
        executors_params = self.config.get('executors', default={})
        for executor_name, p in executors_params.items():
            if isinstance(p, int):
                ex = self.executor_factory(max_workers=p)
            elif isinstance(p, str):
                ex = self.context.get(p)
            else:
                ex = self.executor_factory()
            self._executors[executor_name] = ex

    def run_in_executor(self, name: str, f, *args, **kwargs):
        executor = self._executors[name]
        if kwargs:
            f = partial(f, **kwargs)
        return self.loop.run_in_executor(executor, f, *args)


class NameLogger(logging.LoggerAdapter):
    @classmethod
    def from_instance(cls, logger, instance):
        return cls(
            logger,
            {
                'name': instance.config.name,
            },
        )

    def process(self, msg, kwargs):
        return '[{}] {}'.format(self.extra['name'], msg), kwargs


class LoggingEntity(AbstractNamedEntity):
    logging_adapter = NameLogger
    logger = logging.getLogger('aioworkers')

    def set_config(self, config) -> None:
        super().set_config(config)
        logger = logging.getLogger(self.config.get('logger', 'aioworkers'))
        self.logger = self.logging_adapter.from_instance(logger, self)


class AbstractConnector(LoggingEntity):
    async def init(self):
        await super().init()
        groups = self.config.get('groups')
        self.context.on_connect.append(self.robust_connect, groups)
        self.context.on_disconnect.append(self.disconnect, groups)
        self.context.on_cleanup.append(self.cleanup, groups)

    async def robust_connect(self):
        while True:
            try:
                await self.connect()
            except asyncio.CancelledError:
                break
            except Exception:
                self.logger.exception('Connect error')
                await asyncio.sleep(3)
                self.logger.debug('Try reconnect')
            else:
                break

    @abstractmethod
    async def connect(self):
        raise NotImplementedError()

    @abstractmethod
    async def disconnect(self):
        raise NotImplementedError()

    async def cleanup(self):
        pass
