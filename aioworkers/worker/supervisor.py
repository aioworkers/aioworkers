import logging

from aioworkers import utils
from .base import Worker


logger = logging.getLogger(__name__)


class Supervisor(Worker):
    """
    config:
        children: int - count
        child: Mapping - config for child worker
    """
    async def init(self):
        self._children = [
            self.create_child() for _ in range(self.config.children)
        ]
        await super().init()
        await self._wait(lambda w: w.init())

    def _wait(self, lmbd):
        return self.context.wait_all([lmbd(w) for w in self._children])

    def get_child_config(self):
        return self.config.child

    def create_child(self):
        conf = self.get_child_config()
        cls = utils.import_name(conf.cls)
        if 'name' not in conf:
            name = self.name + '.child'
            conf['name'] = name
        return cls(conf, context=self.context, loop=self.loop)

    async def run(self, value=None):
        await self._wait(lambda w: w.start())

    async def stop(self, force=True):
        await self._wait(lambda w: w.stop(force=force))

    async def status(self):
        status = await super().status()
        status['children'] = []
        for w in self._children:
            status['children'].append(await w.status())
        return status
