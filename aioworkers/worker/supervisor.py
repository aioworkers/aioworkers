import asyncio
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
        self.context.on_stop.append(self.stop)
        self._children = [
            self.create_child() for _ in range(self.config.children)
        ]
        await super().init()
        await self._wait(lambda w: w.init())

    def _wait(self, lmbd):
        return self.context.wait_all([lmbd(w) for w in self._children])

    def get_child_config(self):
        return self.config.child.copy()

    def create_child(self):
        conf = self.get_child_config()
        if not conf.get('input') and self.input is not None:
            conf.input = self.name
        if not conf.get('output') and self.output is not None:
            conf.output = self.name
        cls = utils.import_name(conf.cls)
        if 'name' not in conf:
            name = self.name + '.child'
            conf['name'] = name
        return cls(conf, context=self.context, loop=self.loop)

    async def get(self):
        return await self.input.get()

    async def put(self, *args, **kwargs):
        return await self.output.put(*args, **kwargs)

    async def work(self):
        await self._wait(lambda w: w.start())
        await asyncio.wait([i._future for i in self._children], loop=self.loop)

    async def stop(self, force=True):
        await super().stop(force=force)
        await self._wait(lambda w: w.stop(force=force))

    async def status(self):
        status = await super().status()
        status['children'] = []
        for w in self._children:
            status['children'].append(await w.status())
        return status
