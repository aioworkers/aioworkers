import socket
from typing import List, Optional

from ..core.base import LoggingEntity


class SocketServer(LoggingEntity):
    def __init__(self, *args, **kwargs):
        self._sockets = []
        super().__init__(*args, **kwargs)

    def set_config(self, config):
        super().set_config(config)
        self._sockets.extend(
            self.bind(
                port=self.config.get_int('port', null=True),
                host=self.config.get('host'),
            )
        )

    def set_context(self, context):
        super().set_context(context)
        context.on_cleanup.append(self.cleanup)

    def bind(self, port: int, host: Optional[str] = None) -> List[socket.socket]:
        if not port:
            return []
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        host = host or '0.0.0.0'
        self.logger.info('Bind to %s:%s', host, port)
        sock.bind((host, port))
        sock.setblocking(False)
        return [sock]

    def cleanup(self):
        for s in self._sockets:
            s.close()
