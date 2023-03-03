from eventiq.types import Encoder


def get_default_encoder() -> Encoder:
    from eventiq.encoders.orjson import OrjsonEncoder

    return OrjsonEncoder()
