import atexit
import os
import sys

if sys.version_info < (3, 8):  # no cov
    from pkg_resources import get_distribution as distribution
else:
    from importlib.metadata import distribution

from aioworkers.worker.subprocess import Subprocess


class BaseUpdater(Subprocess):
    def set_config(self, config):
        super().set_config(config)
        cfg = self._config
        self._config = cfg.new_parent(
            {} if cfg.get('sleep') else {'crontab': '0 * * * *'},
            autorun=True,
            persist=True,
            stderr=None,
            stdout=None,
        )

    async def can_restart(self):
        return True

    async def wait_restart(self):
        pass

    async def restart(self):
        atexit.register(os.execl, sys.executable, sys.executable, *sys.argv)
        self.loop.stop()

    async def can_update(self):
        return True

    async def update(self):
        await self.run_cmd()

    async def run(self, value=None):
        if await self.can_update():
            await self.update()
            if await self.can_restart():
                await self.wait_restart()
                await self.restart()


class PipUpdater(BaseUpdater):
    pip = (sys.executable, '-m', 'pip')

    def set_config(self, config):
        super().set_config(config)
        c = self._config
        params = ['install']
        if c.get('upgrade', True):
            params.append('-U')
        if 'find-links' in c:
            params.append('--find-links')
            params.append(c.get('find-links'))
        self._config = c.new_parent(cmd=list(self.pip) + params)
        self.current_version = self.version(c.package.name)
        self.new_version = self.current_version

    async def can_update(self):
        # TODO parse https://pypi.python.org/pypi?:action=doap&name={package.name}  # noqa
        return True

    @classmethod
    def version(cls, package):
        try:
            d = distribution(package)
        except Exception:
            pass
        else:
            return d.version

    async def update(self):
        package = self.config.package
        val = package.get('link', package.name)
        await self.run_cmd(val)
        process = self.process
        if process and not process.returncode:
            self.current_version = self.new_version
