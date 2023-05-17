from __future__ import annotations

import functools
import json
import re
from collections import defaultdict
from itertools import chain
from pathlib import Path

from pydantic.schema import schema as all_schemas

from eventiq.asyncapi.models import (
    AsyncAPI,
    ChannelItem,
    Components,
    Info,
    Message,
    Operation,
    Parameter,
    PayloadRef,
    Server,
    Tag,
)

from ..broker import TOPIC_PATTERN
from ..service import Service
from .registry import PUBLISH_REGISTRY

PREFIX = "#/components/schemas/"


def camel2snake(camel: str) -> str:
    """
    Converts a camelCase string to snake_case.
    """
    snake = re.sub(r"([a-zA-Z])([0-9])", lambda m: f"{m.group(1)}_{m.group(2)}", camel)
    snake = re.sub(r"([a-z0-9])([A-Z])", lambda m: f"{m.group(1)}_{m.group(2)}", snake)
    return snake.lower()


def get_all_models_schema(service: Service):
    all_models = [
        m.event_type  # type: ignore
        for m in chain(service.consumers.values(), PUBLISH_REGISTRY.values())
    ]
    return all_schemas(all_models, ref_prefix=PREFIX).get("definitions", [])


def get_topic_parameters(topic: str, **kwargs) -> dict[str, Parameter]:
    params = {}
    for k in topic.split("."):
        if TOPIC_PATTERN.fullmatch(k):
            param_name = k[1:-1]
            params[param_name] = kwargs.get(param_name, Parameter())
    return params


def populate_channel_spec(service: Service):
    channels: dict[str, ChannelItem] = defaultdict(ChannelItem)
    tags = {t["name"]: Tag.parse_obj(t) for t in service.tags_metadata}

    for publishes in PUBLISH_REGISTRY.values():
        publish_tags = []
        for t in publishes.kwargs.get("tags", []):
            if t not in tags:
                tags[t] = Tag(name=t)
            publish_tags.append(tags[t])
        params = get_topic_parameters(publishes.topic, **publishes.kwargs)
        for k, v in params.items():
            channels[publishes.topic].parameters.setdefault(k, v)
        channels[publishes.topic].publish = Operation(
            message=Message(
                message_id=camel2snake(f"publish_{publishes.event_type.__name__}"),
                content_type=service.broker.encoder.CONTENT_TYPE,
                payload=PayloadRef(ref=f"{PREFIX}{publishes.event_type.__name__}"),
                description=publishes.kwargs.get("description", ""),
            ),
            tags=publish_tags or None,
        )
    for consumer in service.consumers.values():
        consumer_tags = []
        for t in consumer.options.get("tags", []):
            if t not in tags:
                tags[t] = Tag(name=t)
            consumer_tags.append(tags[t])
        subscribe = Operation(
            message=Message(
                message_id=camel2snake(f"subscribe_{camel2snake(consumer.name)}"),
                content_type=service.broker.encoder.CONTENT_TYPE,
                payload=PayloadRef(ref=f"{PREFIX}{consumer.event_type.__name__}"),
                description=consumer.description,
            ),
            tags=consumer_tags or None,
        )
        channels[consumer.topic].subscribe = subscribe
        params = get_topic_parameters(
            consumer.topic, **consumer.options.get("params", {})
        )
        for k, v in params.items():
            channels[consumer.topic].parameters.setdefault(k, v)
    return channels, tags


@functools.lru_cache
def get_async_api_spec(service: Service) -> AsyncAPI:
    channels, tags = populate_channel_spec(service)
    definitions = get_all_models_schema(service)
    doc_model = AsyncAPI(
        info=Info(title=service.title, version=service.version),
        servers={
            "default": Server(
                protocol=service.broker.protocol,
                description=service.broker.description,
                url=getattr(service.broker, "url", ""),
                protocol_version=service.broker.protocol_version,
            )
        },
        channels=channels,
        components=Components(schemas=definitions),
        default_content_type=service.broker.encoder.CONTENT_TYPE,
    )
    return doc_model


def save_async_api_to_file(spec: AsyncAPI, path: Path, fmt: str) -> None:
    dump = json.dump
    if fmt == "yaml":
        import yaml

        dump = yaml.dump
    with open(path, "w") as f:
        dump(spec.dict(by_alias=True, exclude_none=True), f)
