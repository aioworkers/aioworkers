class HttpException(Exception):
    def __init__(self, status=200):
        self.status = status
