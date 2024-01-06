from typing import Any, Optional

from pydantic import Field

from eventiq.settings import BrokerSettings


class RedisSettings(BrokerSettings):
    url: str = Field(..., validation_alias="BROKER_URL")
    connection_options: Optional[dict[str, Any]] = Field(
        None, validation_alias="BROKER_CONNECTION_OPTIONS"
    )
