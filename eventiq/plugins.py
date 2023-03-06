from typing import Generic, TypeVar

from .broker import Broker
from .service import Service

BrokerT = TypeVar("BrokerT", bound=Broker)


class ServicePlugin:
    def __init__(self, service: Service):
        self.service = service


class BrokerPlugin(Generic[BrokerT]):
    def __init__(self, broker: BrokerT):
        self.broker = broker
