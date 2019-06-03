import socket

from ..core.base import LoggingEntity


class SocketServer(LoggingEntity):
    def __init__(self, *args, **kwargs):
        self._sockets = []
        super().__init__(*args, **kwargs)

    def set_config(self, config):
        super().set_config(config)
        port = self.config.get_int('port', null=True)
        if port:
            host = self.config.get('host')
            self._sockets.append(self.bind(port, host))

    def bind(self, port, host=None, backlog=128):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        host = host or '0.0.0.0'
        self.logger.info('Bind to %s:%s', host, port)
        sock.bind((host, port))
        sock.setblocking(False)
        sock.listen(backlog)
        return sock
