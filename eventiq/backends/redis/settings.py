from typing import Any, Dict, Optional

from pydantic import Field

from eventiq.settings import BrokerSettings


class RedisSettings(BrokerSettings):
    url: str = Field(..., env="BROKER_URL")
    connection_options: Optional[Dict[str, Any]] = Field(
        None, env="BROKER_CONNECTION_OPTIONS"
    )
