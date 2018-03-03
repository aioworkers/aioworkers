import asyncio
import shlex
import subprocess
import sys
from collections import Mapping, Sequence

from .. import utils
from ..core.formatter import FormattedEntity
from .base import Worker


class Subprocess(FormattedEntity, Worker):
    """
    config:
        cmd: str - shell command with mask python format
             list[str] - exec command with mask python format
        aioworkers: argv or str for aioworkers subprocess
        stdin: [none | PIPE | DEVNULL]
        stdout: [none | PIPE | DEVNULL]
        stderr: [none | PIPE | STDOUT | DEVNULL]
        wait: bool - default True for wait shutdown process
        params: dict of params
        daemon: true
        format: [json|str|bytes]
    """

    async def init(self):
        if self.config.get('stdin'):
            stdin = getattr(subprocess, self.config.get('stdin'))
        elif 'stdin' in self.config:
            stdin = None
        else:
            stdin = subprocess.PIPE

        if self.config.get('stdout'):
            stdout = getattr(subprocess, self.config.get('stdout'))
        elif 'stdout' in self.config:
            stdout = None
        else:
            stdout = subprocess.PIPE

        if self.config.get('stderr'):
            stderr = getattr(subprocess, self.config.get('stderr'))
        else:
            stderr = None
        self._wait = self.config.get('wait', True)

        self._config_stdin = False

        if 'aioworkers' in self.config:
            cmd = ['{python}', '-m', 'aioworkers', '--config-stdin']
            value = self.config['aioworkers']
            if isinstance(value, str):
                cmd.append(value)
                cmd = ' '.join(cmd)
            elif isinstance(value, list):
                cmd.extend(value)
            else:
                raise TypeError(value)
            stdin = subprocess.PIPE
            self._config_stdin = True
        elif 'cmd' in self.config:
            cmd = self.config['cmd']
        else:
            raise ValueError
        self._cmd = cmd
        self._shell = self.config.get('shell', isinstance(cmd, str))
        if self._shell:
            coro = asyncio.create_subprocess_shell
        else:
            coro = asyncio.create_subprocess_exec
        self.create_subprocess = lambda *args: coro(
            *args, stdin=stdin, stdout=stdout,
            stderr=stderr, loop=self.loop)

        self.params = dict(self.config.get('params', ()))
        self.params.setdefault('python', sys.executable)
        self.params.setdefault('config', self.config)
        self.params.setdefault('worker', self)

        self._daemon = self.config.get('daemon')
        self._keeper = None
        if self._daemon:
            self._wait = False
        else:
            self.run = self.run_cmd
        self._event = asyncio.Event(loop=self.loop)
        self._event.clear()
        await super().init()

    @property
    def process(self):
        return getattr(self, '_process', None)

    def make_command(self, value):
        cmd = self._cmd
        args = ()
        m = dict(self.params)
        if isinstance(value, Mapping):
            m.update(value)
        elif isinstance(value, Sequence):
            args = value
        elif isinstance(value, str):
            args = value,

        is_cmd_str = isinstance(cmd, str)

        if is_cmd_str:
            cmd = cmd.format_map(m)
        else:
            cmd = [part.format_map(m) for part in cmd]
            cmd.extend(args)

        if self._shell and not is_cmd_str:
            cmd = ' '.join(cmd)
        elif not self._shell and is_cmd_str:
            cmd = shlex.split(cmd)
        if isinstance(cmd, str):
            cmd = cmd,
        return cmd

    async def run_cmd(self, *args, **kwargs):
        if len(args) > 1:
            value = args
        elif args:
            value = args[0]
        elif kwargs:
            value = kwargs
        else:
            value = None
        cmd = self.make_command(value)
        self.logger.info(' '.join(cmd))
        self._process = await self.create_subprocess(*cmd)
        if self._config_stdin:
            utils.dump_to_fd(
                self._process.stdin, self.context.config)
            await self._process.stdin.drain()
        if self._wait:
            await self._process.wait()
        if not self._daemon and self._process.stdout is not None:
            data = await self._process.stdout.read()
            return self.decode(data)

    async def work(self):
        if self._daemon:
            await self._event.wait()
        return await super().work()

    async def _keep_daemon(self):
        while True:
            try:
                await self.run_cmd()
                self._event.set()
                await self._process.wait()
            finally:
                self._event.clear()
            await asyncio.sleep(1)

    async def start(self):
        if self._daemon:
            self._keeper = self.loop.create_task(self._keep_daemon())
        return await super().start()

    async def stop(self, force=True):
        if self._keeper is not None:
            self._keeper.cancel()
            self._event.clear()
            try:
                await self._keeper
            except asyncio.CancelledError:
                pass
            self._keeper = None
        process = self.process
        try:
            if process is None:
                pass
            elif force:
                process.kill()
            else:
                process.terminate()
        except ProcessLookupError:
            pass
        await super().stop(force=force)
