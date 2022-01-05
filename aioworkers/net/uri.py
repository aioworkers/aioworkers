import abc
from typing import (
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
)
from urllib.parse import SplitResult, parse_qsl, urlencode, urljoin, urlsplit

from aioworkers.utils import cached_property

TURI = TypeVar('TURI', bound='BaseURI')


def _netloc(
    username: Optional[str] = None,
    password: Optional[str] = None,
    hostname: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    if not hostname:
        return ''
    if username and password:
        result = f'{username}:{password}@{hostname}'
    elif username:
        result = f'{username}@{hostname}'
    elif password:
        result = f':{password}@{hostname}'
    else:
        result = hostname
    if port:
        result = f'{result}:{port}'
    return result


class QueryDict(Mapping[str, str]):
    true = frozenset({'1', 'true'})
    false = frozenset({'0', 'false'})

    __slots__ = ('_data',)
    _data: MutableMapping[str, List[str]]

    def __init__(self, qsl: List[Tuple[str, str]]):
        self._data = {}
        for k, v in reversed(qsl):
            if k in self._data:
                self._data[k].append(v)
            else:
                self._data[k] = [v]

    def __getitem__(self, k: str) -> str:
        v = self._data.get(k)
        if v:
            return v[0]
        else:
            raise KeyError(k)

    def get_bool(self, k: str) -> Optional[bool]:
        for val in self._data.get(k) or ():
            if val in self.true:
                return True
            elif val in self.false:
                return False
        return None

    def get_int(self, k: str) -> Optional[int]:
        for val in self._data.get(k) or ():
            if val.isdigit():
                return int(val)
        return None

    def get_float(self, k: str) -> Optional[float]:
        for val in self._data.get(k) or ():
            try:
                return float(val)
            except ValueError:
                continue
        return None

    def get_list(self, k: str) -> List[str]:
        return list(reversed(self._data.get(k, [])))

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[str]:
        yield from self._data


class BaseURI(str):
    __slots__ = ('_split_result', '_qsl')
    _split_result: SplitResult
    _qsl: List[Tuple[str, str]]

    @classmethod
    def from_bytes(cls: Type[TURI], uri: bytes) -> TURI:
        result = cls(uri.decode())
        return result

    @classmethod
    def from_split(cls: Type[TURI], sr: SplitResult) -> TURI:
        result = cls(sr.geturl())
        result._split_result = sr
        return result

    @cached_property
    def _split(self) -> SplitResult:
        if not hasattr(self, '_split_result'):
            self._split_result = urlsplit(self.__str__())
        return self._split_result

    @cached_property
    def scheme(self) -> Optional[str]:
        return self._split.scheme or None

    @cached_property
    def hostname(self) -> Optional[str]:
        return self._split.hostname or None

    @cached_property
    def port(self) -> Optional[int]:
        return self._split.port or None

    @cached_property
    def username(self) -> Optional[str]:
        return self._split.username or None

    @cached_property
    def password(self) -> Optional[str]:
        return self._split.password or None

    @cached_property
    def path(self) -> Optional[str]:
        return self._split.path or None

    @cached_property
    def query_string(self) -> Optional[str]:
        return self._split.query or None

    @cached_property
    def query(self) -> QueryDict:
        if not hasattr(self, '_qsl'):
            self._qsl = parse_qsl(self._split.query)
        return QueryDict(self._qsl)

    def with_scheme(self: TURI, scheme: str) -> TURI:
        sr = self._split._replace(scheme=scheme)
        return self.from_split(sr)

    def with_auth(
        self: TURI,
        username: Optional[str],
        password: Optional[str] = None,
    ) -> TURI:
        netloc: str = _netloc(
            username,
            password,
            self._split.hostname,
            self._split.port,
        )
        sr = self._split._replace(netloc=netloc)
        return self.from_split(sr)

    def with_username(self: TURI, username: str) -> TURI:
        return self.with_auth(username=username, password=self._split.password)

    def with_password(self: TURI, password: str) -> TURI:
        return self.with_auth(username=self._split.username, password=password)

    def with_hostname(self: TURI, host: str) -> TURI:
        if ':' in host:
            port = None
        else:
            port = self._split.port
        netloc: str = _netloc(
            self._split.username,
            self._split.password,
            host,
            port,
        )
        sr = self._split._replace(netloc=netloc)
        return self.from_split(sr)

    def with_port(self: TURI, port: int) -> TURI:
        netloc: str = _netloc(
            self._split.username,
            self._split.password,
            self._split.hostname,
            port,
        )
        sr = self._split._replace(netloc=netloc)
        return self.from_split(sr)

    def with_path(
        self: TURI,
        path: str,
        drop_query: bool = True,
        drop_fragment: bool = True,
    ) -> TURI:
        path = urljoin(self._split.path, path)
        kw = {}
        if drop_query:
            kw['query'] = ''
        if drop_fragment:
            kw['fragment'] = ''
        sr = self._split._replace(path=path, **kw)
        return self.from_split(sr)

    def with_query(self: TURI, *args, **kwargs) -> TURI:
        if args:
            query = '&'.join(args)
        elif kwargs:
            query = urlencode(kwargs)
        else:
            query = ''
        sr = self._split._replace(query=query)
        return self.from_split(sr)

    def update_query(self: TURI, **kwargs) -> TURI:
        if not hasattr(self, '_qsl'):
            self._qsl = parse_qsl(self._split.query)
        qsl = []
        for k, v in self._qsl:
            if k not in kwargs:
                qsl.append((k, v))
        qsl.extend(kwargs.items())
        query = urlencode(qsl)
        sr = self._split._replace(query=query)
        return self.from_split(sr)

    def __repr__(self):
        return f'{self.__class__.__name__}({super().__repr__()})'


class URI(BaseURI):
    pass


class URL(BaseURI, abc.ABC):
    def __truediv__(self, other):
        if not isinstance(other, str):
            raise TypeError
        elif other.startswith('/'):
            raise ValueError('Not allowed abs path')
        path = self._split.path
        if path.endswith('/'):
            path += other
        else:
            path = f'{path}/{other}'
        sr = self._split._replace(path=path, query='', fragment='')
        return self.from_split(sr)
