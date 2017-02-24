import argparse
import asyncio
import logging.config

from . import config
from .core.context import Context


parser = argparse.ArgumentParser()
parser.add_argument('--host')
parser.add_argument('-p', '--port', type=int)
parser.add_argument('-i', '--interact', action='store_true')


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

    if 'logging' in conf:
        logging.config.dictConfig(conf.logging)

    if args.host:
        conf['http.host'] = args.host
    if args.port is not None:
        conf['http.port'] = args.port

    if not conf.get('app.cls'):
        if conf.get('http.port'):
            conf['app.cls'] = 'aioworkers.http.Application'
        else:
            conf['app.cls'] = 'aioworkers.app.Application'

    loop = asyncio.get_event_loop()
    context = Context(conf, loop=loop)

    loop.run_until_complete(context.init())

    if args.interact:
        from .core.interact import shell
        shell(context)

    context.app.run_forever(host=conf.http.host, port=conf.http.port)


def main_with_conf():
    parser.add_argument('-c', '--config', nargs='+')
    main()


if __name__ == '__main__':
    main_with_conf()
