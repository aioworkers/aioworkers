from abc import abstractmethod

from aioworkers.core.base import AbstractNamedEntity


class AbstractStorageReadOnly(AbstractNamedEntity):
    @abstractmethod
    async def get(self, key):
        raise NotImplementedError()


class AbstractStorageWriteOnly(AbstractNamedEntity):
    @abstractmethod
    async def set(self, key, value):
        raise NotImplementedError()


class AbstractStorage(AbstractStorageReadOnly, AbstractStorageWriteOnly):
    pass


class AbstractListedStorage(AbstractStorage):
    @abstractmethod
    async def list(self):
        raise NotImplementedError()

    @abstractmethod
    async def length(self):
        raise NotImplementedError()


class AbstractExpiryStorage(AbstractStorage):
    @abstractmethod
    async def expiry(self, key, expiry):
        raise NotImplementedError()
