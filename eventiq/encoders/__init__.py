from eventiq.types import Encoder


def get_default_encoder() -> Encoder:
    try:
        from eventiq.encoders.orjson import OrjsonEncoder

        return OrjsonEncoder()

    except ImportError:
        from eventiq.encoders.json import JsonEncoder

        return JsonEncoder()
