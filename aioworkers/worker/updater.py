import atexit
import os
import sys
import pkg_resources

from aioworkers.worker.subprocess import Subprocess


class BaseUpdater(Subprocess):
    def init(self):
        c = self.config
        c.autorun = c.get('autorun', True)
        c.persist = c.get('persist', True)
        c.stderr = c.get('stderr', None)
        c.stdout = c.get('stdout', None)
        c.crontab = c.get('crontab', '0 * * * *')
        return super().init()

    async def can_restart(self):
        return True

    async def wait_restart(self):
        pass

    async def restart(self):
        atexit.register(
            os.execl, sys.executable,
            sys.executable, *sys.argv)
        self.loop.stop()

    async def can_update(self):
        return True

    async def update(self):
        await self.run_cmd()

    async def run(self, value=None):
        if not await self.can_update():
            return
        await self.update()
        if await self.can_restart():
            await self.wait_restart()
            await self.restart()


class PipUpdater(BaseUpdater):
    def init(self):
        c = self.config
        c.cmd = c.get('cmd', [
            sys.executable,
            '-m', 'pip', 'install', '-U',
        ])
        self.v = self.version(c.package.name)
        return super().init()

    async def can_update(self):
        # TODO parse https://pypi.python.org/pypi?:action=doap&name={package.name}
        return True

    @classmethod
    def version(cls, package):
        try:
            return pkg_resources.get_distribution(package).version
        except pkg_resources.DistributionNotFound:
            pass

    async def update(self):
        package = self.config.package
        val = package.get('link', package.name)
        await self.run_cmd(val)
