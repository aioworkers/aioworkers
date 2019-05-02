from abc import abstractmethod

from aioworkers.core.base import AbstractEntity


class AbstractSender(AbstractEntity):
    @abstractmethod  # pragma: no cover
    async def send_message(self, msg):
        raise NotImplementedError()

    async def send(self, *args, **kwargs):
        if args:
            for msg in args:
                if kwargs:
                    msg = msg.copy()
                    msg.update(kwargs)
                await self.send_message(msg)
        elif kwargs:
            await self.send_message(kwargs)
        else:
            raise ValueError('Empty args')
