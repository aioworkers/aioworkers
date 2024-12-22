import asyncio
import contextlib
import inspect
import logging.config
import os
from collections import OrderedDict
from functools import wraps
from typing import (
    Any,
    Awaitable,
    Callable,
    FrozenSet,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from ..utils import import_name
from .base import AbstractEntity, NameLogger
from .config import ValueExtractor

T = TypeVar('T')
TSeq = Union[Sequence, Set, FrozenSet]
DOT = '.'


class Octopus(MutableMapping):
    def _create_item(self):
        return Octopus()

    def _get_item(self, key, create):
        sp = key.split(DOT, 1)
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
        sp = key.rsplit(DOT, 1)
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

    def __repr__(self):
        return self.extended_repr()

    def extended_repr(self, *, indent=1, header=False):
        if os.environ.get('AIOWORKERS_MODE') != 'console':
            return '{cls}({id}, attrs=[{attrs}])'.format(
                cls=self.__class__.__name__,
                id=id(self),
                attrs=", ".join(x for x in self.__dict__ if not x.startswith("_")),
            )

        result = []
        if header:
            result.extend(["  " * indent, "<", self.__class__.__name__, ">\n"])
            indent += 1

        for k, v in sorted(self.__dict__.items()):
            if k.startswith('_'):
                continue
            result.append('  ' * indent)
            result.append(k)
            result.append(': ')
            if isinstance(v, Octopus):
                result.append('\n')
                result.append(v.extended_repr(indent=indent + 1, header=False))
            else:
                result.append(str(v))
                result.append('\n')
        return ''.join(result)

    def find_iter(
        self,
        cls: Type[T],
        *,
        exclude: Optional[Set[int]] = None,
    ) -> Iterable[Tuple[str, T]]:
        can_add = False
        if not exclude:
            can_add = True
            exclude = {id(self)}
        for pp, obj in self.items():
            if isinstance(obj, Octopus):
                identy = id(obj)
                if identy in exclude:
                    continue
                if can_add:
                    exclude.add(identy)
                for pc, o in obj.find_iter(cls, exclude=exclude):
                    yield DOT.join((pp, pc)), o
            if isinstance(obj, cls):
                yield pp, obj


class Signal:
    LOG_RUN = "To emit in '%s'"
    LOG_END = "[%s/%s] End for '%s'"
    LOG_EXC = "[%s/%s] End for '%s' with Exception %s"

    def __init__(self, context: 'Context', name: Optional[str] = None):
        self._counter = 0
        self._signals = []  # type: List
        self._context = context
        self._name = name or str(id(self))
        logger_name = "aioworkers.signals"
        if name:
            logger_name += f".{name}"
            name = logger_name
        else:
            name = f"{logger_name}.{self._name}"
        self._logger = NameLogger(
            logging.getLogger(logger_name),
            {"name": name},
        )

    def append(self, signal: Callable, groups: TSeq = ()):
        if groups:
            groups = {str(g) for g in groups}
        self._signals.append((signal, groups))

    async def _run_async(
        self,
        name: str,
        awaitable: Awaitable,
        finish_only: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        if not finish_only:
            self._logger.info(self.LOG_RUN, name)
        if timeout:
            awaitable = asyncio.wait_for(awaitable, timeout=timeout)
        try:
            await awaitable
        except asyncio.TimeoutError as e:
            self._counter += 1
            self._logger.warning(
                self.LOG_EXC,
                self._counter,
                len(self._signals),
                name,
                e,
            )
            raise TimeoutError(f"{self._name} from {name}") from e
        except Exception as e:
            self._counter += 1
            self._logger.warning(
                self.LOG_EXC,
                self._counter,
                len(self._signals),
                name,
                e,
            )
            raise
        else:
            self._counter += 1
            self._logger.info(
                self.LOG_END,
                self._counter,
                len(self._signals),
                name,
            )

    def _run_sync(self, name: str, func: Callable) -> Optional[Awaitable]:
        params = inspect.signature(func).parameters
        self._logger.info(self.LOG_RUN, name)
        try:
            if 'context' in params:
                result = func(self._context)
            else:
                result = func()
        except Exception as e:
            self._counter += 1
            self._logger.warning(
                self.LOG_EXC,
                self._counter,
                len(self._signals),
                name,
                e,
            )
            raise
        if isinstance(result, Awaitable):
            return result
        else:
            self._counter += 1
            self._logger.info(
                self.LOG_END,
                self._counter,
                len(self._signals),
                name,
            )
            return None

    def _send(
        self,
        group_resolver: "GroupResolver",
        timeout: Optional[float] = None,
        coroutine: bool = True,
    ) -> List[Awaitable]:
        self._counter = 0
        errors = []
        coros = []  # type: List
        for i, g in self._signals:
            if not group_resolver.match(g):
                continue
            instance = getattr(i, '__self__', None)
            name = instance and repr(instance) or repr(i)
            if isinstance(instance, AbstractEntity):
                name = instance.config.get('name') or repr(instance)
            if callable(i):
                try:
                    opt_awaitable = self._run_sync(name, i)
                except Exception as e:
                    if coroutine:
                        fut = self._context.loop.create_future()
                        fut.set_exception(e)
                        coro = wraps(i)(lambda x: x)(fut)
                    else:
                        errors.append(e)
                        continue
                else:
                    if opt_awaitable is None:
                        continue
                    elif not coroutine:
                        continue
                    awaitable = self._run_async(
                        name,
                        opt_awaitable,
                        finish_only=True,
                        timeout=timeout,
                    )
                    coro = wraps(i)(lambda x: x)(awaitable)
            elif isinstance(i, Awaitable):
                coro = self._run_async(name, i, timeout=timeout)
            else:
                continue
            coros.append(coro)
        if errors:
            raise errors[0]
        return coros

    def send(
        self,
        group_resolver: "GroupResolver",
        *,
        coroutine: bool = True,
        timeout: Optional[float] = None,
    ):
        coros = self._send(group_resolver, timeout=timeout, coroutine=coroutine)
        if coroutine:
            return self._context.wait_all(coros, raises=True)


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
    key: str

    def __init__(self, context: 'Context', path: str, value: ValueExtractor):
        self.context = context
        self.path = path
        self.value = value

    @classmethod
    def match(cls, context: 'Context', path: str, value: ValueExtractor):
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
        if value:
            cfg = dict(value)
            cfg.setdefault('version', 1)
            logging.config.dictConfig(cfg)


class GroupsContextProcessor(ContextProcessor):
    key = 'groups'
    process = None

    @classmethod
    def match(cls, context, path, value):
        if not isinstance(value, Mapping):
            return
        groups = value.get(cls.key)
        if not context._group_resolver.match(groups):
            assert isinstance(value, ValueExtractor)
            return cls(context, path, value)


class EntityContextProcessor(ContextProcessor):
    key = 'cls'

    def __init__(self, context: 'Context', path: str, value: ValueExtractor):
        super().__init__(context, path, value)
        cls = import_name(value[self.key])
        if issubclass(cls, AbstractEntity):
            entity = cls(None)
        else:
            try:
                signature = inspect.signature(cls)
                signature.bind(config=None, context=None, loop=None)
            except TypeError as e:
                raise TypeError(f"Error while creating entity on {path} from {value[self.key]}: {e}") from e
            except ValueError as e:
                raise ValueError(f"Error while checking entity on {path} from {value[self.key]}: {e}") from e
            entity = cls(value, context=context, loop=context.loop)
        context[path] = entity
        self.entity = entity

    @classmethod
    def match(
        cls,
        context: 'Context',
        path: str,
        value: ValueExtractor,
    ) -> Optional[ContextProcessor]:
        if isinstance(value, Mapping) and cls.key in value:
            return cls(context, path, value)
        return None

    async def process(self):
        await self.entity.init()

    def __repr__(self):
        return self.path


class InstanceEntityContextProcessor(EntityContextProcessor):
    key = 'obj'

    def __init__(self, context: 'Context', path: str, value: ValueExtractor):
        ContextProcessor.__init__(self, context, path, value)
        self.entity = getattr(context, path, None)
        if isinstance(self.entity, AbstractEntity):
            self.entity.set_config(value.new_parent(name=path))
        elif not isinstance(self.entity, Mapping):
            entity = import_name(value[self.key])
            context[path] = entity

    @classmethod
    def match(
        cls,
        context: 'Context',
        path: str,
        value: ValueExtractor,
    ) -> Optional[ContextProcessor]:
        e = context[path]
        if isinstance(e, AbstractEntity):
            return cls(context, path, value)
        else:
            return super().match(context, path, value)

    async def process(self):
        if isinstance(self.entity, AbstractEntity):
            await self.entity.init()


class FuncContextProcessor(ContextProcessor):
    key = 'func'
    process = None

    def __init__(self, context: 'Context', path: str, value: ValueExtractor):
        super().__init__(context, path, value)
        func = import_name(value[self.key])
        args = value.get('args', ())
        kwargs = value.get('kwargs', {})
        context[path] = func(*args, **kwargs)

    @classmethod
    def match(
        cls,
        context: 'Context',
        path: str,
        value: ValueExtractor,
    ) -> Optional[ContextProcessor]:
        if isinstance(value, Mapping) and cls.key in value:
            return cls(context, path, value)
        return None


class RootContextProcessor(ContextProcessor):
    processors: Sequence[Type[ContextProcessor]] = (
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
        self._processors = OrderedDict((i.key, i) for i in self.processors)

    def __iter__(self) -> Iterator[Type[ContextProcessor]]:
        yield from self._processors.values()

    def processing(self, config, path=None):
        for k, v in config.items():
            if '/' in k:
                continue
            p = '.'.join(i for i in (path, k) if i)
            for processor in self:
                m = processor.match(self.context, p, v)
                if m is None:
                    continue
                if m.process:
                    groups: Sequence[str] = ()
                    if isinstance(v, Mapping):
                        groups = v.get('groups') or groups
                    self.on_ready.append(m.process, groups)
                break
            else:
                if isinstance(v, Mapping):
                    self.processing(v, p)

    def build(self, config):
        if not self._built:
            if config is None:
                raise RuntimeError('Config is empty')
            self.value = config
            self.processing(self.value)
            self._built = True

    async def process(self, config=None):
        self.build(config)
        await self.on_ready.send(self.context._group_resolver)


class Context(AbstractEntity, Octopus):
    def __init__(self, *args, **kwargs):
        self._group_resolver = kwargs.pop('group_resolver', GroupResolver())
        self._connect_timeout = kwargs.pop("connect_timeout", 0)
        self._on_connect = Signal(self, name='connect')
        self._sent_start = kwargs.pop("sent_start", True)
        self._on_start = Signal(self, name='start')
        self._on_stop = Signal(self, name='stop')
        self._on_disconnect = Signal(self, name='disconnect')
        self._on_cleanup = Signal(self, name='cleanup')
        self.logger = logging.getLogger('aioworkers')
        root_processor = kwargs.pop('root_processor', RootContextProcessor)
        self.processors = root_processor(self)

        for p, e in list(kwargs.items()):
            if isinstance(e, AbstractEntity):
                kwargs.pop(p)
                self.__dict__[p] = e
                e.set_config(ValueExtractor(name=p))
        super().__init__(*args, **kwargs)

    def set_group_resolver(self, gr):
        self._group_resolver = gr

    def set_config(self, config) -> None:
        self._config = config

    def set_loop(self, loop):
        if self._loop is not None:
            raise RuntimeError('Loop already set')
        self._set_loop(loop)
        for _path, obj in self.find_iter(AbstractEntity):
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

    async def wait_all(self, coros, raises: bool = False):
        if not coros:
            return
        coros = [self.loop.create_task(i) if inspect.iscoroutine(i) else i for i in coros]
        d, p = await asyncio.wait(coros)
        errors = []
        for f in d:
            if f.exception():
                errors.append(f)
        if errors:
            if raises:
                *errors, err = errors
            for f in errors:
                self.logger.exception("ERROR", exc_info=f.exception())
            if raises:
                await err

    async def connect(self, timeout: Optional[float] = None):
        await self.on_connect.send(self._group_resolver, timeout=timeout)

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

    def __dir__(self) -> List[str]:
        result = []
        if self.config:
            result.extend(self.config)
            result.extend(k for k in super().__dir__() if k not in self.config)
        else:
            result.extend(super().__dir__())
        return result

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

    def _setattr(self, key, value, method):
        if isinstance(value, AbstractEntity):
            value.set_context(self)
            if self.config and self.config.get(key):
                config = self.config[key].new_parent(name=key)
                value.set_config(config)
        if isinstance(key, str) and DOT not in key:
            self.__dict__[key] = value
        else:
            return method(key, value)

    def __setitem__(self, key, value):
        self._setattr(key, value, super().__setitem__)

    def __setattr__(self, key, value):
        self._setattr(key, value, super().__setattr__)

    def __getattr__(self, item):
        try:
            return self._config[item]
        except KeyError:
            raise AttributeError(item) from None

    def __enter__(self):
        if self._loop is None:
            self.set_loop(asyncio.get_event_loop())
        self.loop.run_until_complete(self.__aenter__())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.loop.is_closed():
            self.loop.run_until_complete(
                self.__aexit__(exc_type, exc_val, exc_tb),
            )

    async def __aenter__(self):
        await self.init()
        await self.connect(timeout=self._connect_timeout)
        if self._sent_start:
            await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._sent_start:
            await self.stop()
        await self.disconnect()
        await self._on_cleanup.send(self._group_resolver)

    def get_object(self, path: str) -> Any:
        if path.startswith(DOT):
            item = path[1:]

            try:
                return super().__getitem__(item)
            except KeyError:
                pass

            cfg = self._config
            for i in item.split(DOT):
                try:
                    cfg = cfg[i]
                except KeyError:
                    break
                if isinstance(cfg, Mapping):
                    groups = cfg.get(GroupsContextProcessor.key)
                    if groups:
                        raise RuntimeError(f"Access to inactive path '{path}', rerun with any group: {groups}")
            else:
                return cfg

            raise KeyError(path)

        return import_name(path)
