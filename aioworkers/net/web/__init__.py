import logging

access_logger = logging.getLogger(__name__ + '.access')


def get_config():
    return dict(
        http=dict(
            port=8080,
            cls='aioworkers.net.web.server.WebServer',
            host='0.0.0.0',
        ),
        app=dict(
            cls='aioworkers.net.web.app.Application',
        ),
    )
