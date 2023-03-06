from __future__ import annotations

import json
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
    PayloadRef,
)

from ..service import Service
from .registry import PUBLISH_REGISTRY

PREFIX = "#/components/schemas/"


def normalize(v: str) -> str:
    return v.lower().replace("-", "_")


def get_all_models_schema(service: Service):
    all_models = [
        m.event_type  # type: ignore
        for m in chain(service.consumers.values(), PUBLISH_REGISTRY.values())
    ]
    return all_schemas(all_models, ref_prefix=PREFIX).get("definitions", [])


def populate_channel_spec(service: Service):
    channels: dict[str, ChannelItem] = defaultdict(ChannelItem)
    # tags = {t["name"]: Tag(**t) for t in service.tags_metadata}

    for publishes in PUBLISH_REGISTRY.values():
        channels[publishes.topic].publish = Operation(
            message=Message(
                message_id=normalize(f"{service.name}_{publishes.event_type.__name__}"),
                content_type=service.broker.encoder.CONTENT_TYPE,
                payload=PayloadRef(ref=f"{PREFIX}{publishes.event_type.__name__}"),
                description=publishes.kwargs.get("description", ""),
            )
        )
    for consumer in service.consumers.values():

        subscribe = Operation(
            message=Message(
                message_id=normalize(f"{consumer.name}_{consumer.event_type.__name__}"),
                content_type=service.broker.encoder.CONTENT_TYPE,
                payload=PayloadRef(ref=f"{PREFIX}{consumer.event_type.__name__}"),
                description=consumer.description,
            )
        )
        channels[consumer.topic].subscribe = subscribe
    return channels


def get_async_api_spec(service: Service) -> AsyncAPI:
    channels = populate_channel_spec(service)
    definitions = get_all_models_schema(service)
    doc_model = AsyncAPI(
        info=Info(title=service.title, version=service.version),
        servers={},
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
