import argparse
import asyncio
import logging.config
import multiprocessing.connection
import operator
import os
import signal
import sys
import time
from functools import partial, reduce
from pathlib import Path
from urllib.parse import splittype  # type: ignore
from urllib.request import urlopen

from . import utils
from .core import command
from .core.config import Config
from .core.context import Context, GroupResolver
from .core.plugin import Plugin, search_plugins

parser = argparse.ArgumentParser(prefix_chars='-+')

group = parser.add_mutually_exclusive_group(required=False)
group.add_argument(
    '+g',
    '++groups',
    nargs='+',
    action='append',
    metavar='GROUP',
    help='Run groups',
)
group.add_argument(
    '-g',
    '--groups',
    nargs='*',
    action='append',
    dest='exclude_groups',
    metavar='GROUP',
    help='Run all exclude groups',
)

parser.add_argument('--multiprocessing', action='store_true')
parser.add_argument('-i', '--interact', action='store_true')
parser.add_argument('-I', '--interact-kernel', action='store_true')
parser.add_argument('-l', '--logging', help='logging level')
parser.add_argument('--shutdown-timeout', type=float, default=60)


PROMPT = "======== Running aioworkers ========\n" \
    "(Press CTRL+C to quit)"


class PidFileType(argparse.FileType):
    def __call__(self, string):
        f = super().__call__(string)
        with f:
            f.write(str(os.getpid()))
        return f


parser.add_argument(
    '--pid-file',
    help='Process ID file',
    type=PidFileType('w'),
)

try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


context = Context(Config())


def main(
    *config_files,
    args=None,
    config_dirs=(),
    commands=(),
    config_dict=None,
):
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    context.config.search_dirs.extend(config_dirs)

    if not commands:
        p = Path(sys.argv[0])
        if __package__ in (p.parent.name, p.name):
            commands += (__name__,)
        elif p.name.startswith('__'):
            commands += (p.parent.name,)
        else:
            commands += (p.name,)

    plugins = search_plugins()
    plugins.extend(search_plugins(*commands, force=True))
    for i in plugins:
        i.add_arguments(parser)

    if args is None:
        args, argv = parser.parse_known_args()
        cmds = list(commands)
        while argv and not argv[0].startswith('-'):
            cmds.append(argv.pop(0))
        if getattr(args, 'config', None):
            config_files += tuple(args.config)
        if getattr(args, 'config_stdin', None):
            assert (
                not args.interact
            ), 'Can not be used --config-stdin with --interact'
            config_dict = utils.load_from_fd(sys.stdin.buffer)
        if args.logging:
            logging.basicConfig(level=args.logging.upper())
    else:
        cmds, argv = list(commands), []

    config = context.config
    plugins.extend(search_plugins(*cmds))
    for p in plugins:
        args, argv = p.parse_known_args(args=argv, namespace=args)
        config.load(*p.configs)
        config.update(p.get_config())
    cmds = [cmd for cmd in cmds if cmd not in sys.modules]

    config.load(*config_files)
    config_dict and config.update(config_dict)

    def sum_g(list_groups):
        if list_groups:
            return set(reduce(operator.add, list_groups))

    run = partial(
        loop_run,
        group_resolver=GroupResolver(
            include=sum_g(args.groups),
            exclude=sum_g(args.exclude_groups),
            all_groups=args.exclude_groups is not None,
            default=True,
        ),
        cmds=cmds,
        argv=argv,
        ns=args,
        prompt=PROMPT,
    )

    try:
        if args.multiprocessing:
            with context.processes():
                print(PROMPT)
                logger = multiprocessing.get_logger()
                processes = process_iter(config.get('processes', {}))
                for p in processes:
                    logger.info('Create process %s', p['name'])
                    p['process'] = create_process(p)
                while True:
                    multiprocessing.connection.wait(
                        map(lambda x: x['process'].sentinel, processes),
                    )
                    for p in processes:
                        proc = p['process']  # type: multiprocessing.Process
                        if not proc.is_alive():
                            logger.critical('Recreate process %s', p['name'])
                            p['process'] = create_process(p)
                    time.sleep(1)

        elif args.interact:
            from .core.interact import shell

            args.print = lambda *args: None
            os.environ['AIOWORKERS_MODE'] = 'console'
            shell(run)
        elif args.interact_kernel:
            from .core.interact import kernel

            kernel(run)
        else:
            run()
    except KeyboardInterrupt:
        pass
    finally:
        for p in multiprocessing.active_children():
            os.kill(p.pid, signal.SIGTERM)
        t = time.monotonic()
        sentinels = [p.sentinel for p in multiprocessing.active_children()]
        while sentinels and time.monotonic() - t < args.shutdown_timeout:
            multiprocessing.connection.wait(sentinels)
            sentinels = [p.sentinel for p in multiprocessing.active_children()]
        while multiprocessing.active_children():
            print('killall children')
            for p in multiprocessing.active_children():
                os.kill(p.pid, signal.SIGKILL)
            time.sleep(0.3)


