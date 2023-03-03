from typing import Any, Dict, List, Optional, Union

from pydantic import Field

from eventiq.settings import BrokerSettings


class KafkaSettings(BrokerSettings):
    bootstrap_servers: Union[str, List[str]] = Field(
        ..., env="BROKER_BOOTSTRAP_SERVERS"
    )
    publisher_options: Optional[Dict[str, Any]] = Field(
        None, env="BROKER_PUBLISHER_OPTIONS"
    )
    consumer_options: Optional[Dict[str, Any]] = Field(
        None, env="BROKER_CONSUMER_OPTIONS"
    )
