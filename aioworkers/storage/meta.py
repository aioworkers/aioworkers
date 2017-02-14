import weakref
from itertools import cycle

from . import base


class AbstractMetaListStorage(base.AbstractStorage):
    def raw_key(self, key):
        return key

    @property
    def storages(self):
        return map(lambda x: self.context[x], self.config.storages)


class Fallback(AbstractMetaListStorage):
    async def get(self, key):
        key = self.raw_key(key)
        for storage in self.storages:
            v = await storage.get(key)
            if v is not None:
                return v

    async def set(self, key, value):
        pass


class Replicator(AbstractMetaListStorage):
    async def init(self):
        self._pool = cycle(self.storages)

    async def get(self, key):
        storage = next(self._pool)
        key = self.raw_key(key)
        return await storage.get(key)

    async def set(self, key, value):
        key = self.raw_key(key)
        for storage in self.storages:
            await storage.set(key, value)


class Cache(base.AbstractStorage):
    def raw_key(self, key):
        return key

    @property
    def storage(self):
        return self.context[self.config.storage]

    @property
    def source(self):
        return self.context[self.config.source]

    async def get(self, key):
        key = self.raw_key(key)
        v = await self.storage.get(key)
        if v is not None:
            return v
        v = await self.source.get(key)
        await self.storage.set(key, v)
        return v

    def set(self, key, value):
        key = self.raw_key(key)
        return self.storage.set(key, value)


class FutureStorage(base.AbstractStorage):
    async def init(self):
        if self.config.get('weak', True):
            self._futures = weakref.WeakValueDictionary()
        else:
            self._futures = {}

    def raw_key(self, key):
        return key

    async def set(self, key, value):
        future = self.get(key)
        future.set_result(value)

    def get(self, key):
        key = self.raw_key(key)
        if key in self._futures:
            return self._futures[key]
        else:
            return self._futures.setdefault(
                key, self.loop.create_future())
