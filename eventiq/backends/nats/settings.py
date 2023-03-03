from typing import Any, Dict, Optional

from pydantic import Field

from eventiq.settings import BrokerSettings


class NatsSettings(BrokerSettings):
    url: str = Field(..., env="BROKER_URL")
    auto_flush: bool = Field(True, env="BROKER_AUTO_FLUSH")
    connection_options: Optional[Dict[str, Any]] = Field(
        None, env="BROKER_CONNECTION_OPTIONS"
    )


class JetStreamSettings(NatsSettings):
    prefetch_count: int = Field(10, env="BROKER_PREFETCH_COUNT")
    fetch_timeout: int = Field(10, env="BROKER_FETCH_TIMEOUT")
    jetstream_options: Optional[Dict[str, Any]] = Field(None, env="BROKER_OPTIONS")
