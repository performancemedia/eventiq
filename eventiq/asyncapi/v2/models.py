from __future__ import annotations

from typing import Any

from pydantic import AnyUrl, ConfigDict, Field
from pydantic import BaseModel as _BaseModel


class BaseModel(_BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ExtendableBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Info(BaseModel):
    title: str
    version: str


class ExternalDocumentation(ExtendableBaseModel):
    description: str | None = None
    url: AnyUrl


class Tag(ExtendableBaseModel):
    name: str
    description: str | None = None
    externalDocs: ExternalDocumentation | None = None
    model_config = ConfigDict(extra="allow")


class Ref(BaseModel):
    ref: str = Field(..., alias="$ref")


class Message(BaseModel):
    payload: Ref
    content_type: str = Field(..., alias="contentType")
    description: str | None = None
    tags: list[Tag] | None = None


class Operation(BaseModel):
    operation_id: str = Field(..., alias="operationId")
    summary: str | None = None
    message: Ref
    tags: list[Tag] | None = None


class Parameter(BaseModel):
    description: str | None = None
    param_schema: dict[str, Any] = Field({"type": "string"}, alias="schema")
    location: str | None = None


class ChannelItem(BaseModel):
    publish: Operation | None = None
    subscribe: Operation | None = None
    parameters: dict[str, Parameter] = {}


class Server(BaseModel):
    protocol: str
    url: str | None = None
    protocol_version: str = Field("", alias="protocolVersion")
    description: str | None = None


class Components(BaseModel):
    schemas: dict[str, Any] = {}
    messages: dict[str, Any] = {}


class AsyncAPI(BaseModel):
    asyncapi: str = "2.5.0"
    info: Info
    servers: dict[str, Server] = {}
    channels: dict[str, ChannelItem] = {}
    default_content_type: str = Field("application/json", alias="defaultContentType")
    components: Components
    tags: list[Tag] = []
