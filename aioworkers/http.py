from aioworkers.net.uri import URL as _URL

try:  # pragma: no cover
    import yarl
except ImportError:  # pragma: no cover
    yarl = None  # type: ignore

if yarl:  # pragma: no cover
    URL = yarl.URL
    _URL.register(yarl.URL)
else:  # pragma: no cover
    URL = _URL  # type: ignore
