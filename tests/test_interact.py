from aioworkers.core import interact


def test_shell(mocker):
    mocker.patch.object(interact.Shell, 'start')
    interact.shell(None)

    mocker.patch('IPython.embed')
    t = interact.Shell(args=(None,))
    t.run()

    mocker.patch('concurrent.futures.Future.result')
    context = mocker.Mock()
    interact._await(1, context)