def process_iter(cfg, cpus=os.cpu_count() or 1):
    result = []
    for k, v in cfg.items():
        if 'count' in v or 'cpus' in v:
            c = v.get_int('count', 0) + int(cpus * v.get_float('cpus', 0))
            for i in range(c):
                result.append(
                    {
                        'name': '{}-{}'.format(k, i),
                        'groups': v.get('groups', ()),
                    }
                )
        else:
            result.append(
                {
                    'name': k,
                    'groups': v.get('groups', ()),
                }
            )
    return result


def create_process(cfg):
    p = multiprocessing.Process(
        target=loop_run,
        kwargs=dict(
            group_resolver=GroupResolver(
                include=set(cfg['groups']),
                exclude=set(),
                all_groups=False,
                default=True,
            ),
            process_name=cfg['name'],
        ),
        name=cfg['name'],
        daemon=True,
    )
    p.start()
    return p


def loop_run(
    conf=None,
    future=None,
    group_resolver=None,
    ns=None,
    cmds=None,
    argv=None,
    loop=None,
    prompt=None,
    process_name=None,
):
    if process_name:
        utils.setproctitle(process_name)
    if loop is None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if conf:
        context.set_config(conf)
    if loop is not None:
        context.set_loop(loop)
    if group_resolver is not None:
        context.set_group_resolver(group_resolver)

    if not cmds:
        cmds = ['run_forever']
        prompt and print(prompt)
    argv = argv or []
    ns = ns or argparse.Namespace()

    async def shutdown():
        await context.__aexit__(None, None, None)
        if hasattr(loop, 'shutdown_asyncgens'):
            await loop.shutdown_asyncgens()
        loop.stop()

    with utils.monkey_close(loop), context:
        context.loop.add_signal_handler(
            signal.SIGTERM, lambda *args: loop.create_task(shutdown())
        )
        if future is not None:
            future.set_result(context)
        for cmd in cmds:
            try:
                result = command.run(cmd, context, argv=argv, ns=ns)
            except command.CommandNotFound:
                print('Command {} not found'.format(cmd))
                continue
            if result is not None:
                print('{} => {}'.format(cmd, result))
        if not loop.is_closed() and hasattr(loop, 'shutdown_asyncgens'):
            loop.run_until_complete(loop.shutdown_asyncgens())


class UriType(argparse.FileType):
    def __call__(self, string):
        t, path = splittype(string)
        if not t:
            return super().__call__(string)
        return urlopen(string)


class ExtendAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        getattr(namespace, self.dest).extend(values)


class plugin(Plugin):
    def add_arguments(self, parser):
        default = []
        parser.set_defaults(config=default)
        parser.add_argument(
            '-c',
            '--config',
            nargs='+',
            action=ExtendAction,
            type=UriType('r', encoding='utf-8'),
        )
        parser.add_argument('--config-stdin', action='store_true')


def main_with_conf(*args, **kwargs):
    import warnings

    warnings.warn(
        'Deprecated main_with_conf, use main',
        DeprecationWarning,
        stacklevel=2,
    )
    main(*args, **kwargs)


if __name__ == '__main__':
    main()
