import argparse
import asyncio

from . import config, utils


parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', required=True)
parser.add_argument('--host')
parser.add_argument('-p', '--port', type=int)


try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def main():
    args = parser.parse_args()
    conf = config.load_conf(args.config)
    if args.host:
        conf['http.host'] = args.host
    if args.port is not None:
        conf['http.port'] = args.port

    if conf.get('app.cls'):
        cls = utils.import_name(conf.app.cls)
    elif conf.http.port:
        from .http import Application as cls
    else:
        from .app import Application as cls

    app = cls(loop=asyncio.get_event_loop(), config=conf)
    app.run_forever(host=conf.http.host, port=conf.http.port)


if __name__ == '__main__':
    main()
