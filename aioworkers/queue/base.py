import asyncio

from ..core.base import AbstractReader, AbstractWriter
from ..utils import import_name


class AbstractQueue(AbstractReader, AbstractWriter):
    pass


class Queue(asyncio.Queue, AbstractQueue):
    def __init__(self, config=None, *, loop=None, **kwargs):
        self._maxsize = kwargs.get('maxsize', 0)
        AbstractQueue.__init__(self, config, loop=loop, **kwargs)
        asyncio.Queue.__init__(self, maxsize=self._maxsize, loop=loop)

    def set_config(self, config) -> None:
        super().set_config(config)
        self._maxsize = self.config.get('maxsize', 0)

    def __len__(self):
        return self.qsize()


class PriorityQueue(asyncio.PriorityQueue, Queue):
    def __init__(self, config=None, *, loop=None, **kwargs):
        self._maxsize = kwargs.get('maxsize', 0)
        AbstractQueue.__init__(self, config, loop=loop, **kwargs)
        asyncio.Queue.__init__(self, maxsize=self._maxsize, loop=loop)


class ScoreQueueMixin:
    """
    config:
        default_score: default value score
    """

    def __init__(self, *args, **kwargs):
        self._set_default(kwargs)
        return super().__init__(*args, **kwargs)

    def _set_default(self, cfg):
        default = cfg.get('default_score', self.default_score)
        if isinstance(default, str):
            self._default_score = import_name(default)
        else:
            self._default_score = default

    def set_config(self, config):
        super().set_config(config)
        self._set_default(self._config)

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
