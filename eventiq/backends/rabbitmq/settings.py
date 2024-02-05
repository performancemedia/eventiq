from eventiq.settings import UrlBrokerSettings


class RabbitMQSettings(UrlBrokerSettings):
    default_prefetch_count: int = 10
    exchange_name: str = "default"
