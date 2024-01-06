from typing import Any

from eventiq.settings import UrlBrokerSettings


class NatsSettings(UrlBrokerSettings):
    auto_flush: bool = True


class JetStreamSettings(NatsSettings):
    prefetch_count: int = 10
    fetch_timeout: int = 10
    jetstream_options: dict[str, Any] = {}
