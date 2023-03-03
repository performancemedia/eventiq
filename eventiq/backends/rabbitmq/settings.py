from typing import Any, Dict, Optional

from pydantic import Field

from eventiq.settings import BrokerSettings


class RabbitMQSettings(BrokerSettings):
    url: str = Field(..., env="BROKER_URL")
    default_prefetch_count: int = Field(10, env="BROKER_DEFAULT_PREFETCH_COUNT")
    exchange_name: str = Field("events", env="BROKER_EXCHANGE_NAME")
    connection_options: Optional[Dict[str, Any]] = Field(None, env="CONNECTION_OPTIONS")
