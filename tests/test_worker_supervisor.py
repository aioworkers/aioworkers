from pathlib import Path

from aioworkers.core.config import Config
from aioworkers.core.context import Context

config = Config()
config.load(Path(__file__).with_suffix('.yaml'))


async def test_autorun(event_loop):
    async with Context(config.autorun, loop=event_loop) as ctx:
        await ctx.sv._future
        assert ctx.sv._started_at
        assert not ctx.sv.running()
        await ctx.sv.stop()
        assert await ctx.sv.status()
        assert 2 == await ctx.sv(2)


async def run(w, value):
    return value


async def test_super_queue(event_loop):
    async with Context(config.super.queue, loop=event_loop) as ctx:
        await ctx.q1.put(1)
        result = await ctx.q2.get()
        assert result == 1
        await ctx.sv(2)
        result = await ctx.q2.get()
        assert result == 2


async def test_super_crash(event_loop):
    async with Context(config.super.queue, loop=event_loop) as ctx:
        ctx.sv['a']._future.cancel()
        await ctx.q1.put(1)
        await ctx.q2.get()
