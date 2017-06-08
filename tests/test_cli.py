from aioworkers import cli


def test_main(mocker):
    mocker.patch.object(cli, 'asyncio')

    parser = mocker.patch.object(cli, 'parser')
    parser.parse_args().groups = None
    parser.parse_args().exclude_groups = None

    mocker.patch.object(cli, 'logging')
    mocker.patch('aioworkers.core.interact.shell')

    def init(self):
        self.app = mocker.Mock()

    mocker.patch.object(cli.Context, 'init', init)
    cli.main_with_conf()
