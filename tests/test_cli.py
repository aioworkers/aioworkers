from aioworkers import cli


def test_main(mocker):
    mocker.patch.object(cli, 'asyncio')
    mocker.patch.object(cli, 'parser')
    mocker.patch.object(cli, 'logging')
    mocker.patch('aioworkers.core.interact.shell')

    def init(self):
        self.app = mocker.Mock()

    mocker.patch.object(cli.Context, 'init', init)
    cli.main_with_conf()
