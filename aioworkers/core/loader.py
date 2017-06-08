import logging
from collections import Mapping

from .. import utils

logger = logging.getLogger(__name__)


async def load_entities(conf, context=None, loop=None, entities=None, path=(),
                        group_resolver=None):
    from .context import Context

    ents = {}
    if entities is None:
        entities = ents

    if conf.get('app.cls'):
        cls = utils.import_name(conf['app.cls'])
        app = await cls.factory(
            config=conf, context=context, loop=loop)

        if context is not None:
            context.app = app
            app.on_startup.append(lambda x: context.start())
            app.on_shutdown.append(lambda x: context.stop())

    elif context is None:
        context = Context(conf, loop=loop, group_resolver=group_resolver)

    for k, v in conf.items():
        if not isinstance(v, Mapping):
            continue
        elif k in ('logging', 'app'):
            continue
        elif 'cls' not in v and 'func' not in v:
            conf[k] = await load_entities(
                conf[k],
                context=context,
                loop=loop,
                entities=entities,
                path=path + (k,),
                group_resolver=group_resolver,
            )
        p = path + (k,)
        str_path = '.'.join(p)
        groups = v.get('groups')
        if not group_resolver.match(groups):
            continue
        if 'cls' in v:
            if 'name' not in v:
                v['name'] = str_path
            entity = context[v]
            context[str_path] = entity
            entities[p] = entity
        elif 'func' in v:
            context[str_path] = context[v]

    for i in ents.values():
        await i.init()

    return conf
