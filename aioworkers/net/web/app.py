import asyncio
import inspect
from collections import Iterable, Mapping, defaultdict, namedtuple

from aioworkers.core.base import AbstractNamedEntity
from aioworkers.net.web.exceptions import HttpException

Route = namedtuple('Route', 'handler kwargs')


class Application(AbstractNamedEntity):
    async def init(self):
        self._routes = defaultdict(dict)
        resources = self.config.get('resources')
        for url, name, routes in Resources(resources):
            for method, operation in routes.items():
                if not isinstance(operation, Mapping):
                    raise TypeError(
                        'operation for {method} {url} expected Mapping, not {t}'.format(
                            method=method.upper(), url=url, t=type(operation)))
                operation = dict(operation)
                handler = operation.pop('handler')
                self.add_route(method, url, handler, name=name)

    def add_route(self, method, path, handler, name=None, **kwargs):
        handlers = self._routes[path]
        method = method.upper()
        assert method not in handlers
        h = self.context.get_object(handler)
        if callable(h):
            try:
                kwargs = inspect.signature(h).parameters
            except ValueError:
                kwargs = ()
        else:
            kwargs = ()
        handlers[method] = Route(h, kwargs)

    async def handler(self, request):
        path = request.url.path
        method = request.method
        if path not in self._routes:
            raise HttpException(status=404)
        handlers = self._routes[path]
        if method not in handlers:
            raise HttpException(status=405)
        route = handlers[method]
        handler = route.handler
        kwargs = {}
        if 'request' in route.kwargs:
            kwargs['request'] = request
        if 'context' in route.kwargs:
            kwargs['context'] = self._context
        if asyncio.iscoroutinefunction(handler):
            request.app = self
            handler = await handler(**kwargs)
        elif callable(handler):
            handler = handler(**kwargs)
        if asyncio.isfuture(handler):
            handler = await handler
        return request.response(handler, format='json')


class Resources(Iterable):
    def __init__(self, resources: Mapping):
        self._resources = resources
        self._prepared = self._sort_resources(resources)

    def __iter__(self):
        return iter(self._prepared)

    def _iter_resources(self, resources, prefix=''):
        if not resources:
            return
        elif not isinstance(resources, Mapping):
            raise TypeError(
                'Resources should be described in dict %s' % resources)
        prefix += resources.get('prefix', '')
        for name, sub in resources.items():
            if name == 'prefix':
                continue
            elif not isinstance(sub, Mapping):
                raise TypeError(
                    'Resource should be described in dict %s' % sub)
            routes = dict(sub)
            priority = routes.pop('priority', 0)
            if 'include' in routes:
                url = name if name.startswith('/') else None
                if url:
                    url = prefix + url
                else:
                    url = prefix
                if url:
                    routes['prefix'] = url + routes.get('prefix', '')
                yield priority, url or None, name, routes
                continue
            elif not name.startswith('/'):
                for p, u, n, rs in self._iter_resources(sub, prefix):
                    if n:
                        n = ':'.join((name, n))
                    yield p, u, n, rs
                continue
            url = name
            name = routes.pop('name', None)
            for k, v in routes.items():
                if 'include' in routes:
                    continue
                elif isinstance(v, str):
                    routes[k] = {'handler': v}
            yield priority, prefix + url, name, routes

    def _sort_resources(self, resources):
        r = sorted(self._iter_resources(resources), key=lambda x: x[0], reverse=True)
        return map(lambda x: x[1:], r)
