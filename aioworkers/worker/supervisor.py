import asyncio
import logging
import random

from .base import Worker

logger = logging.getLogger(__name__)


class Supervisor(Worker):
    """
    config:
        children: Union[int, list[str], list[dict]] - count or list
        child: Mapping - config for child worker
    """

    def __init__(self, *args, **kwargs):
        self._children = {}
        super().__init__(*args, **kwargs)

    def __getattr__(self, item):
        return self._children[item]

    def __getitem__(self, item):
        return self._children[item]

    async def init(self):
        children = [super()]
        for p in self._gen_child_params():
            name = p['name']
            if name in self._children:
                raise RuntimeError('Duplicate child name %s' % name)
            child = self.create_child(p)
            self._children[name] = child
            children.append(child)
        await self._wait(lambda w: w.init(), children)

    def _wait(self, lmbd, children=()):
        children = children or self._children.values()
        return self.context.wait_all([lmbd(w) for w in children])

    def __call__(self, *args, **kwargs):
        if self.input is None:
            vs = random.choice(list(self._children.values()))
            return vs(*args, **kwargs)
        else:
            return self.input.put(*args, **kwargs)

    def _gen_child_params(self):
        children = self.config.children
        if isinstance(children, int):
            for i in range(children):
                yield {'name': 'child' + str(i)}
        elif isinstance(children, list):
            for i in children:
                if isinstance(i, str):
                    yield {'name': i}
                elif isinstance(i, dict):
                    yield i
                else:
                    raise RuntimeError('Unexpected type of parameter %s', i)
        else:
            raise RuntimeError('Unexpected type of parameter children')

    def get_child_config(self, *args, **kwargs):
        return self.config.child.new_child(*args, **kwargs)

    def create_child(self, *args, **kwargs):
        conf = self.get_child_config(*args, **kwargs)
        add = {}
        if not conf.get('input') and self.input is not None:
            add['input'] = self.name
        if not conf.get('output') and self.output is not None:
            add['output'] = self.name
        cls = conf.get_obj('cls')
        add['name'] = '.'.join([self.name, conf.get('name', 'child')])
        if add:
            conf = conf.new_child(add)
        return cls(conf, context=self.context, loop=self.loop)

    async def get(self):
        assert self.input is not None
        return await self.input.get()

    async def put(self, *args, **kwargs):
        assert self.output is not None
        return await self.output.put(*args, **kwargs)

    async def work(self):
        children = list(self._children.values())
        then: str
        if self._persist:
            then = asyncio.FIRST_EXCEPTION
        else:
            then = asyncio.ALL_COMPLETED
        while self._children:
            await self._wait(lambda w: w.start(), children)
            d, p = await asyncio.wait(
                [i._future for i in self._children.values()],
                return_when=then,
            )
            if not self._persist:
                break
            await asyncio.sleep(1)
            children = [i for i in self._children.values() if i._future in d]

    async def stop(self, force=False):
        await super().stop(force=True)
        await self._wait(lambda w: w.stop(force=force))

    async def status(self):
        status = await super().status()
        status['children'] = {}
        for name, w in self._children.items():
            status['children'][name] = await w.status()
        return status
