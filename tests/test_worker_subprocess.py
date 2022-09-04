import pytest
from asyncio import subprocess

from aioworkers.core.config import Config
from aioworkers.core.context import Context
from aioworkers.worker.subprocess import Subprocess


async def test_autorun(event_loop):
    config = Config(
        a=dict(
            cls="aioworkers.worker.subprocess.Subprocess",
            autorun=True,
            sleep=1,
            cmd="echo",
            stdin='PIPE',
            stdout='PIPE',
            stderr='PIPE',
        )
    )
    async with Context(config, loop=event_loop) as context:
        await context.a._future
        assert not context.a.running()
        assert context.a._started_at


async def test_daemon(event_loop):
    config = Config(
        a=dict(
            cls="aioworkers.worker.subprocess.Subprocess",
            autorun=True,
            daemon=True,
            cmd="echo",
        )
    )
    async with Context(config, loop=event_loop) as ctx:
        assert not ctx.a.process


@pytest.mark.parametrize("cmd", ["time.time", ["time.time"]])
async def test_aioworkers(event_loop, cmd):
    config = Config(
        a=dict(
            cls="aioworkers.worker.subprocess.Subprocess",
            aioworkers=cmd,
            wait=False,
        )
    )
    async with Context(config, loop=event_loop) as ctx:
        p = await ctx.a.run_cmd()
        assert isinstance(p, subprocess.Process)
        await p.wait()


async def test_stop(event_loop, mocker):
    config = Config(
        a=dict(
            cls="aioworkers.worker.subprocess.Subprocess",
            autorun=True,
            daemon=True,
            cmd="echo",
        )
    )

    async def ok_wait():
        pass

    async def fail_wait():
        raise ProcessLookupError

    async with Context(config, loop=event_loop) as ctx:
        assert isinstance(ctx.a, Subprocess)
        p1 = mocker.Mock(returncode=1)
        p2 = mocker.Mock(returncode=None, wait=ok_wait)
        p3 = mocker.Mock(returncode=None, wait=fail_wait)
        ctx.a._processes[1] = p1
        ctx.a._processes[2] = p2
        ctx.a._processes[3] = p3
        await ctx.a.stop(force=False)
        assert ctx.a.process


@pytest.mark.parametrize("cmd", ["echo 1", ["echo", "1"]])
async def test_shell_cmd(event_loop, cmd):
    config = Config(
        a=dict(
            cls="aioworkers.worker.subprocess.Subprocess",
            autorun=True,
            cmd=cmd,
        )
    )
    async with Context(config, loop=event_loop) as ctx:
        assert b"1\n" == await ctx.a.run_cmd()


@pytest.mark.parametrize("arg", ["1", ["1"]])
async def test_arg(event_loop, arg):
    config = Config(
        a=dict(
            cls="aioworkers.worker.subprocess.Subprocess",
            autorun=True,
            cmd=["echo"],
        )
    )
    async with Context(config, loop=event_loop) as ctx:
        assert b"1\n" == await ctx.a.run_cmd(arg)


async def test_args(event_loop):
    config = Config(
        a=dict(
            cls="aioworkers.worker.subprocess.Subprocess",
            autorun=True,
            cmd=["echo"],
        )
    )
    async with Context(config, loop=event_loop) as ctx:
        assert b"1 2\n" == await ctx.a.run_cmd("1", "2")


@pytest.mark.parametrize("arg", [{"a": 1}])
async def test_kwarg(event_loop, arg):
    async with Context(
        loop=event_loop,
        a=Subprocess(
            autorun=True,
            cmd=["echo", "{a}"],
        ),
    ) as ctx:
        assert b"1\n" == await ctx.a.run_cmd(**arg)
