import pytest


@pytest.fixture
def config_yaml():
    return """
    local_sender:
        cls: aioworkers.net.sender.proxy.Facade
        queue: .queue1

    queue1:
        cls: aioworkers.queue.base.Queue

    worker:
        cls: aioworkers.net.sender.proxy.Worker
        autorun: true
        input: .queue1
        sender: remote_sender

    remote_sender:
        cls: aioworkers.net.sender.proxy.Facade
        queue: .queue2

    queue2:
        cls: aioworkers.queue.base.Queue
    """


async def test_proxy_chains(context):
    await context.local_sender.send(
        to='example@example.com',
        subject='test',
        content='text',
        html='<b>text</b>',
    )
    msg = await context.queue2.get()
    assert msg['subject'] == 'test'
