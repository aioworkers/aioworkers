from unittest import mock

import pytest

from aioworkers.worker.updater import BaseUpdater, PipUpdater
from aioworkers.utils import import_uri


@pytest.fixture
def config(config):
    config.update(
        base_updater=dict(
            cls=import_uri(BaseUpdater),
            autorun=False,
        ),
        pip_updater=dict(
            cls=import_uri(PipUpdater),
            package=dict(name='pip'),
            autorun=False,
        )
    )
    return config


@pytest.mark.parametrize('p', ['base_updater', 'pip_updater'])
async def test_run(context, mocker, make_coro, p):
    w = context[p]
    mocker.patch('aioworkers.worker.updater.atexit')
    mocker.patch.object(w, 'run_cmd', make_coro())
    with mock.patch.object(w._loop, 'stop'):
        await w()
    await w.update()
