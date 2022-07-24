import logging
import urllib.error
import urllib.request
from http.client import HTTPResponse
from typing import Any, Awaitable, Callable, Mapping, Optional, Tuple, Union

from aioworkers.core.base import ExecutorEntity
from aioworkers.http import URL

logger = logging.getLogger(__name__)


class Request:
    def __init__(self, session: 'Session', *args, **kwargs):
        self._session = session
        self._request = urllib.request.Request(*args, **kwargs)
        self._response = None  # type: Optional[Response]

    async def __aenter__(self) -> 'Response':
        logger.info('Request %r', self._request)
        try:
            response = await self._session.run(
                self._session.opener.open,
                self._request,
            )
        except urllib.error.HTTPError as e:
            response = e
        logger.info('Response %r', response)
        self._response = Response(response, self._session)
        return self._response

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        assert self._response
        await self._response.close()


class Response:
    def __init__(
        self,
        response: HTTPResponse,
        session: 'Session',
    ):
        self._response = response
        self._session = session

    @property
    def status(self):
        return self._response.status

    @property
    def reason(self):
        return self._response.reason

    @property
    def headers(self):
        return self._response.headers

    async def read(self) -> bytes:
        return await self._session.run(self._response.read)

    def isclosed(self):
        return self._response.isclosed()

    async def close(self):
        return await self._session.run(self._response.close)


class Session:
    def __init__(
        self,
        runner: Callable[..., Awaitable[Any]],
        headers: Mapping = None,
        conn_timeout: float = 60,
        read_timeout: float = 60,
        handlers: Optional[Tuple[urllib.request.BaseHandler]] = None,
    ):
        self.run = runner
        self._headers = headers
        self._conn_timeout = conn_timeout
        self._read_timeout = read_timeout
        if handlers is None:
            handlers = (
                urllib.request.HTTPCookieProcessor(),
            )
        self.opener = urllib.request.build_opener(*handlers)
        if headers:
            if isinstance(headers, Mapping):
                self.opener.addheaders = list(headers.items())
            else:
                self.opener.addheaders = list(headers)

    @classmethod
    def from_entity(cls, entity: ExecutorEntity, **kwargs) -> 'Session':
        kwargs.update(
            runner=entity.run_in_executor,
        )
        return cls(**kwargs)

    def request(self, url: Union[str, URL], method='get', **kwargs) -> Request:
        if isinstance(url, URL):
            url = str(url)
        kwargs.update(
            url=url,
            method=method.upper(),
        )
        return Request(self, **kwargs)

    async def close(self):
        self.opener.close()
