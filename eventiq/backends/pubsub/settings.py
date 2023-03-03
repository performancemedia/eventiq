from pydantic import Field

from eventiq.settings import BrokerSettings


class PubSubSettings(BrokerSettings):
    service_file: str = Field(..., env="BROKER_SERVICE_FILE_PATH")
