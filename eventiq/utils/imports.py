import importlib
from typing import Any


def import_from_string(path: str) -> Any:
    module_name, _, obj = path.partition(":")
    module = importlib.import_module(module_name)
    return getattr(module, obj)
