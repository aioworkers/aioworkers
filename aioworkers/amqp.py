"""
Module support amqp
Required: asynqp
"""
import asyncio

import asynqp

from aioworkers.queue.base import AbstractQueue


class AmqpQueue(AbstractQueue):
    async def init(self):
        """
        config:
            connection:
                host:
                port:
                auth:
                    username:
                    password:
                virtual_host:
            exchange:
                name:
                type:
            queue:
            route_key:
            wait:
            format: [json|msg]
        """
        await super().init()
        self._started = False
        self._lock = asyncio.Lock(loop=self.loop)
        await self._lock.acquire()
        self.context.on_start.append(self.start)
        self.context.on_stop.append(self.stop)

    async def start(self):
        if self._started:
            return
        logger = self.context.logger
        logger.debug('Amqp connection start')
        self.connection = await asynqp.connect(
            self.config.connection.host, self.config.connection.port,
            virtual_host=self.config.connection.get('virtual_host', '/'),
            loop=self.loop,
            **self.config.connection.auth)
        logger.debug('Amqp connected')
        self.channel = await self.connection.open_channel()
        logger.debug('Amqp open_channel')

        self.exchange = await self.channel.declare_exchange(
            self.config.exchange.name, self.config.exchange.type)
        logger.debug('Amqp declare_exchange')
        self.queue = await self.channel.declare_queue(self.config.queue)
        logger.debug('Amqp declare_queue')

        await self.queue.bind(self.exchange, self.config.route_key)
        self._started = True
        self._lock.release()
        return self

    async def stop(self):
        if not self._started:
            return
        if not self._lock.locked():
            await self._lock.acquire()
        try:
            await self.channel.close()
        except:
            pass
        try:
            await self.connection.close()
        except:
            pass
        self._started = False

    def encode(self, msg):
        if isinstance(msg, asynqp.Message):
            return msg
        else:
            return asynqp.Message(msg)

    def decode(self, envelop):
        if self.config.get('format', 'json') == 'json':
            val = envelop.json()
            envelop.ack()
            return val
        return envelop

    def put_nowait(self, msg):
        msg = self.encode(msg)
        self.exchange.publish(msg, self.config.route_key)

    async def put(self, msg):
        self.put_nowait(msg)

    async def get(self):
        await self._lock.acquire()
        while True:
            received_message = await self.queue.get()
            if received_message is None:
                self.context.logger.debug('No message')
            else:
                self._lock.release()
                return self.decode(received_message)
            await asyncio.sleep(self.config.wait)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
