import io

from aioworkers import cli, utils


def test_main(mocker):
    mocker.patch.object(cli, 'asyncio')

    parser = mocker.patch.object(cli, 'parser')
    ns = mocker.Mock()
    ns.config = ()
    ns.config_stdin = False
    ns.multiprocessing = False
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


def test_stdin_config():
    f = io.BytesIO()
    data = (123,)
    utils.dump_to_fd(f, data)
    f.seek(0)
    assert data == utils.load_from_fd(f)
