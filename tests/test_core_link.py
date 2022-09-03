import uuid
from typing import Tuple, Dict

import pytest

from aioworkers.core.base import LoggingEntity, link
from aioworkers.utils import import_uri


class Linked(LoggingEntity):
    x: Tuple[uuid.UUID, ...] = ()
    y: Dict
    d: 'Linked' = link()
    d2 = link()
    dx: Tuple = link('x')
    dx0: uuid.UUID = link('x', 0)
    dya: int = link('y', 'a')
    dTypeError: str = link('d')
    dyaTypeError: str = link('y', 'a')
    dybNone: str = link('y', 'b', nullable=True)
    dKeyError: str = link()
    d_nullable: str = link(nullable=True)
    d_warn: 'Linked' = link()

    def init(self):
        self.x = (uuid.uuid4(),)
        self.y = {'a': 0, 'b': None}
        return super().init()


@pytest.fixture
def config_yaml():
    return """
    linked:
      cls: {}
      d: .linked
      d2: .linked
      dx: .linked
      dx0: .linked
      dya: .linked
      dTypeError: .d
      dyaTypeError: .linked
      dybNone: .linked
      d_warn: linked
    """.format(
        import_uri(Linked)
    )


async def test_link(context):
    assert context.linked is context.linked.d


async def test_link2(context):
    assert context.linked is context.linked.d2


async def test_link_path(context):
    assert context.linked.dx == context.linked.d.dx


async def test_link_path_int(context):
    assert context.linked.dx0 == context.linked.d.dx0


async def test_link_path_key(context):
    assert context.linked.dya == context.linked.d.dya


async def test_link_type_error(context):
    with pytest.raises(TypeError):
        assert context.linked.dyaTypeError


async def test_link_type_error_(context):
    with pytest.raises(TypeError):
        context.d = 1
        assert context.linked.dTypeError is None


async def test_link_key_error(context):
    with pytest.raises(KeyError):
        assert context.linked.dKeyError


async def test_link_nullable(context):
    assert context.linked.d_nullable is None


async def test_link_nullable_(context):
    assert context.linked.dybNone is None


async def test_link_warn(context):
    with pytest.warns():
        assert context.linked.d_warn
