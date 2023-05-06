from typing import Optional

from aioworkers.core.base import AbstractWriter, LoggingEntity
from aioworkers.net.sender import AbstractSender
from aioworkers.worker.base import Worker as BaseWorker


class Facade(LoggingEntity, AbstractSender):
    _queue: Optional[AbstractWriter] = None

    async def init(self):
        await super().init()
        self._queue = self.context.get_object(self.config.queue)

    async def send_message(self, msg):
        await self._queue.put(msg)


class Worker(BaseWorker):
    _sender = None  # type: AbstractSender

    async def init(self):
        await super().init()
        self._sender = self.context[self.config.sender]

    async def run(self, value=None):
        await self._sender.send(value)
