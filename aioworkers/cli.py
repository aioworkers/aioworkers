import argparse
import asyncio
import logging.config
import multiprocessing
import operator
import os
import signal
import sys
import time
from functools import reduce

from . import config, utils
from .core.context import Context, GroupResolver


parser = argparse.ArgumentParser(prefix_chars='-+')
parser.add_argument('--host')
parser.add_argument('-p', '--port', type=int)

group = parser.add_mutually_exclusive_group(required=False)
group.add_argument('+g', '++groups', nargs='+', action='append',
                   metavar='GROUP', help='Run groups')
group.add_argument('-g', '--groups', nargs='*', action='append',
                   dest='exclude_groups',
                   metavar='GROUP', help='Run all exclude groups')

parser.add_argument('-i', '--interact', action='store_true')
parser.add_argument('-l', '--logging', help='logging level')


try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def main(*config_files, args=None, config_dirs=()):
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    if args is None:
        args = parser.parse_args()
        if getattr(args, 'config', None):
            config_files += tuple(args.config)
        if args.logging:
            logging.basicConfig(level=args.logging.upper())
    conf = config.load_conf(*config_files, search_dirs=config_dirs)

    if args.host:
        conf['http.host'] = args.host
    if args.port is not None:
        conf['http.port'] = args.port

    if not conf.get('app.cls'):
        if conf.get('http.port'):
            conf['app.cls'] = 'aioworkers.http.Application'
        else:
            conf['app.cls'] = 'aioworkers.app.Application'

    def sum_g(list_groups):
        if list_groups:
            return set(reduce(operator.add, list_groups))

    loop = asyncio.get_event_loop()
    context = Context(
        conf, loop=loop,
        group_resolver=GroupResolver(
            include=sum_g(args.groups),
            exclude=sum_g(args.exclude_groups),
            all_groups=args.exclude_groups is not None,
            default=True,
        ),
    )

    if args.interact:
        from .core.interact import shell
        shell(context)

    try:
        with utils.monkey_close(loop), context:
            context.app.run_forever(
                host=conf.http.host,
                port=conf.http.port)
    finally:
        sig = signal.SIGTERM
        while multiprocessing.active_children():
            for p in multiprocessing.active_children():
                os.kill(p.pid, sig)
            time.sleep(0.3)
            print('killall children')
            sig = signal.SIGKILL


def main_with_conf():
    parser.add_argument(
        '-c', '--config', nargs='+',
        type=argparse.FileType('r', encoding='utf-8'))
    main()


if __name__ == '__main__':
    main_with_conf()
