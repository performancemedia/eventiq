import importlib


def import_from_string(path: str):
    module_name, _, obj = path.partition(":")
    module = importlib.import_module(module_name)
    return getattr(module, obj)
