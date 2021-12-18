import io
import os
from queue import Queue

from aioworkers import utils
from aioworkers.core.config import Config
from aioworkers.core.context import Context
from aioworkers.queue import proxy


async def test_q(loop):
    conf = Config()
    conf.update({'q.cls': utils.import_uri(proxy.ProxyQueue)})

    async with Context(conf, loop=loop) as ctx:
        ctx.q.set_queue(Queue())
        await ctx.q.put(1)
        assert 1 == await ctx.q.get()


async def test_plq(loop):
    conf = Config()
    conf.update(
        {
            'q.cls': utils.import_uri(proxy.PipeLineQueue),
            'q.format': 'newline:str',
        }
    )

    async with Context(conf, loop=loop) as ctx:
        nl = os.linesep.encode()
        fin = io.BytesIO(b'123' + nl)
        fout = io.BytesIO()
        ctx.q.set_reader(fin)
        ctx.q.set_writer(fout)
        assert '123' == await ctx.q.get()
        await ctx.q.put('1')
        assert b'1' + nl == fout.getvalue()
