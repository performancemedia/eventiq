from typing import Any, Optional, Union

from eventiq.settings import BrokerSettings


class KafkaSettings(BrokerSettings):
    bootstrap_servers: Union[str, list[str]]
    publisher_options: Optional[dict[str, Any]]
    consumer_options: Optional[dict[str, Any]]
