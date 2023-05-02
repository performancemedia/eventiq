import sys
import typing

py38 = sys.version_info >= (3, 8)

if typing.TYPE_CHECKING or py38:
    from importlib import metadata as importlib_metadata
else:
    import importlib_metadata


def importlib_metadata_get(group):
    ep = importlib_metadata.entry_points()
    if not typing.TYPE_CHECKING and hasattr(ep, "select"):
        return ep.select(group=group)
    else:
        return ep.get(group, ())
