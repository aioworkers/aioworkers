import asyncio

from ..core.base import AbstractReader, AbstractWriter
from ..utils import import_name


class AbstractQueue(AbstractReader, AbstractWriter):
    pass


class Queue(asyncio.Queue, AbstractQueue):
    def __init__(self, config, *, context=None, loop=None):
        maxsize = config.get('maxsize', 0)
        AbstractQueue.__init__(self, config, context=context, loop=loop)
        asyncio.Queue.__init__(self, maxsize=maxsize, loop=loop)

    def __len__(self):
        return len(self._queue)


class PriorityQueue(asyncio.PriorityQueue, Queue):
    def __init__(self, config, *, context=None, loop=None):
        maxsize = config.get('maxsize', 0)
        AbstractQueue.__init__(self, config, context=context, loop=loop)
        asyncio.Queue.__init__(self, maxsize=maxsize, loop=loop)


class ScoreQueueMixin:
    """
    config:
        default_score: default value score
    """

    def init(self):
        self._default_score = self.config.get(
            'default_score', self.default_score)
        if isinstance(self._default_score, str):
            self._default_score = import_name(self._default_score)
        return super().init()

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
        {'default_score': default_score, 'super': klass}
    )


@score_queue()
class ScoreQueue(PriorityQueue):
    pass
