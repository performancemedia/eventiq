from __future__ import annotations

import functools
import json
import re
from collections import defaultdict
from itertools import chain
from pathlib import Path
from typing import Iterable

from pydantic.json_schema import models_json_schema

from eventiq.asyncapi.models import (
    AsyncAPI,
    ChannelItem,
    Components,
    Info,
    Message,
    Operation,
    Parameter,
    Ref,
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
        (m.event_type, "validation")
        for m in chain(service.consumers.values(), PUBLISH_REGISTRY.values())
    ]
    _, top_level_schema = models_json_schema(
        all_models, ref_template="#/components/schemas/{model}"  # type: ignore
    )
    return top_level_schema.get("$defs", {})


def get_topic_parameters(topic: str, **kwargs) -> dict[str, Parameter]:
    params = {}
    for k in topic.split("."):
        if TOPIC_PATTERN.fullmatch(k):
            param_name = k[1:-1]
            params[param_name] = kwargs.get(param_name, Parameter())
    return params


def get_tag_list(tags: dict[str, Tag], taggable: Iterable):
    tag_list = []
    for t in taggable:
        if t not in tags:
            tags[t] = Tag(name=t)
        tag_list.append(tags[t])
    return tag_list


def populate_spec(service: Service):
    channels: dict[str, ChannelItem] = defaultdict(ChannelItem)
    messages: dict[str, Message] = {}
    tags = {t["name"]: Tag.model_validate(t) for t in service.tags_metadata}

    for publishes in PUBLISH_REGISTRY.values():
        event_type = publishes.event_type.__name__
        params = get_topic_parameters(publishes.topic, **publishes.kwargs)
        for k, v in params.items():
            channels[publishes.topic].parameters.setdefault(k, v)
        if event_type not in messages:
            messages[event_type] = Message(
                content_type=service.broker.encoder.CONTENT_TYPE,
                payload=Ref(ref=f"{PREFIX}{event_type}"),
            )
        channels[publishes.topic].publish = Operation(
            operation_id=f"publish_{camel2snake(event_type)}",
            message=Ref(ref=f"#/components/messages/{event_type}"),
            tags=get_tag_list(tags, publishes.kwargs.get("tags", [])),
            summary=publishes.kwargs.get("description"),
        )
    for consumer in service.consumers.values():
        event_type = consumer.event_type.__name__
        # message_id = camel2snake(f"{consumer.name}_{event_type}")
        if event_type not in messages:
            messages[event_type] = Message(
                content_type=service.broker.encoder.CONTENT_TYPE,
                payload=Ref(ref=f"{PREFIX}{event_type}"),
            )
        subscribe = Operation(
            operation_id=camel2snake(consumer.name),
            message=Ref(ref=f"#/components/messages/{event_type}"),
            tags=get_tag_list(tags, consumer.tags) or None,
            summary=consumer.description,
        )
        channels[consumer.topic].subscribe = subscribe
        params = get_topic_parameters(consumer.topic, **consumer.parameters)
        for k, v in params.items():
            channels[consumer.topic].parameters.setdefault(k, v)
    return channels, messages


@functools.lru_cache
def get_async_api_spec(service: Service) -> AsyncAPI:
    channels, messages = populate_spec(service)
    definitions = get_all_models_schema(service)
    doc_model = AsyncAPI(
        info=Info(title=service.title, version=service.version),
        servers={
            "default": Server(
                protocol=service.broker.protocol,
                description=service.broker.description,
                url=service.broker.safe_url,
                protocol_version=service.broker.protocol_version,
            )
        },
        channels=channels,
        components=Components(schemas=definitions, messages=messages),
        default_content_type=service.broker.encoder.CONTENT_TYPE,
    )
    return doc_model


def save_async_api_to_file(spec: AsyncAPI, path: Path, fmt: str) -> None:
    dump = json.dump
    if fmt == "yaml":
        import yaml

        dump = yaml.dump
    with open(path, "w") as f:
        dump(spec.model_dump(by_alias=True, exclude_none=True), f)
