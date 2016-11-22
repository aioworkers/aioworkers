import logging
from collections import Mapping

from .. import utils
from .context import Context

logger = logging.getLogger(__name__)


async def load_entities(conf, context=None, loop=None, entities=None, path=()):
    ents = {}
    if entities is None:
        entities = ents

    if conf.get('app.cls'):
        cls = utils.import_name(conf['app.cls'])
        conf['app'] = await cls.factory(config=conf['app'], loop=loop)
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
            logger.info(v['cls'], cls)
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
