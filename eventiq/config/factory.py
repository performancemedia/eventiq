from __future__ import annotations

import os

import yaml

from eventiq import Service, ServiceRunner

from .models import AppConfig


def create_app(config_file: str, section: str | None = None) -> ServiceRunner:

    with open(config_file) as f:
        data = f.read()
    formatted = data.format(**os.environ)
    loaded = yaml.safe_load(formatted)
    parsed = AppConfig.parse_obj(loaded[section] if section else loaded)
    _brokers = {}
    services = []
    for service_config in parsed.services:
        if service_config.broker not in _brokers:
            _brokers[service_config.broker] = parsed.brokers[
                service_config.broker
            ].build()
        service = Service(
            broker=_brokers[service_config.broker],
            **service_config.dict(exclude={"consumers", "broker"}),
        )
        for consumer_config in service_config.consumers:
            consumer = consumer_config.build()
            service.add_consumer(consumer)
        services.append(service)

    return ServiceRunner(services)


def create_app_from_env():
    from .settings import ConfigSettings

    settings = ConfigSettings()
    return create_app(settings.config_file, section=settings.ENV)
