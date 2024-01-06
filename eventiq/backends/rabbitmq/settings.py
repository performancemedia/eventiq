from typing import Any, Optional

from pydantic import Field

from eventiq.settings import BrokerSettings


class RabbitMQSettings(BrokerSettings):
    url: str = Field(..., validation_alias="BROKER_URL")
    default_prefetch_count: int = Field(
        10, validation_alias="BROKER_DEFAULT_PREFETCH_COUNT"
    )
    exchange_name: str = Field("events", validation_alias="BROKER_EXCHANGE_NAME")
    connection_options: Optional[dict[str, Any]] = Field(
        None, validation_alias="CONNECTION_OPTIONS"
    )
