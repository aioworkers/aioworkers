import argparse
import asyncio
import logging.config

from . import config
from .app import BaseApplication
from .core import loader


parser = argparse.ArgumentParser()
parser.add_argument('--host')
parser.add_argument('-p', '--port', type=int)


try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def main(*config_files, args=None, config_dirs=()):
    if args is None:
        args = parser.parse_args()
        if getattr(args, 'config', None):
            config_files += tuple(args.config)
    conf = config.load_conf(*config_files, search_dirs=config_dirs)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(loader.load_entities(conf, loop=loop))

    if 'logging' in conf:
        logging.config.dictConfig(conf.logging)

    if args.host:
        conf['http.host'] = args.host
    if args.port is not None:
        conf['http.port'] = args.port

    if isinstance(conf.get('app'), BaseApplication):
        app = conf.app
    else:
        if conf.http.port:
            from .http import Application as cls
        else:
            from .app import Application as cls
        app = loop.run_until_complete(cls.factory(loop=loop, config=conf))
        conf['app'] = app

    app.run_forever(host=conf.http.host, port=conf.http.port)


if __name__ == '__main__':
    parser.add_argument('-c', '--config', nargs='*', required=True)
    main()
