from pathlib import Path

from .core.config import Config, MergeDict


def load_conf(*filenames, **kwargs):
    sd = kwargs.pop('search_dirs', None)
    c = Config(search_dirs=sd or [Path.cwd()])
    conf = MergeDict({
        'http.port': 0,
        'http.host': '0.0.0.0',
        **kwargs,
    })
    conf(c.load(*filenames))
    return conf
