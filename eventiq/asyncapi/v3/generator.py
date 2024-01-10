from __future__ import annotations

import functools
from collections import defaultdict
from collections.abc import Iterable
from itertools import chain
from typing import Any

from pydantic.alias_generators import to_camel
from pydantic.json_schema import models_json_schema

from eventiq.broker import TOPIC_PATTERN
from eventiq.service import Service

from .. import PUBLISH_REGISTRY
from .models import (
    AsyncAPI,
    Channel,
    Components,
    Info,
    Message,
    Operation,
    Parameter,
    Reference,
    Server,
    Tag,
)

TOPIC_TRANSLATION = str.maketrans({"{": "", "}": "", ".": "_", "*": "all"})


def get_all_models_schema(service: Service):
    all_models = [
        (m.event_type, "validation")
        for m in chain(service.consumers.values(), PUBLISH_REGISTRY.values())
    ]
    _, top_level_schema = models_json_schema(
        all_models,
        ref_template="#/components/schemas/{model}",  # type: ignore
    )
    return top_level_schema.get("$defs", {})


def get_topic_parameters(topic: str, **kwargs) -> dict[str, Parameter]:
    params = {}
    for k in topic.split("."):
        if TOPIC_PATTERN.fullmatch(k):
            param_name = k[1:-1]
            params[param_name] = kwargs.get(
                param_name, Parameter(description=param_name)
            )
    return params


def snake_case_to_title(name: str) -> str:
    return name.replace("_", " ").title()


def get_tag_list(tags: dict[str, Tag], taggable: Iterable):
    tag_list = []
    for t in taggable:
        if t not in tags:
            tags[t] = Tag(name=t)
        tag_list.append(tags[t])
    return tag_list


def generate_channel_id(topic: str) -> str:
    topic_snake = topic.translate(TOPIC_TRANSLATION)
    return to_camel(topic_snake)


def generate_spec(service: Service):
    spec: dict[str, dict[str, Any]] = {
        "channels": {},
        "operations": {},
        "components": {"messages": {}},
    }
    channels_params: dict[str, dict[str, Parameter]] = defaultdict(dict)
    tags = {t["name"]: Tag.model_validate(t) for t in service.tags_metadata}

    for consumer in service.consumers.values():
        event_type = consumer.event_type.__name__
        channel_id = generate_channel_id(consumer.topic)
        params = get_topic_parameters(consumer.topic, **consumer.parameters)
        for k, v in params.items():
            channels_params[channel_id].setdefault(k, v)
        message = Message(
            name=event_type,
            title=event_type,
            description=consumer.event_type.__doc__,
            contentType=consumer.event_type.get_default_content_type(),  # This is different per broker
            payload=Reference(ref=f"#/components/schemas/{event_type}"),
        )
        spec["components"]["messages"][event_type] = message
        channel = Channel(
            address=consumer.topic,
            servers=[
                Reference(ref=f"#/servers/{broker}") for broker in consumer.brokers
            ],
            messages={
                event_type: Reference(
                    ref=f"#/channels/{channel_id}/messages/{event_type}"
                )
            },
            parameters=channels_params[channel_id],
            tags=get_tag_list(tags, consumer.tags),
        )
        spec["channels"][channel_id] = channel

        operation_id = f"{to_camel(consumer.name)}Receive"
        operation = Operation(
            action="receive",
            title=f"{snake_case_to_title(consumer.name)} Receive",
            summary=consumer.description,
            channel=Reference(ref=f"#/channels/{channel_id}"),
        )
        spec["operations"][operation_id] = operation

    for publishes in PUBLISH_REGISTRY.values():
        event_type = publishes.event_type.__name__
        params = get_topic_parameters(publishes.topic, **publishes.kwargs)
        channel_id = generate_channel_id(publishes.topic)
        for k, v in params.items():
            channels_params[channel_id].setdefault(k, v)

        operation = Operation(
            action="send",
            title=f"Send {event_type}",
            messages=[Reference(ref=f"#/channels/{channel_id}/messages/{event_type}")],
            channel=Reference(ref=f"#/channels/{channel_id}"),
            tags=get_tag_list(tags, publishes.kwargs.get("tags", [])),
            summary=publishes.kwargs.get("summary", ""),
        )
        operation_id = f"send{event_type}"
        spec["operations"][operation_id] = operation

        if channel_id not in spec["channels"]:
            channel = Channel(
                address=publishes.topic,
                servers=[
                    Reference(ref=f"#/servers/{broker}")
                    for broker in publishes.kwargs.get("servers", ("default",))
                ],
                messages={
                    event_type: Reference(ref=f"#/components/messages/{event_type}")
                },
                parameters=channels_params[channel_id],
                tags=get_tag_list(tags, publishes.kwargs.get("tags", [])),
                summary=publishes.kwargs.get("description", ""),
            )
            spec["channels"][channel_id] = channel

    return spec


@functools.lru_cache
def get_async_api_spec(service: Service) -> AsyncAPI:
    schemas = get_all_models_schema(service)
    servers = {
        name: Server(
            **{
                "title": name.title(),
                "description": broker.description,
                "protocolVersion": broker.protocol_version,
                "tags": broker.tags,
                **broker.get_info(),
                **broker.async_api_extra,
            }
        )
        for name, broker in service.get_brokers()
    }
    spec = generate_spec(service)
    components = Components(schemas=schemas, **spec["components"])
    return AsyncAPI(
        info=Info(
            **{
                "title": service.title,
                "version": service.version,
                **service.async_api_extra,
            }
        ),
        servers=servers,
        defaultContentType=service.default_broker.encoder.CONTENT_TYPE,
        channels=spec["channels"],
        operations=spec["operations"],
        components=components,
    )
