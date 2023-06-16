import asyncio
import shlex
import subprocess
import sys
import weakref
from asyncio.subprocess import Process
from typing import (
    Any,
    Callable,
    Coroutine,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
)

from aioworkers.core.config import ValueExtractor

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

    _event: asyncio.Event
    _subprocess_kwargs: MutableMapping[str, Any]
    _processes: MutableMapping[int, Process]
    _cmd: Tuple[str, ...]
    _shell: bool
    _keeper: Optional[asyncio.Task]

    def __init__(self, *args, **kwargs):
        self._processes = weakref.WeakValueDictionary()
        self._cmd = ()
        self._shell = False
        self._config_stdin = False
        self._wait = True
        self._daemon = False
        self._keeper = None
        self.params = {"python": sys.executable, "worker": self}
        self._subprocess_kwargs = {}
        super().__init__(*args, **kwargs)

    def set_config(self, config: ValueExtractor):
        super().set_config(config)

        if self.config.get("stdin"):
            stdin = getattr(subprocess, self.config.get("stdin"))
            self._subprocess_kwargs["stdin"] = stdin
        elif "stdin" not in self.config:
            self._subprocess_kwargs["stdin"] = subprocess.PIPE

        if self.config.get("stdout"):
            stdout = getattr(subprocess, self.config.get("stdout"))
            self._subprocess_kwargs["stdout"] = stdout
        elif "stdout" not in self.config:
            self._subprocess_kwargs["stdout"] = subprocess.PIPE

        if self.config.get("stderr"):
            stderr = getattr(subprocess, self.config.get("stderr"))
            self._subprocess_kwargs["stderr"] = stderr

        self._wait = self.config.get("wait", True)

        self._config_stdin = False

        is_shell = False
        if "aioworkers" in self.config:
            cmd = ["{python}", "-m", "aioworkers", "--config-stdin"]
            value = self.config["aioworkers"]
            if isinstance(value, str):
                cmd.append(value)
                cmd = [" ".join(cmd)]
                is_shell = True
            elif isinstance(value, list):
                cmd.extend(value)
            else:
                raise TypeError(value)
            self._subprocess_kwargs["stdin"] = subprocess.PIPE
            self._config_stdin = True
        else:
            cmd = self.config.get("cmd") or []
            if isinstance(cmd, str):
                cmd = [cmd]
                is_shell = True
            elif not isinstance(cmd, (list, tuple)):
                raise ValueError(cmd)
        self._cmd = tuple(cmd)
        self._shell = self.config.get("shell", is_shell)

        self.params.update(dict(self.config.get("params", ())))
        self.params.setdefault("config", self.config)

        self._daemon = self.config.get("daemon")
        self._keeper = None
        if self._daemon:
            self._wait = False

    async def init(self):
        self._event = asyncio.Event()
        self._event.clear()
        await super().init()

    @property
    def process(self) -> Optional[Process]:
        for p in self._processes.values():
            if p.returncode is None:
                return p
        return None

    def create_subprocess(self, *args) -> Coroutine[Any, Any, Process]:
        c: Callable[..., Coroutine[Any, Any, Process]]
        if self._shell:
            c = asyncio.create_subprocess_shell
        else:
            c = asyncio.create_subprocess_exec
        return c(*args, **self._subprocess_kwargs)

    def make_command(self, value: Any = None) -> Tuple[str, ...]:
        args: Sequence[str] = ()
        m = dict(self.params)
        if isinstance(value, Mapping):
            m.update(value)
        elif isinstance(value, str):
            args = (value,)
        elif isinstance(value, Sequence):
            args = value

        cmd = [part.format_map(m) for part in self._cmd]

        if self._shell:
            cmd.extend(args)
            return (" ".join(cmd),)
        elif not self._shell and len(self._cmd) == 1:
            cmd = shlex.split(cmd[0])
        cmd.extend(args)
        return tuple(cmd)

    async def run_cmd(self, *args, **kwargs):
        if len(args) > 1:
            value: Any = args
        elif args:
            value = args[0]
        elif kwargs:
            value = kwargs
        else:
            value = None
        cmd = self.make_command(value)
        self.logger.info(" ".join(cmd))
        process = await self.create_subprocess(*cmd)
        self._processes[process.pid] = process
        if self._config_stdin:
            assert process.stdin
            utils.dump_to_fd(process.stdin, self.context.config)
            await process.stdin.drain()
        if self._wait:
            await process.wait()
        else:
            return process
        if not self._daemon and process.stdout is not None:
            data = await process.stdout.read()
            return self.decode(data)

    async def work(self):
        if self._daemon:
            await self._event.wait()
        return await super().work()

    async def _keep_daemon(self):
        while True:
            try:
                process = await self.run_cmd()
                self._event.set()
                await process.wait()
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
        for process in self._processes.values():
            try:
                if process.returncode is not None:
                    continue
                elif force:
                    process.kill()
                else:
                    process.terminate()
                await process.wait()
            except ProcessLookupError:
                pass
        await super().stop(force=force)
