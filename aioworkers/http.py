
try:  # pragma: no cover
    from yarl import URL
except ImportError:  # pragma: no cover
    URL = type('URL', (str,), {})
