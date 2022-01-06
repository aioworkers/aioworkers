from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    List,
    Mapping,
    Optional,
    Tuple,
)
from urllib.parse import SplitResult

from aioworkers.core.context import Context
from aioworkers.core.formatter import registry
from aioworkers.utils import cached_property

from ..uri import URL
from .exceptions import HttpException

if TYPE_CHECKING:  # pragma: no cover
    from .app import Application
else:
    Application = Any


class Request:
    def __init__(
        self,
        scope: Mapping,
        receive: Callable[[], Awaitable],
        send: Callable[[Mapping], Awaitable],
        context: Context,
        app: Application,
    ):
        self._scope = scope
        self._receive = receive
        self._send = send
        self.context = context
        self.app = app
        self._finised = False

    async def read(self):
        msg = await self._receive()
        return msg['body']

    @cached_property
    def method(self) -> str:
        return self._scope['method']

    @cached_property
    def url(self) -> URL:
        return URL.from_split(
            SplitResult(
                scheme=self._scope['scheme'],
                netloc='',
                path=self._scope.get('path', ''),
                query=self._scope.get('query_string', b'').decode(),
                fragment='',
            )
        )

    @cached_property
    def content_length(self) -> int:
        cl = self.headers.get('content-length', 0)
        return int(cl)

    @cached_property
    def headers(self) -> Mapping[str, str]:
        result = {}
        for k, v in self._scope['headers']:
            val = v.decode()
            key = k.decode()
            result[k] = v
            result[key] = val
            result[key.lower()] = val
        return result

    def response(
        self,
        data: Any = None,
        status: int = 200,
        reason: str = '',
        format: Optional[str] = None,
        headers: List[Tuple[bytes, bytes]] = None,
    ):
        if self._finised:
            return
        elif isinstance(data, HttpException):
            status = data.status
            data = None

        if not headers:
            headers = []
        else:
            headers = list(headers)

        if isinstance(data, bytes):
            pass
        elif isinstance(data, str):
            data = data.encode()
            headers.append((b'Content-Type', b'text/plain'))
        elif format:
            formatter = registry.get(format)
            if formatter.mimetypes:
                header = (b'Content-Type', formatter.mimetypes[0].encode())
                headers.append(header)
            data = formatter.encode(data)

        self._send(
            {
                'type': 'http.response.start',
                'status': status,
                'reason': reason,
                'headers': headers,
            }
        )
        self._send(
            {
                'type': 'http.response.body',
                'body': data,
            }
        )

        self._finised = True
        return HttpException(status=status)
