import asyncio
import time

from ..core.base import AbstractReader, AbstractWriter
from ..utils import import_name


class AbstractQueue(AbstractReader, AbstractWriter):
    pass


class Queue(asyncio.Queue, AbstractQueue):
    def __init__(self, config=None, *, loop=None, **kwargs):
        self._maxsize = kwargs.get('maxsize', 0)
        AbstractQueue.__init__(self, config, loop=loop, **kwargs)
        asyncio.Queue.__init__(self, maxsize=self._maxsize)

    def set_config(self, config) -> None:
        super().set_config(config)
        self._maxsize = self.config.get('maxsize', 0)

    def __len__(self):
        return self.qsize()


class PriorityQueue(asyncio.PriorityQueue, Queue):
    def __init__(self, config=None, *, loop=None, **kwargs):
        self._maxsize = kwargs.get('maxsize', 0)
        AbstractQueue.__init__(self, config, loop=loop, **kwargs)
        asyncio.Queue.__init__(self, maxsize=self._maxsize)


class ScoreQueueMixin:
    """
    config:
        default_score: default value score
    """

    def __init__(self, *args, **kwargs):
        self._base_timestamp = time.time()
        self._set_default(kwargs)
        return super().__init__(*args, **kwargs)

    def _set_default(self, cfg):
        default = cfg.get('default_score', self.default_score)
        if not isinstance(default, str):
            self._default_score = default
        elif default == 'time.time':
            self._default_score = self._loop_time
        else:
            self._default_score = import_name(default)

    def _loop_time(self) -> float:
        return self.loop.time() + self._base_timestamp

    def set_config(self, config):
        super().set_config(config)
        self._set_default(self._config)

    async def init(self):
        self._base_timestamp = -self.loop.time() + time.time()
        await super().init()

    def put(self, value, score=None):
        if score is None:
            if callable(self._default_score):
                score = self._default_score()
        v = score, value
        return super().put(v)

    async def get(self, score=False):
        s, val = await super().get()
        if score:
            return val, s
        else:
            return val


def score_queue(default_score=None):
    return lambda klass: type(
        klass.__name__,
        (ScoreQueueMixin, klass),
        {
            'default_score': default_score,
            'super': klass,
        },
    )


@score_queue()
class ScoreQueue(PriorityQueue):
    pass
