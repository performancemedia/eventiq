"""
To be done: allow auto-importing/registering third party plugins (from external packages) automatically on service startup
"""

from __future__ import annotations

import functools
from abc import ABC
from typing import Any, Generic, TypeVar

from ._compat import importlib_metadata_get
from .broker import Broker
from .exceptions import PluginLoadError
from .logger import LoggerMixin
from .service import Service
from .utils.imports import import_from_string

BrokerT = TypeVar("BrokerT", bound=Broker)


class PluginLoader:
    def __init__(self, namespace: str):
        self.namespace = namespace
        self.impls: dict[str, Any] = {}

    def clear(self):
        self.impls.clear()

    def load(self, name: str) -> Any:
        if name in self.impls:
            return self.impls[name]()

        for impl in importlib_metadata_get(self.namespace):
            if impl.name == name:
                self.impls[name] = impl.load
                return impl.load()

        raise PluginLoadError(f"Can't load plugin: {self.namespace}:{name}")

    def register(self, name: str, import_path: str) -> None:
        self.impls[name] = functools.partial(import_from_string, import_path)


registry = PluginLoader("eventiq.plugins")


class EventiqPlugin(ABC, LoggerMixin):
    async def setup(self):
        self.logger.info("Initializing...")

    async def teardown(self):
        self.logger.info("Disconnecting...")


class ServicePlugin(EventiqPlugin):
    def __init__(self, service: Service):
        self.service = service


class BrokerPlugin(EventiqPlugin, Generic[BrokerT]):
    def __init__(self, broker: BrokerT):
        self.broker = broker
