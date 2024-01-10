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
    parsed = AppConfig.model_validate(loaded[section] if section else loaded)
    _brokers = {}
    services = []
    for service_config in parsed.services:
        service_brokers = {}
        for broker_name in service_config.brokers:
            if broker_name not in _brokers:
                _brokers[broker_name] = parsed.brokers[broker_name].build()

            service_brokers[broker_name] = _brokers[broker_name]

        service = Service(
            brokers=service_brokers,
            **service_config.model_dump(exclude={"consumers", "broker"}),
        )
        for consumer_config in service_config.consumers:
            consumer = consumer_config.build()
            service.add_consumer(consumer)
        services.append(service)

    return ServiceRunner(*services)


def create_app_from_env():
    from .settings import ConfigSettings

    settings = ConfigSettings()
    return create_app(settings.config_file, section=settings.ENV)
