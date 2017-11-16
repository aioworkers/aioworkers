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
        exclude = groups.intersection(self._exclude)
        include = groups.intersection(self._include)
        if self._all:
            if exclude:
                return ()
        else:
            if not include:
                return ()
        return groups


class ContextProcessor:
    def __init__(self, context, path, value):
        self.context = context
        self.path = path
        self.value = value

    @classmethod
    def match(cls, context, path, value):
        raise NotImplementedError

    async def process(self):
        raise NotImplementedError


class LoggingContextProcessor(ContextProcessor):
    process = None

    @classmethod
    def match(cls, context, path, value):
        if path == 'logging' and isinstance(value, Mapping):
            logging.config.dictConfig(value)
            return cls(context, path, value)


class GroupsContextProcessor(ContextProcessor):
    key = 'groups'
    process = None

    @classmethod
    def match(cls, context, path, value):
        if not isinstance(value, Mapping):
            return
        groups = value.get(cls.key)
        if not context._group_resolver.match(groups):
            return cls(context, path, value)


class EntityContextProcessor(ContextProcessor):
    key = 'cls'

    def __init__(self, context, path, value):
        super().__init__(context, path, value)
        cls = import_name(value[self.key])
        value.setdefault('name', path)
        entity = cls(value, context=context, loop=context.loop)
        context[path] = entity
        self.entity = entity

    @classmethod
    def match(cls, context, path, value):
        if isinstance(value, Mapping) and cls.key in value:
            return cls(context, path, value)

    async def process(self):
        await self.entity.init()


class FuncContextProcessor(ContextProcessor):
    key = 'func'
    process = None

    def __init__(self, context, path, value):
        super().__init__(context, path, value)
        func = import_name(value[self.key])
        args = value.get('args', ())
        kwargs = value.get('kwargs', {})
        context[path] = func(*args, **kwargs)

    @classmethod
    def match(cls, context, path, value):
        if isinstance(value, Mapping) and cls.key in value:
            return cls(context, path, value)


class RootContextProcessor(ContextProcessor):
    key = 'app'
    key_class = 'app.cls'
    processors = (
        LoggingContextProcessor,
        GroupsContextProcessor,
        EntityContextProcessor,
        FuncContextProcessor,
    )

    def __init__(self, context, path=None, value=None):
        super().__init__(context, path, value)
        self.on_ready = Signal(context, name='ready')

    def __iter__(self):
        yield type(self)
        yield from self.processors

    @classmethod
    def match(cls, context, path, value):
        if isinstance(value, Mapping) and value.get(cls.key_class):
            nested_context = Context(value, loop=context.loop)
            context.on_start.append(nested_context.start)
            context.on_stop.append(nested_context.stop)
            context[path] = nested_context
            return cls(nested_context, config=value)

    def _path(self, base, key):
        if not base:
            return key
        return '.'.join((base, key))

    def processing(self, config, path=None):
        for k, v in config.items():
            if k == self.key and not path:
                continue
            p = self._path(path, k)
            for processor in self:
                m = processor.match(self.context, p, v)
                if m is None:
                    continue
                if m.process:
                    self.on_ready.append(m.process)
                break
            else:
                if isinstance(v, Mapping):
                    self.processing(v, p)

    async def process(self):
        strcls = self.value.get(self.key_class)
        if strcls:
            cls = import_name(strcls)
            app = await cls.factory(
                config=self.value,
                context=self.context,
                loop=self.context.loop)
            self.context.app = app
        self.processing(self.value)
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
        await RootContextProcessor(self, value=self.config).process()

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

    def __enter__(self):
        self.loop.run_until_complete(self.init())
        self.loop.run_until_complete(self.start())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.loop.run_until_complete(self.stop())

    async def __aenter__(self):
        await self.init()
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
