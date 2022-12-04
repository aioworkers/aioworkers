import asyncio
import collections
import datetime
from abc import abstractmethod
from functools import partial
from typing import Any, Dict, Optional, Tuple

from ..core.base import AbstractNamedEntity, LoggingEntity, link
from ..queue.base import AbstractQueue
from ..utils import import_name


class AbstractWorker(LoggingEntity, AbstractNamedEntity):
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
    """Worker
    config:
        run: str optional coroutine
        autorun: bool with self.init
        persist: bool if need rerun
        logger: str
        sleep: int time in seconds for sleep between rerun
        sleep_start: int time in seconds for sleep before run
        crontab: str rule as cron. Every 5 minutes "*/5 * * * *"
        input: str.path to instance of AbstractReader
        output: str.path to instance of AbstractWriter
    """

    counter: Dict
    _crontab = None
    _sleep = None
    _sleep_start = None
    _started_at = None
    _stopped_at = None
    _is_sleep = None
    _future = None
    _persist = False

    input: Optional[AbstractQueue] = link(nullable=True)
    output: Optional[AbstractQueue] = link(nullable=True)

    def __init__(self, *args, **kwargs):
        self.counter = collections.Counter()
        super().__init__(*args, **kwargs)

    def set_config(self, config):
        super().set_config(config)
        crontab = self.config.get('crontab')
        if crontab:
            CronTab = import_name('crontab.CronTab')
            self._crontab = CronTab(crontab)

        self._sleep = self.config.get_duration(
            'sleep',
            default=None,
            null=True,
        )
        self._sleep_start = self.config.get_duration(
            'sleep_start', default=None, null=True
        )

    async def init(self):
        await super().init()

        if self.config.get('run'):
            run = import_name(self.config.run)
            self.run = partial(run, self)  # type: ignore

        if self.input is not None or self.output is not None:
            self._persist = True
        elif self._crontab is not None:
            self._persist = True
        else:
            self._persist = self.config.get('persist')

        groups = self.config.get('groups')
        if self.config.get('autorun'):
            self.context.on_start.append(self.start, groups)
        self.context.on_stop.append(self.stop, groups)

    async def work(self):
        self._is_sleep = False
        if self.input is not None:
            args: Tuple[Any, ...] = (await self.input.get(),)
        else:
            args = ()
        self.counter['run'] += 1
        result = await self.run(*args)
        self.counter['done'] += 1
        if self.output is not None:
            await self.output.put(result)

    async def runner(self):
        self._is_sleep = True
        try:
            if self._sleep_start:
                await asyncio.sleep(self._sleep_start)
            while True:
                if self._crontab is not None:
                    await asyncio.sleep(self._crontab.next(default_utc=True))
                try:
                    await self.work()
                except asyncio.CancelledError:
                    raise
                except BaseException:
                    self.counter['error'] += 1
                    self.logger.exception(
                        'ERROR {} {}'.format(
                            self.name,
                            self.config.get('run', type(self)),
                        )
                    )
                self._is_sleep = True
                if not self._persist:
                    return
                if self._sleep:
                    await asyncio.sleep(self._sleep)
        finally:
            self._stopped_at = datetime.datetime.now()

    async def run(self, value=None):  # type: ignore
        raise NotImplementedError()

    def __call__(self, *args, **kwargs):
        if self.input is None:
            return self.run(*args, **kwargs)
        else:
            return self.input.put(*args, **kwargs)

    @property
    def started_at(self):
        return getattr(self, '_started_at', None)

    @property
    def stopped_at(self):
        return getattr(self, '_stopped_at', None)

    def running(self):
        if not hasattr(self, '_future'):
            return False
        elif self._future is None:
            return False
        else:
            return not self._future.done()

    async def start(self):
        if not self.running():
            self._started_at = datetime.datetime.now()
            self._stopped_at = None
            self._future = self.loop.create_task(self.runner())

    async def stop(self, force=True):
        if not self.running():
            pass
        elif force or self._is_sleep:
            assert self._future
            self._future.cancel()
            self._stopped_at = datetime.datetime.now()
            try:
                await self._future
            except asyncio.CancelledError:
                pass
        elif self._future:
            self._persist = False
            try:
                await self._future
            except asyncio.CancelledError:
                pass
        self._is_sleep = None

    async def status(self):
        return {
            'started_at': self.started_at,
            'stopped_at': self.stopped_at,
            'running': self.running(),
            'is_sleep': self._is_sleep,
            **self.counter,
        }
