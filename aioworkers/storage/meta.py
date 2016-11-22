from itertools import cycle

from . import base


class AbstractMetaListStorage(base.AbstractStorage):
    @property
    def storages(self):
        return map(lambda x: self.context[x], self.config.storages)


class Fallback(AbstractMetaListStorage):
    async def get(self, key):
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
        return await storage.get(key)

    async def set(self, key, value):
        for storage in self.storages:
            await storage.set(key, value)


class Cache(base.AbstractStorage):
    @property
    def storage(self):
        return self.context[self.config.storage]

    @property
    def source(self):
        return self.context[self.config.source]

    async def get(self, key):
        v = await self.storage.get(key)
        if v is not None:
            await self.storage.set(key, v)
            return v
        return await self.source.get(key)

    def set(self, key, value):
        return self.storage.set(key, value)
