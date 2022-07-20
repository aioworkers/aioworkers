import asyncio
import collections
import heapq
from typing import Any, Deque, NamedTuple, Optional, Tuple

from .base import AbstractQueue, ScoreQueueMixin


class Item(NamedTuple):
    value: Any
    timestamp: float

    def __lt__(self, other) -> bool:
        return self.timestamp < other.timestamp


class TimestampQueue(ScoreQueueMixin, AbstractQueue):
    default_score = 'time.time'
    _getters: Deque[Tuple[bool, asyncio.Future]]
    _putters: Deque[asyncio.Future]

    def __init__(self, *args, **kwargs):
        self._queue = []
        self._getters = collections.deque()
        self._putters = collections.deque()
        self._add_score = kwargs.pop('add_score', 0)
        self._maxsize = kwargs.pop('maxsize', 0)
        self._min_timestamp = 0.0
        super().__init__(*args, **kwargs)

    def set_config(self, config):
        super().set_config(config)
        self._add_score = self.config.get_duration(
            'add_score',
            null=True,
            default=0,
        )
        self._maxsize = self.config.get_int(
            'maxsize',
            null=True,
            default=0,
        )

    def set_context(self, context):
        context.on_cleanup.append(self.cleanup)
        return super().set_context(context)

    async def cleanup(self):
        for s, i in self._getters:
            if not i.done():
                i.cancel()
        for f in self._putters:
            if not f.done():
                f.cancel()

    async def __aenter__(self):
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not self.loop.is_closed():
            await self.cleanup()

    def __len__(self):
        return len(self._queue)

    def empty(self) -> bool:
        return not self._queue

    def full(self) -> bool:
        if 0 >= self._maxsize:
            return False
        return len(self) >= self._maxsize

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if not self._loop:
            self._loop = asyncio.get_running_loop()
        return self._loop

    def _schedule(self, item: Item):
        self._put(item)
        if not self._min_timestamp or self._min_timestamp > item.timestamp:
            self._min_timestamp = item.timestamp
            self._loop.call_at(item.timestamp - self._base_timestamp, self._on_time)

    async def get(self, score: bool = False, *, timeout: float = None):
        item = self._pop()
        if item is None:
            pass
        elif item.timestamp > self._loop_time():
            self._schedule(item)
        else:
            self._release_putter()
            if score:
                return item.value, item.timestamp
            else:
                return item.value
        waiter = self.loop.create_future()
        self._getters.append((score, waiter))
        if timeout:
            self._loop.call_later(timeout, self._on_timeout, waiter, timeout)
        return await waiter

    def _on_timeout(self, waiter: asyncio.Future, timeout: float):
        if not waiter.done():
            waiter.set_exception(asyncio.TimeoutError(timeout))

    def _send(self, item: Item) -> bool:
        while self._getters:
            with_score, f = self._getters.popleft()
            if f.done():
                continue
            elif with_score:
                f.set_result((item.value, item.timestamp))
            else:
                f.set_result(item.value)
            self._release_putter()
            return True
        return False

    def _pop(self) -> Optional[Item]:
        if self._queue:
            return heapq.heappop(self._queue)
        else:
            return None

    def _put(self, item: Item):
        heapq.heappush(self._queue, item)

    async def put(self, value, score=None):
        if score is None:
            if callable(self._default_score):
                score = self._default_score()
            score += self._add_score
        item = Item(value=value, timestamp=score)
        if self._getters:
            if score < self._loop_time():
                if self._send(item):
                    return
                else:
                    self._put(item)
            else:
                self._schedule(item)
        else:
            self._put(item)
        if self.full():
            waiter = self.loop.create_future()
            self._putters.append(waiter)
            await waiter

    def _release_putter(self):
        while self._putters and not self.full():
            self._putters.popleft().set_result(None)

    def _on_time(self):
        while self._queue and self._getters:
            item = self._pop()
            if not item:
                break
            elif item.timestamp > self._loop_time():
                self._schedule(item)
                break
            elif not self._send(item):
                self._put(item)


class UniqueQueue(TimestampQueue):
    def __init__(self, *args, **kwargs):
        self._values = {}
        super().__init__(*args, **kwargs)

    def _pop(self) -> Optional[Item]:
        while self._queue:
            item = heapq.heappop(self._queue)
            if item is self._values.get(item.value):
                return self._values.pop(item.value)
        return None

    def _put(self, item: Item):
        super()._put(item)
        self._values[item.value] = item

    def __len__(self) -> int:
        return len(self._values)

    def empty(self) -> bool:
        return not self._values
