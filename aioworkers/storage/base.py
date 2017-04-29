from abc import abstractmethod

from aioworkers.core.base import AbstractNamedEntity


class AbstractBaseStorage(AbstractNamedEntity):
    @abstractmethod
    async def raw_key(self, key):
        raise NotImplementedError()


class AbstractStorageReadOnly(AbstractBaseStorage):
    @abstractmethod
    async def get(self, key):
        raise NotImplementedError()


class AbstractStorageWriteOnly(AbstractBaseStorage):
    @abstractmethod
    async def set(self, key, value):
        raise NotImplementedError()


class AbstractStorage(AbstractStorageReadOnly, AbstractStorageWriteOnly):
    async def copy(self, key_source, storage_dest, key_dest):
        data = await self.get(key_source)
        await storage_dest.set(key_dest, data)
        return data is None

    async def move(self, key_source, storage_dest, key_dest):
        result = await self.copy(key_source, storage_dest, key_dest)
        if result:
            await self.set(key_source, None)
        return result


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


class FieldStorageMixin(AbstractStorage):
    model = dict

    async def get(self, key, *, field=None, fields=None):
        value = await super().get(key)
        if field:
            return value[field]
        elif fields:
            m = self.model()
            for f in fields:
                m[f] = value[f]
            return m
        else:
            return value

    async def set(self, key, value, *, field=None, fields=None):
        if field or fields:
            m = await super().get(key)
            if field:
                m[field] = value
            else:
                for f in fields:
                    m[f] = value[f]
            value = m
        await super().set(key, value)
