import asyncio
import contextlib
import inspect
import logging.config
from collections import Mapping, MutableMapping, OrderedDict

from ..utils import import_name
from .base import AbstractConnector, AbstractEntity


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
            try:
                v = self[k]
            except Exception:
                raise KeyError(key)
        if len(sp) == 1:
            return v
        if isinstance(v, Octopus):
            return v._get_item(sp[-1], create)
        try:
            return getattr(v, sp[-1])
        except AttributeError:
            return v[sp[-1]]

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

    def find_iter(self, cls):
        for pp, obj in self.items():
            if isinstance(obj, Octopus):
                for pc, obj in obj.find_iter(cls):
                    yield '.'.join((pp, pc)), obj
            elif isinstance(obj, cls):
                yield pp, obj


class Signal:
    def __init__(self, context, name=None):
        self._signals = []
        self._context = context
        self._name = name

    def append(self, signal, groups=None):
        if groups:
            groups = {str(g) for g in groups}
        self._signals.append((signal, groups))

    def _send(self, group_resolver):
        coros = []
        for i, g in self._signals:
            if not group_resolver.match(g):
                continue
            if asyncio.iscoroutinefunction(i):
                params = inspect.signature(i).parameters
                if 'context' in params:
                    coro = i(self._context)
                else:
                    coro = i()
            elif asyncio.iscoroutine(i):
                coro = i
            elif callable(i):
                params = inspect.signature(i).parameters
                if 'context' in params:
                    i(self._context)
                else:
                    i()
                continue
            else:
                continue
            coros.append(coro)
        return coros

    def send(self, group_resolver, *, coroutine=True):
        coros = self._send(group_resolver)
        if coroutine:
            return self._context.wait_all(coros)


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
    key = 'logging'
    process = None

    @classmethod
    def match(cls, context, path, value):
        if path == cls.key and value and isinstance(value, Mapping):
            m = cls(context, path, value)
            m.configure(value)
            return m

    def configure(self, value):
        logging.config.dictConfig(value)


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
        if not isinstance(cls, AbstractEntity):
            try:
                signature = inspect.signature(cls)
                signature.bind(config=None, context=None, loop=None)
            except TypeError as e:
                raise TypeError(
                    'Error while creating entity on {} from {}: {}'.format(
                        path, value[self.key], e))
            except ValueError as e:
                raise ValueError(
                    'Error while checking entity on {} from {}: {}'.format(
                        path, value[self.key], e))
        value = value.new_parent(name=path)
        entity = cls(value, context=context, loop=context.loop)
        context[path] = entity
        self.entity = entity

    @classmethod
    def match(cls, context, path, value):
        if isinstance(value, Mapping) and cls.key in value:
            return cls(context, path, value)

    async def process(self):
        await self.entity.init()


class InstanceEntityContextProcessor(EntityContextProcessor):
    key = 'obj'

    def __init__(self, context, path, value):
        ContextProcessor.__init__(self, context, path, value)
        entity = import_name(value[self.key])
        if isinstance(entity, AbstractEntity):
            value = value.new_parent(name=path)
            entity.set_config(value)
            entity.set_context(context)
        context[path] = entity
        self.entity = entity

    async def process(self):
        if isinstance(self.entity, AbstractEntity):
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
    processors = (
        LoggingContextProcessor,
        GroupsContextProcessor,
        InstanceEntityContextProcessor,
        EntityContextProcessor,
        FuncContextProcessor,
    )

    def __init__(self, context, path=None, value=None):
        super().__init__(context, path, value)
        self._built = False
        self.on_ready = Signal(context, name='ready')
        self.processors = OrderedDict((i.key, i) for i in self.processors)

    def __iter__(self):
        yield from self.processors.values()

    def processing(self, config, path=None):
        for k, v in config.items():
            p = '.'.join(i for i in (path, k) if i)
            for processor in self:
                m = processor.match(self.context, p, v)
                if m is None:
                    continue
                if m.process:
                    groups = None
                    if isinstance(v, Mapping):
                        groups = v.get('groups')
                    self.on_ready.append(m.process, groups)
                break
            else:
                if isinstance(v, Mapping):
                    self.processing(v, p)

    def build(self, config):
        if not self._built:
            self.value = config
            self.processing(self.value)
            self._built = True

    async def process(self, config=None):
        self.build(config)
        await self.on_ready.send(self.context._group_resolver)


class Context(AbstractConnector, Octopus):
    def __init__(self, *args, **kwargs):
        self._group_resolver = kwargs.pop('group_resolver', GroupResolver())
        self._on_connect = Signal(self, name='connect')
        self._on_start = Signal(self, name='start')
        self._on_stop = Signal(self, name='stop')
        self._on_disconnect = Signal(self, name='disconnect')
        self._on_cleanup = Signal(self, name='cleanup')
        self.logger = logging.getLogger('aioworkers')
        root_processor = kwargs.pop('root_processor', RootContextProcessor)
        self.processors = root_processor(self)
        super().__init__(*args, **kwargs)

    def set_group_resolver(self, gr):
        self._group_resolver = gr

    def set_loop(self, loop):
        if self._loop is not None:
            raise RuntimeError('Loop already set')
        self._set_loop(loop)
        for path, obj in self.find_iter(AbstractEntity):
            obj._set_loop(loop)

    @contextlib.contextmanager
    def processes(self):
        gr = GroupResolver(all_groups=True)
        self.set_group_resolver(gr)
        self.processors.build(self.config)
        yield
        self.on_cleanup.send(gr, coroutine=False)

    @property
    def on_connect(self):
        return self._on_connect

    @property
    def on_start(self):
        return self._on_start

    @property
    def on_stop(self):
        return self._on_stop

    @property
    def on_disconnect(self):
        return self._on_disconnect

    @property
    def on_cleanup(self):
        return self._on_cleanup

    async def init(self):
        if self._loop is None:
            self.set_loop(asyncio.get_event_loop())
        await self.processors.process(self.config)

    async def wait_all(self, coros, timeout=None):
        if not coros:
            return
        d, p = await asyncio.wait(coros, loop=self.loop, timeout=timeout)
        assert not p, '\n'.join(map(repr, p))
        for f in d:
            if f.exception():
                self.logger.exception('ERROR', exc_info=f.exception())

    async def connect(self):
        await self.on_connect.send(self._group_resolver)

    async def start(self):
        await self.on_start.send(self._group_resolver)

    async def stop(self):
        await self.on_stop.send(self._group_resolver)

    async def disconnect(self):
        await self.on_disconnect.send(self._group_resolver)

    def run_forever(self):
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass
        self.loop.close()

    def __getitem__(self, item):
        if item is None:
            return
        elif isinstance(item, str):
            try:
                return super().__getitem__(item)
            except Exception:
                pass
            try:
                return self._config[item]
            except Exception:
                pass
            try:
                return import_name(item)
            except Exception:
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
        if self._loop is None:
            self.set_loop(asyncio.get_event_loop())
        self.loop.run_until_complete(self.init())
        self.loop.run_until_complete(self.connect())
        self.loop.run_until_complete(self.start())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.loop.run_until_complete(self.stop())
        self.loop.run_until_complete(self.disconnect())
        self.loop.run_until_complete(
            self._on_cleanup.send(self._group_resolver)
        )

    async def __aenter__(self):
        await self.init()
        await self.connect()
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        await self.disconnect()
        await self._on_cleanup.send(self._group_resolver)

    def get_object(self, path):
        if path.startswith('.'):
            return self[path[1:]]
        return import_name(path)
