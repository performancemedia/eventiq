from typing import Any, Dict, Optional

from pydantic import Field

from eventiq.settings import BrokerSettings


class NatsSettings(BrokerSettings):
    url: str = Field(..., validation_alias="BROKER_URL")
    auto_flush: bool = Field(True, validation_alias="BROKER_AUTO_FLUSH")
    connection_options: Optional[Dict[str, Any]] = Field(
        None, validation_alias="BROKER_CONNECTION_OPTIONS"
    )


class JetStreamSettings(NatsSettings):
    prefetch_count: int = Field(10, validation_alias="BROKER_PREFETCH_COUNT")
    fetch_timeout: int = Field(10, validation_alias="BROKER_FETCH_TIMEOUT")
    jetstream_options: Optional[Dict[str, Any]] = Field(
        None, validation_alias="BROKER_OPTIONS"
    )
