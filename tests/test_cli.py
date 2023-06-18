import argparse
import io
import tempfile

import pytest

from aioworkers import cli, utils
from aioworkers.core.config import ValueExtractor


def test_main(mocker):
    mocker.patch.object(cli, 'asyncio')
    mocker.patch('os.kill')

    actives = [[mocker.Mock()]] * 7
    actives[-3] = []
    iter_actives = iter(actives)
    mocker.patch('multiprocessing.active_children', lambda: next(iter_actives, ()))
    mocker.patch('multiprocessing.connection')

    parser = mocker.patch.object(cli, 'parser')
    ns = mocker.Mock()
    ns.config = ()
    ns.config_stdin = False
    ns.multiprocessing = False
    ns.groups = None
    ns.exclude_groups = None
    ns.shutdown_timeout = 1
    parser.parse_known_args.return_value = ns, [__file__]

    mocker.patch.object(cli, 'logging')
    mocker.patch('aioworkers.core.interact.shell')

    def init(self):
        self.app = mocker.Mock()

    context = mocker.patch.object(cli, 'Context')
    context.init = init
    cli.main()
    cli.main(commands=("aioworkers.cli",))


def test_stdin_config():
    f = io.BytesIO()
    data = (123,)
    utils.dump_to_fd(f, data)
    f.seek(0)
    assert data == utils.load_from_fd(f)


@pytest.mark.parametrize(
    'cfg, count',
    [
        (dict(count=1), 1),
        (dict(count=-12, cpus=1), 12),
        (dict(count=12, cpus=0), 12),
        (dict(count=-12, cpus=0), 0),
        (dict(cpus=0), 0),
        (dict(cpus=1), 24),
    ],
)
def test_process_iter(cfg, count):
    processes = cli.process_iter(ValueExtractor(dict(web=cfg)), 24)
    assert processes == [
        dict(
            name=f'web-{n}',
            groups=(),
        )
        for n in range(count)
    ]


@pytest.mark.timeout(5)
def test_loop_run():
    cli.loop_run(cmds=['time.time'])


def test_pidfile():
    p = cli.PidFileType("w")
    with tempfile.NamedTemporaryFile() as t:
        f = p(t.name)
    assert f is not None


def test_uritype(mocker):
    mocker.patch.object(cli, "urlopen")
    p = cli.UriType()

    with tempfile.NamedTemporaryFile() as t:
        f = p(t.name)
    assert f is not None

    f = p("http://localhost")
    assert f is not None


def test_plugin():
    parser = argparse.ArgumentParser()
    p = cli.plugin()
    p.add_arguments(parser)


def test_create_process():
    p = cli.create_process({"name": "", "groups": []})
    p.kill()
    p.join()
