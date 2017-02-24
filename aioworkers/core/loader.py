import logging
from collections import Mapping

from .. import utils

logger = logging.getLogger(__name__)


async def load_entities(conf, context=None, loop=None, entities=None, path=()):
    from .context import Context

    ents = {}
    if entities is None:
        entities = ents

    if conf.get('app.cls'):
        cls = utils.import_name(conf['app.cls'])
        app = await cls.factory(
            config=conf, context=context, loop=loop)
        conf['app'] = app

        if context is not None:
            app.on_startup.append(lambda x: context.start())
            app.on_shutdown.append(lambda x: context.stop())

    elif context is None:
        context = Context(conf, loop=loop)

    for k, v in conf.items():
        if not isinstance(v, Mapping):
            pass
        elif k in ('logging', 'app'):
            pass
        elif 'cls' in v:
            if 'name' not in v:
                v['name'] = '.'.join(path + (k,))
            cls = utils.import_name(v['cls'])
            logger.debug('Imported "{}" as {}'.format(v['cls'], cls))
            conf[k] = cls(v, context=context, loop=loop)
            entities[path + (k,)] = conf[k]
        else:
            conf[k] = await load_entities(
                conf[k],
                context=context,
                loop=loop,
                entities=entities,
                path=path + (k,))

    for i in ents.values():
        await i.init()

    return conf
