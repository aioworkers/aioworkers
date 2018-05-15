import abc

try:  # pragma: no cover
    import yarl
except ImportError:  # pragma: no cover
    yarl = None


class _URL(str, abc.ABC):
    def __truediv__(self, other):
        if not isinstance(other, str):
            raise TypeError
        return _URL(self.rstrip('/') + '/' + other.lstrip('/'))

    def __repr__(self):
        return 'URL({})'.format(super().__repr__())


if yarl:  # pragma: no cover
    URL = yarl.URL
    _URL.register(yarl.URL)
else:  # pragma: no cover
    URL = _URL
