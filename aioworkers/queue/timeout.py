import asyncio
import heapq
import time

from .base import AbstractQueue, ScoreQueueMixin


class TimestampQueue(ScoreQueueMixin, AbstractQueue):
    default_score = 'time.time'

    def init(self):
        self._future = None
        self._queue = []
        self._waiters = []
        self.context.on_stop.append(self.stop)
        return super().init()

    async def stop(self):
        if self._future and not self._future.done():
            self._future.cancel()
        for s, i in self._waiters:
            i.cancel()
        self._waiters = []

    def __len__(self):
        return len(self._queue)

    def get(self, score=False):
        waiter = self.loop.create_future()
        if self._queue:
            timestamp, value = heapq.nsmallest(1, self._queue)[0]
            if time.time() >= timestamp:
                ts, value = heapq.heappop(self._queue)
                if score:
                    waiter.set_result((value, ts))
                else:
                    waiter.set_result(value)
                return waiter
            if not self._future or self._future.done():
                self._future = self.loop.create_task(self._timer())
        self._waiters.append((score, waiter))
        return waiter

    async def put(self, value, score=None):
        if score is None:
            if callable(self._default_score):
                score = self._default_score()
        heapq.heappush(self._queue, (score, value))
        if self._future and not self._future.done():
            self._future.cancel()
        self._future = self.loop.create_task(self._timer())

    async def _timer(self):
        if not self._queue or not self._waiters:
            return

        ts = heapq.nsmallest(1, self._queue)[0][0]
        t = ts - time.time()
        if t < 0:
            score, f = self._waiters.pop(0)
            ts, val = heapq.heappop(self._queue)
            if score:
                f.set_result((val, ts))
            else:
                f.set_result(val)
        else:
            await asyncio.sleep(t, loop=self.loop)
            self._future = self.loop.create_task(self._timer())


class UniqueQueue(TimestampQueue):
    async def put(self, value, score=None):
        if score is None:
            if callable(self._default_score):
                score = self._default_score()
        item = score, value
        for i, (t, v) in enumerate(self._queue):
            if v == value:
                self._queue[i] = item
                heapq.heapify(self._queue)
                break
        else:
            heapq.heappush(self._queue, item)
        if self._future and not self._future.done():
            self._future.cancel()
        self._future = self.loop.create_task(self._timer())
