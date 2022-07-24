import argparse
import asyncio
import importlib
import inspect
from typing import Mapping


class CommandNotFound(RuntimeError):
    pass


def kwargs_from_argv(params, ns, argv):
    parser = argparse.ArgumentParser()
    for i in params:
        p = params[i]
        if p.annotation is p.empty:
            parser.add_argument('--' + i)
        else:
            parser.add_argument('--' + i, type=p.annotation)
    argv[:] = parser.parse_known_args(argv, namespace=ns)[1]
    return {k: v for k, v in ns.__dict__.items() if v is not None and k in params}


def run(cmd, context, loop=None, ns=None, argv=None):
    loop = loop or context.loop or asyncio.get_event_loop()

    def runner(cmd):
        params: Mapping
        try:
            sig = inspect.signature(cmd)
            params = sig.parameters

        except (ValueError, TypeError):
            params = {}
        kwargs = kwargs_from_argv(params, ns, argv)
        if 'context' in params:
            kwargs['context'] = context
        if asyncio.iscoroutinefunction(cmd):
            return loop.run_until_complete(cmd(**kwargs))
        elif callable(cmd):
            return cmd(**kwargs)
        else:
            return cmd

    cmdl = cmd.split('.')
    obj = context
    for a in cmdl:
        r = getattr(obj, a, None)
        if r is not None:
            obj = r
            continue
        if isinstance(obj, Mapping):
            obj = obj.get(a)
            if obj is None:
                break
        else:
            break
    else:
        if isinstance(obj, str):
            try:
                return run(obj, context, argv=argv, ns=ns)
            except CommandNotFound:
                return obj
        return runner(obj)

    cmdl = []
    package = cmd
    while True:
        try:
            obj = importlib.import_module(package)
            break
        except ImportError:
            if '.' in package:
                package, c = package.rsplit('.', 1)
                cmdl.append(c)
            else:
                obj = None
                break
    if obj is not None:
        cmdl.reverse()
        for a in cmdl:
            obj = getattr(obj, a, None)
            if obj is None:
                break
        else:
            return runner(obj)

    raise CommandNotFound(cmd)
