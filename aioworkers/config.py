from pathlib import Path

from .core.config import Config, MergeDict


def load_conf(filename, *args, **kwargs):
    c = Config(search_dirs=[Path.cwd()])
    conf = MergeDict({
        'http.port': 0,
        'http.host': '0.0.0.0',
    })
    conf(c.load(filename))
    return conf
