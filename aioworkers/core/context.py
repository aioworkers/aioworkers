import asyncio
import inspect
import logging.config
from collections import Mapping, MutableMapping

from .base import AbstractEntity
from ..utils import import_name


class Octopus(MutableMapping):
    def _create_item(self):
        return Octopus()

    def _get_item(self, key, create):
        sp = key.split('.', 1)
        k = sp[0]
        if k in self.__dict__:
            v = self.__dict__[k]
        elif create:
            v = self._create_item()
            self[k] = v
        else:
            raise KeyError(key)
        if len(sp) == 1:
            return v
        return v._get_item(sp[-1], create)

    def items(self):
        return self.__dict__.items()

    def __getitem__(self, key):
        if not isinstance(key, str):
            return
        return self._get_item(key, False)

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            return
        sp = key.rsplit('.', 1)
        if len(sp) == 2:
            f = self._get_item(sp[0], True)
        else:
            f = self
        setattr(f, sp[-1], value)

    def __delitem__(self, key):  # pragma: no cover
        pass

    def __iter__(self):  # pragma: no cover
        pass

    def __len__(self):  # pragma: no cover
        return len(self.__dict__)

    def __repr__(self, *, indent=1, header=False):
        result = []
        if header:
            result.extend(['  ' * indent, '<', self.__class__.__name__, '>\n'])
            indent += 1

        for k, v in sorted(self.__dict__.items()):
            if k.startswith('_'):
                continue
            result.append('  ' * indent)
            result.append(k)
            result.append(': ')
            if isinstance(v, Octopus):
                result.append('\n')
                result.append(v.__repr__(indent=indent + 1, header=False))
            else:
                result.append(str(v))
                result.append('\n')
        return ''.join(result)


class Signal:
    def __init__(self, context, name=None):
        self._signals = []
        self._context = context
        self._name = name

    def append(self, signal, groups=None):
        if groups:
            groups = {str(g) for g in groups}
        self._signals.append((signal, groups))

    async def send(self, group_resolver):
        coros = []
        for i, g in self._signals:
            if not group_resolver.match(g):
                continue
            if asyncio.iscoroutinefunction(i):
                params = inspect.signature(i).parameters
                if 'app' in params:
                    coro = i(self._context.app)
                elif 'context' in params:
                    coro = i(self)
                else:
                    coro = i()
            elif asyncio.iscoroutine(i):
                coro = i
            else:
                continue
            coros.append(coro)
        await self._context.wait_all(coros)


class GroupResolver:
    def __init__(
        self,
        include=None,
        exclude=None,
        all_groups=False,
        default=True,
    ):
        self._include = frozenset(include or ())
        self._exclude = frozenset(exclude or ())
        self._all = all_groups
        self._default = default

    def match(self, groups):
        if not groups:
            return self._default
        groups = {str(e) for e in groups}
        if self._exclude:
            groups -= self._exclude
        if self._all:
            pass
        elif self._include:
            groups = groups.intersection(self._include)
        else:
            groups = ()
        return groups


class ContextProcessor:
    def __init__(self, context, path, config):
        self.context = context
        self.path = path
        self.config = config

    @classmethod
    def match(cls, context, path, config):
        raise NotImplementedError

    async def process(self):
        raise NotImplementedError


class NotMappingContextProcessor(ContextProcessor):
    process = None

    @classmethod
    def match(cls, context, path, config):
        if not isinstance(config, Mapping):
            return cls(context, path, config)


class LoggingContextProcessor(ContextProcessor):
    process = None

    @classmethod
    def match(cls, context, path, config):
        if path.split('.')[-1] == 'logging':
            logging.config.dictConfig(config)
            return cls(context, path, config)


class GroupsContextProcessor(ContextProcessor):
    key = 'groups'
    process = None

    @classmethod
    def match(cls, context, path, config):
        groups = config.get(cls.key)
        if not context._group_resolver.match(groups):
            return cls(context, path, config)


class EntityContextProcessor(ContextProcessor):
    key = 'cls'

    def __init__(self, context, path, config):
        super().__init__(context, path, config)
        cls = import_name(config[self.key])
        config.setdefault('name', path)
        entity = cls(config, context=context, loop=context.loop)
        context[path] = entity
        self.entity = entity

    @classmethod
    def match(cls, context, path, config):
        if cls.key in config:
            return cls(context, path, config)

    async def process(self):
        await self.entity.init()


class FuncContextProcessor(ContextProcessor):
    key = 'func'
    process = None

    def __init__(self, context, path, config):
        super().__init__(context, path, config)
        func = import_name(config[self.key])
        args = config.get('args', ())
        kwargs = config.get('kwargs', {})
        context[path] = func(*args, **kwargs)

    @classmethod
    def match(cls, context, path, config):
        if cls.key in config:
            return cls(context, path, config)


class RootContextProcessor(ContextProcessor):
    mapping_processors = (
        LoggingContextProcessor,
        GroupsContextProcessor,
        EntityContextProcessor,
        FuncContextProcessor,
    )

    def __init__(self, context, path=None, config=None):
        super().__init__(context, path, config)
        self.processors = \
            (NotMappingContextProcessor, type(self)) + \
            self.mapping_processors
        self.on_ready = Signal(context, name='ready')

    @classmethod
    def match(cls, context, path, config):
        if config.get('app.cls'):
            nested_context = Context(config, loop=context.loop)
            context[path] = nested_context
            return cls(nested_context, config=config)

    def _path(self, base, key):
        if not base:
            return key
        return '.'.join((base, key))

    def processing(self, config, path=None):
        for k, v in config.items():
            if k == 'app' and not path:
                continue
            p = self._path(path, k)
            for processor in self.processors:
                m = processor.match(self.context, p, v)
                if m is None:
                    continue
                if m.process:
                    self.on_ready.append(m.process)
                break
            else:
                self.processing(v, p)

    async def process(self):
        strcls = self.config.get('app.cls')
        if strcls:
            cls = import_name(strcls)
            app = await cls.factory(
                config=self.config,
                context=self.context,
                loop=self.context.loop)
            self.context.app = app
            app.on_startup.append(lambda x: self.context.start())
            app.on_shutdown.append(lambda x: self.context.stop())
        self.processing(self.config)
        await self.on_ready.send(self.context._group_resolver)


class Context(AbstractEntity, Octopus):
    def __init__(self, *args, group_resolver=None, **kwargs):
        self._group_resolver = group_resolver or GroupResolver()
        self._on_start = Signal(self, name='start')
        self._on_stop = Signal(self, name='stop')
        self.logger = logging.getLogger('aioworkers')
        super().__init__(*args, **kwargs)

    @property
    def on_start(self):
        return self._on_start

    @property
    def on_stop(self):
        return self._on_stop

    async def init(self):
        await RootContextProcessor(self, config=self.config).process()

    async def wait_all(self, coros):
        if not coros:
            return
        d, p = await asyncio.wait(coros, loop=self.loop)
        assert not p
        for f in d:
            if f.exception():
                self.logger.exception('ERROR', exc_info=f.exception())

    async def start(self):
        await self.on_start.send(self._group_resolver)

    async def stop(self):
        await self.on_stop.send(self._group_resolver)

    def __getitem__(self, item):
        if item is None:
            return
        elif isinstance(item, str):
            try:
                return super().__getitem__(item)
            except:
                pass
            try:
                return self._config[item]
            except:
                pass
            try:
                return import_name(item)
            except:
                pass
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
