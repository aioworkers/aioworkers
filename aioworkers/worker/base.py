import asyncio
import datetime
import logging
from abc import abstractmethod

from ..core.base import AbstractEntity
from ..utils import import_name


class AbstractWorker(AbstractEntity):
    @abstractmethod  # pragma: no cover
    async def start(self):
        raise NotImplementedError()

    @abstractmethod  # pragma: no cover
    async def stop(self):
        raise NotImplementedError()

    @abstractmethod  # pragma: no cover
    async def status(self):
        raise NotImplementedError()


class Worker(AbstractWorker):
    """ Worker
        config:
            run: str optional coroutine
            autorun: bool with self.init
            persist: bool if need rerun
            logger: str
            sleep: int time in seconds for sleep between rerun
            sleep_start: int time in seconds for sleep before run
            input: str.path to instance of AbstractReader
            output: str.path to instance of AbstractWriter
    """
    async def init(self):
        self._started_at = None
        self._stoped_at = None
        self._future = None
        if self.config.get('run'):
            run = import_name(self.config.run)
            self.run = lambda value=None: run(self, value)
        self._input = self.context[self.config.get('input')]
        self._output = self.context[self.config.get('output')]
        if self._input or self._output:
            self._persist = True
        else:
            self._persist = self.config.get('persist')
        self._sleep = self.config.get('sleep')
        self._sleep_start = self.config.get('sleep_start')
        self.logger = logging.getLogger(self.config.get('logger', __name__))
        if self.config.get('autorun'):
            await self.start()

    async def runner(self):
        try:
            if self._sleep_start:
                await asyncio.sleep(self._sleep_start, loop=self.loop)
            while True:
                try:
                    if self._input:
                        args = (await self._input.get(),)
                    else:
                        args = ()
                    result = await self.run(*args)
                    if self._output:
                        await self._output.put(result)
                except BaseException:
                    self.logger.exception('ERROR')
                if not self._persist:
                    return
                if self._sleep:
                    await asyncio.sleep(self._sleep, loop=self.loop)
        finally:
            self._stoped_at = datetime.datetime.now()

    async def run(self, value=None):
        raise NotImplementedError()

    def running(self):
        return self._future is not None and not self._future.done()

    async def start(self):
        if not self.running():
            self._started_at = datetime.datetime.now()
            self._stoped_at = None
            self._future = self.loop.create_task(self.runner())

    async def stop(self):
        if self.running():
            self._future.cancel()
            self._stoped_at = datetime.datetime.now()
            try:
                await self._future
            except asyncio.CancelledError:
                pass

    async def status(self):
        return {
            'started_at': self._started_at,
            'stoped_at': self._stoped_at,
            'running': self.running(),
        }
