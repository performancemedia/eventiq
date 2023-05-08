"""
To be done: allow auto-importing/registering third party plugins (from external packages) automatically on service startup
"""

from __future__ import annotations

from typing import Generic, TypeVar

from .broker import Broker
from .logger import LoggerMixin
from .service import Service

BrokerT = TypeVar("BrokerT", bound=Broker)


class ServicePlugin(LoggerMixin):
    def __init__(self, service: Service) -> None:
        self.service = service


class BrokerPlugin(Generic[BrokerT], LoggerMixin):
    def __init__(self, broker: BrokerT) -> None:
        self.broker = broker
