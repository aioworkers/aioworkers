
try:
    from yarl import URL
except ImportError:
    URL = type('URL', (str,), {})
