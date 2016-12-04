import asyncio
import heapq
import time

from .base import AbstractQueue


class TimestampQueue(AbstractQueue):
    async def init(self):
        self._future = None
        self._queue = []
        self._waiters = []

    async def stop(self):
        if self._future and not self._future.done():
            self._future.cancel()
        for i in self._waiters:
            i.cancel()

    def __len__(self):
        return len(self._queue)

    def get(self):
        waiter = self.loop.create_future()
        if self._queue:
            timestamp, value = heapq.nsmallest(1, self._queue)[0]
            if time.time() >= timestamp:
                ts, value = heapq.heappop(self._queue)
                waiter.set_result(value)
                return waiter
            if not self._future or self._future.done():
                self._future = self.loop.create_task(self._timer())
        self._waiters.append(waiter)
        return waiter

    async def put(self, value):
        heapq.heappush(self._queue, value)
        if self._future and not self._future.done():
            self._future.cancel()
        self._future = self.loop.create_task(self._timer())

    async def _timer(self):
        if not self._queue or not self._waiters:
            return

        ts = heapq.nsmallest(1, self._queue)[0][0]
        t = ts - time.time()
        if t < 0:
            f = self._waiters.pop(0)
            f.set_result(heapq.heappop(self._queue)[1])
        else:
            await asyncio.sleep(t, loop=self.loop)
            self._future = self.loop.create_task(self._timer())


class UniqueQueue(TimestampQueue):
    async def put(self, value):
        ts, val = value
        for i, (t, v) in enumerate(self._queue):
            if v == val:
                self._queue[i] = value
                heapq.heapify(self._queue)
                break
        else:
            heapq.heappush(self._queue, value)
        if self._future and not self._future.done():
            self._future.cancel()
        self._future = self.loop.create_task(self._timer())
