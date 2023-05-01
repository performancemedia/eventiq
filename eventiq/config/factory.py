from __future__ import annotations

import os

import yaml

from eventiq import Service, ServiceRunner

from .models import AppConfig


def create_app(config_file: str, section: str | None = None) -> ServiceRunner:

    with open(config_file) as f:
        data = f.read()

    formatted = data.format(os.environ)
    loaded = yaml.safe_load(formatted)
    parsed = AppConfig.parse_obj(loaded[section] if section else loaded)
    broker = parsed.broker.build()
    services = []
    for service_config in parsed.services:
        service = Service(broker=broker, **service_config.dict(exclude={"consumers"}))
        for consumer_config in service_config.consumers:
            consumer = consumer_config.build()
            service.add_consumer(consumer)
        services.append(service)

    return ServiceRunner(services)