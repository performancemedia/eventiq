from typing import Annotated, Any, Literal, Optional, TypeVar, Union

from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict, Field
from pydantic_core import Url

T = TypeVar("T")


SecurityType = Literal[
    "userPassword",
    "apiKey",
    "X509",
    "symmetricEncryption",
    "asymmetricEncryption",
    "httpApiKey",
    "http",
    "oauth2",
    "openIdConnect",
    "plain",
    "scramSha256",
    "scramSha512",
    "gssapi",
]


class BaseModel(_BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Reference(BaseModel):
    ref: str = Field(alias="$ref")

    def __hash__(self):
        return hash(self.ref)

    def __eq__(self, other):
        if isinstance(other, Reference):
            return self.ref == other.ref
        return False


TypeOrRef = Annotated[Optional[dict[str, Union[T, Reference]]], Field(default=None)]


class ExternalDocumentation(BaseModel):
    url: Url
    description: Optional[str] = None


OptExternalDocs = Annotated[
    Union[ExternalDocumentation, Reference, None], Field(default=None)
]


class Contact(BaseModel):
    name: str
    url: Url
    email: str


class License(BaseModel):
    name: str
    url: Url


class Tag(BaseModel):
    name: str
    description: Optional[str] = None
    externalDocs: OptExternalDocs

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Tag):
            return self.name == other.name
        return False


Tags = Annotated[Optional[set[Tag]], Field(default=None)]


class Info(BaseModel):
    title: str
    version: str
    description: Optional[str] = None
    termsOfService: Optional[Url] = None
    license: Optional[License] = None
    tags: Tags
    contact: Optional[Contact] = None
    externalDocs: OptExternalDocs


class ServerVariable(BaseModel):
    enum: Optional[set[str]] = None
    default: Optional[str] = None
    description: Optional[str] = None
    examples: Optional[set[str]] = None


class OAuthFlow(BaseModel):
    authorizationUrl: str
    tokenUrl: str
    refreshUrl: Optional[str] = None
    availableScopes: Optional[dict[str, str]] = None


class OAuthFlows(BaseModel):
    implicit: OAuthFlow
    password: OAuthFlow
    clientCredentials: OAuthFlow
    authorizationCode: OAuthFlow


class SecurityScheme(BaseModel):
    type: SecurityType
    name: str
    description: Optional[str] = None
    in_: str = Field(alias="in")
    scheme: str
    bearerFormat: Optional[str] = None
    flows: OAuthFlows
    openIdConnectUrl: Url
    scopes: Optional[set[str]] = None


class Server(BaseModel):
    host: str
    protocol: str
    protocolVersion: Optional[str] = None
    pathname: str = ""
    description: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    variables: TypeOrRef[ServerVariable]
    security: TypeOrRef[SecurityScheme]
    tags: Tags
    externalDocs: OptExternalDocs
    # bindings: Optional[Reference]


#
# class Schema(BaseModel):
#     schemaFormat: str = "application/schema+json;version=draft-07"
#     spec: Any = Field(..., alias="schema")


class Message(BaseModel):
    name: str
    title: str
    contentType: str
    summary: Optional[str] = None
    description: Optional[str] = None
    payload: Union[Reference, Any]
    tags: Tags
    externalDocs: OptExternalDocs
    # headers: Union[Schema, Reference]
    # correlationId: Optional[Union[Reference, Any]]
    # traits: ...
    # bindings: ...


class Parameter(BaseModel):
    enum: Optional[set[str]] = None
    default: Optional[str] = None
    description: Optional[str] = None
    examples: Optional[set[str]] = None
    location: Optional[str] = None


class Channel(BaseModel):
    address: str
    messages: dict[str, Union[Message, Reference]] = {}
    title: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    servers: Optional[set[Reference]] = None
    parameters: TypeOrRef[Parameter]
    tags: Tags
    externalDocs: OptExternalDocs
    # bindings: Union[Reference, ChannelBinding, None]


class ReplyAddress(BaseModel):
    location: str
    description: Optional[str]


class Reply(BaseModel):
    address: Union[ReplyAddress, Reference]
    channel: Optional[Reference] = None
    messages: list[Reference] = []


class Operation(BaseModel):
    action: Literal["send", "receive"]
    channel: Reference
    title: str
    summary: str = ""
    description: Optional[str] = None
    security: Optional[set[Union[SecurityScheme, Reference]]] = None
    tags: Tags = None
    externalDocs: OptExternalDocs
    messages: list[Reference] = []
    reply: Union[Reply, Reference, None] = None
    # bindings: ...
    # traits: ...


class Components(BaseModel):
    schemas: TypeOrRef[Any]
    servers: TypeOrRef[Server]
    channels: TypeOrRef[Channel]
    operations: TypeOrRef[Operation]
    messages: TypeOrRef[Message]
    securitySchemas: TypeOrRef[SecurityScheme]
    serverVariables: TypeOrRef[ServerVariable]
    parameters: TypeOrRef[Parameter]
    replies: TypeOrRef[Reply]
    replyAddresses: TypeOrRef[ReplyAddress]
    externalDocs: TypeOrRef[ExternalDocumentation]
    tags: TypeOrRef[Tag]
    # correlationIds
    # operationTraits
    # messageTraits
    # serverBindings
    # channelBindings
    # operationBindings
    # messageBindings


class AsyncAPI(BaseModel):
    asyncapi: str = "3.0.0"
    info: Info
    servers: TypeOrRef[Server]
    defaultContentType: Optional[str] = None
    channels: TypeOrRef[Channel]
    operations: TypeOrRef[Operation]
    components: Components = Field(default_factory=Components)
    logo: str = Field(
        "https://raw.githubusercontent.com/asyncapi/spec/master/assets/logo.png",
        alias="x-logo",
    )
