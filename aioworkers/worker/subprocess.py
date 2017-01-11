import asyncio
import subprocess

from ..core.formatter import FormattedEntity
from .base import Worker


class Subprocess(FormattedEntity, Worker):
    """
    config:
        cmd: str - shell command with mask python format
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
        if hasattr(self, '_process') and self._process is not None:
            return self._process

    def make_command(self, value):
        if not self.config.get('cmd'):
            return value
        elif isinstance(value, str):
            return self.config.cmd + ' ' + value
        elif isinstance(value, dict):
            return self.config.cmd.format_map(value)
        elif isinstance(value, list):
            return self.config.cmd.format(*value)
        else:
            raise ValueError()

    async def run_cmd(self, *args, **kwargs):
        if args:
            value = args[0]
        elif kwargs:
            value = kwargs
        else:
            value = None
        cmd = self.make_command(value)
        self._process = await asyncio.create_subprocess_exec(
            cmd, stdout=self._stdout, stderr=self._stderr)
        if self._wait:
            await self._process.wait()
        if self._stdout:
            data = await self._process.stdout.read()
            return self.decode(data)

    run = run_cmd
