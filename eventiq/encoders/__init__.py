import functools

from ..encoder import Encoder


@functools.cache
def get_default_encoder() -> Encoder:
    try:
        from eventiq.encoders.orjson import OrjsonEncoder

        return OrjsonEncoder()

    except ImportError:
        from eventiq.encoders.json import JsonEncoder

        return JsonEncoder()
