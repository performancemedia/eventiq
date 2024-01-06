from typing import Any, Optional, Union

from pydantic import Field

from eventiq.settings import BrokerSettings


class KafkaSettings(BrokerSettings):
    bootstrap_servers: Union[str, list[str]] = Field(
        ..., validation_alias="BROKER_BOOTSTRAP_SERVERS"
    )
    publisher_options: Optional[dict[str, Any]] = Field(
        None, validation_alias="BROKER_PUBLISHER_OPTIONS"
    )
    consumer_options: Optional[dict[str, Any]] = Field(
        None, validation_alias="BROKER_CONSUMER_OPTIONS"
    )
