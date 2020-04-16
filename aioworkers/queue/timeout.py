import asyncio
import collections
import heapq
import time

from .base import AbstractQueue, ScoreQueueMixin


class TimeoutItem:
    def __init__(self, value, *,
                 timeout: float = None,
                 add: float = 0):
        self._value = value
        if timeout is None:
            timeout = time.time()
        self._timeout = timeout + add

    @property
    def value(self):
        return self._value

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout: float):
        self._timeout = timeout

    def __lt__(self, other):
        if isinstance(other, TimeoutItem):
            return self._timeout < other._timeout
        raise TypeError

    def __iter__(self):
        return iter((self._timeout, self._value))

    def __repr__(self):
        return '{}({}, timeout={})'.format(
            type(self).__name__, repr(self._value), self._timeout,
        )


class TimestampQueue(ScoreQueueMixin, AbstractQueue):
    default_score = 'time.time'

    def __init__(self, *args, **kwargs):
        self._future = None
        self._queue = []
        self._waiters = collections.deque()
        self._add_score = 0
        super().__init__(*args, **kwargs)

    def set_config(self, config):
        super().set_config(config)
        self._add_score = self.config.get_duration(
            'add_score',
            null=True, default=0,
        )

    def set_context(self, context):
        context.on_cleanup.append(self.cleanup)
        return super().set_context(context)

    def cleanup(self):
        if self._future and not self._future.done():
            self._future.cancel()
        for s, i in self._waiters:
            i.cancel()

    def __len__(self):
        return len(self._queue)

    def get(self, score: bool = False):
        waiter = self.loop.create_future()
        if self._queue:
            item = heapq.nsmallest(1, self._queue)[0]  # type: TimeoutItem
            if time.time() >= item.timeout:
                item = self._pop()
                if score:
                    waiter.set_result((item.value, item.timeout))
                else:
                    waiter.set_result(item.value)
                return waiter
            if not self._future or self._future.done():
                self._future = self.loop.create_task(self._timer())
        self._waiters.append((score, waiter))
        return waiter

    def _put(self, item: TimeoutItem):
        heapq.heappush(self._queue, item)

    async def put(self, value, score=None):
        if score is None:
            if callable(self._default_score):
                score = self._default_score()
            score += self._add_score
        self._put(TimeoutItem(value, timeout=score))
        if not self._waiters:
            return
        if score > heapq.nsmallest(1, self._queue)[0].timeout:
            return
        if self._future and not self._future.done():
            self._future.cancel()
        self._future = self.loop.create_task(self._timer())

    def _pop(self) -> TimeoutItem:
        return heapq.heappop(self._queue)

    async def _timer(self):
        while self._queue and self._waiters:
            min_item = heapq.nsmallest(1, self._queue)[0]  # type: TimeoutItem
            t = min_item.timeout - time.time()
            if t > 0:
                await asyncio.sleep(t, loop=self.loop)
            else:
                while self._waiters:
                    with_score, f = self._waiters.popleft()
                    if f.done():
                        continue
                    item = self._pop()
                    if with_score:
                        f.set_result((item.value, item.timeout))
                    else:
                        f.set_result(item.value)
                    break


class UniqueQueue(TimestampQueue):
    def __init__(self, *args, **kwargs):
        self._values = {}
        super().__init__(*args, **kwargs)

    def _pop(self) -> TimeoutItem:
        item = heapq.heappop(self._queue)
        return self._values.pop(item.value)

    def _put(self, item: TimeoutItem):
        old = self._values.get(item.value)
        if isinstance(old, TimeoutItem):
            old.timeout = item.timeout
            heapq.heapify(self._queue)
        else:
            super()._put(item)
            self._values[item.value] = item
