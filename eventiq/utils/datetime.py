import time
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def current_millis() -> int:
    return time.monotonic_ns() // 1000
