import importlib


def import_name(stref: str):
    package, name = stref.rsplit(maxsplit=1)
    module = importlib.import_module(package)
    return getattr(module, name)
