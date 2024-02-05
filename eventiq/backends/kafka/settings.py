from typing import Any, Union

from eventiq.settings import BrokerSettings


class KafkaSettings(BrokerSettings):
    bootstrap_servers: Union[str, list[str]]
    publisher_options: dict[str, Any] = {}
    consumer_options: dict[str, Any] = {}
