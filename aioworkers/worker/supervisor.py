import asyncio
import logging

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

    def _wait(self, lmbd, children=()):
        children = children or self._children
        return self.context.wait_all([lmbd(w) for w in children])

    def get_child_config(self):
        return self.config.child

    def create_child(self):
        conf = self.get_child_config()
        add = {}
        if not conf.get('input') and self.input is not None:
            add['input'] = self.name
        if not conf.get('output') and self.output is not None:
            add['output'] = self.name
        cls = conf.get_obj('cls')
        if 'name' not in conf:
            name = self.name + '.child'
            add['name'] = name
        if add:
            conf = conf.new_child(add)
        return cls(conf, context=self.context, loop=self.loop)

    async def get(self):
        return await self.input.get()

    async def put(self, *args, **kwargs):
        return await self.output.put(*args, **kwargs)

    async def work(self):
        children = self._children
        then = asyncio.FIRST_EXCEPTION if self._persist else asyncio.ALL_COMPLETED
        while True:
            await self._wait(lambda w: w.start(), children)
            d, p = await asyncio.wait(
                [i._future for i in self._children],
                loop=self.loop, return_when=then)
            if not self._persist:
                break
            await asyncio.sleep(1, loop=self.loop)
            children = [i for i in self._children if i._future in d]

    async def stop(self, force=False):
        await super().stop(force=True)
        await self._wait(lambda w: w.stop(force=force))

    async def status(self):
        status = await super().status()
        status['children'] = []
        for w in self._children:
            status['children'].append(await w.status())
        return status
