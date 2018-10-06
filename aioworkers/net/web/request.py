from ...core.formatter import registry
from .exceptions import HttpException


class Request:
    def __init__(self, url, method, *,
                 body_future=None,
                 headers=(), transport=None,
                 context=None):
        self.url = url
        self.method = method
        self.headers = headers
        self.transport = transport
        self.context = context
        self.content_length = None
        for k, v in headers:
            if k.lower() == 'content-length':
                self.content_length = int(v)
        self._body_future = body_future
        self._finised = False

    def read(self):
        self.transport.resume_reading()
        return self._body_future

    def response(
        self, data=None, status=200, reason='',
        format=None, headers=(),
    ):
        if self._finised:
            return
        elif isinstance(data, HttpException):
            status = data.status
            data = None

        write = self.transport.write
        write(b'HTTP/1.1 ')
        write(str(status).encode())
        write(b' ')
        write(reason.encode())
        write(b'\nServer: aioworkers')
        for h, v in headers:
            write('\n{}: {}'.format(h, v).encode())
        if format:
            formatter = registry.get(format)
            if formatter.mimetypes:
                write(b'\nContent-Type: ')
                write(formatter.mimetypes[0].encode())
            data = formatter.encode(data)
        if data:
            write(b'\nContent-Length: ')
            write(str(len(data)).encode())
        write(b'\n\n')
        if data:
            write(data)
        self.transport.close()
        self._finised = True
        return HttpException(status=status)
