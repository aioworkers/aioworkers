from aioworkers import cli


def test_main(mocker):
    mocker.patch.object(cli, 'asyncio')

    parser = mocker.patch.object(cli, 'parser')
    ns = mocker.Mock()
    ns.config = ()
    ns.groups = None
    ns.exclude_groups = None
    parser.parse_known_args.return_value = ns, ()

    mocker.patch.object(cli, 'logging')
    mocker.patch('aioworkers.core.interact.shell')

    def init(self):
        self.app = mocker.Mock()
    context = mocker.patch.object(cli, 'Context')
    context.init = init
    cli.main_with_conf()
