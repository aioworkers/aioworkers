import asyncio
import subprocess
from collections import Mapping, Sequence

from ..core.formatter import FormattedEntity
from .base import Worker


class Subprocess(FormattedEntity, Worker):
    """
    config:
        cmd: str - shell command with mask python format
             list[str] - exec command with mask python format
        stdout: [none | PIPE | DEVNULL]
        stderr: [none | PIPE | DEVNULL]
        wait: bool - default True for wait shutdown process
        format: [json|str|bytes]
    """

    async def init(self):
        if self.config.get('stdout'):
            self._stdout = getattr(subprocess, self.config.get('stdout'))
        elif 'stdout' in self.config:
            self._stdout = None
        else:
            self._stdout = subprocess.PIPE

        if self.config.get('stderr'):
            self._stderr = getattr(subprocess, self.config.get('stderr'))
        else:
            self._stderr = None
        self._wait = self.config.get('wait', True)
        await super().init()

    @property
    def process(self):
        return getattr(self, '_process', None)

    def make_command(self, value):
        cmd = self.config.get('cmd')
        if isinstance(cmd, list) and not value:
            return cmd
        elif value is None:
            return cmd,
        elif not cmd and isinstance(value, Sequence):
            return value
        elif not cmd and isinstance(value, str):
            return value,
        elif isinstance(cmd, list) and isinstance(value, str):
            return cmd + [value]
        elif isinstance(cmd, list) and isinstance(value, Sequence):
            result = list(cmd)
            result.extend(value)
            return result
        elif isinstance(cmd, list) and isinstance(value, Mapping):
            return [i.format_map(value) for i in cmd]
        elif isinstance(cmd, str) and isinstance(value, str):
            return self.config.cmd + ' ' + value,
        elif isinstance(cmd, str) and isinstance(value, Mapping):
            return self.config.cmd.format_map(value),
        elif isinstance(cmd, str) and isinstance(value, Sequence):
            return self.config.cmd.format(*value),
        else:
            raise ValueError(value)

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
        if len(cmd) > 1:
            coro = asyncio.create_subprocess_exec
        else:
            coro = asyncio.create_subprocess_shell
        self._process = await coro(
            *cmd, stdout=self._stdout, stderr=self._stderr, loop=self.loop)
        if self._wait:
            await self._process.wait()
        if self._stdout:
            data = await self._process.stdout.read()
            return self.decode(data)

    run = run_cmd

    async def stop(self, force=True):
        process = self.process
        if process is None:
            pass
        elif force:
            process.kill()
        else:
            process.terminate()
        await super().stop(force=force)
