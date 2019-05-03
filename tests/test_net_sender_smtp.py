import pytest


@pytest.fixture
def config_yaml():
    return """
    smtp:
        cls: aioworkers.net.sender.smtp.SMTP
        from: example@example.com
    """


async def test_smtp(context, mocker):
    mocker.patch('smtplib.SMTP')
    await context.smtp.send(
        to='example@example.com',
        subject='test',
        content='text',
        html='<b>text</b>',
    )
