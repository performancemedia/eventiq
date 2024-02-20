from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from eventiq import CloudEvent

    from ._compat import PublishInfo


PUBLISH_REGISTRY: dict[str, PublishInfo] = {}


def publishes(topic: str | None = None, **kwargs):
    def wrapper(cls: type[CloudEvent]) -> type[CloudEvent]:
        PUBLISH_REGISTRY[cls.__name__] = PublishInfo(
            topic=topic, event_type=cls, kwargs=kwargs
        )
        return cls

    return wrapper


def save_async_api_to_file(spec: BaseModel, path: Path, fmt: str) -> None:
    dump = json.dump
    if fmt == "yaml":
        import yaml

        dump = yaml.dump
    with open(path, "w") as f:
        dump(spec.model_dump(by_alias=True, exclude_none=True), f)


def resolve_generator(version: int):
    if version == 2:
        from .v2.generator import get_async_api_spec
    elif version == 3:
        from .v3.generator import get_async_api_spec
    else:
        raise ValueError("Version 2 or 3 expected")
    return get_async_api_spec


def get_html() -> str:
    return """
    <!DOCTYPE html>
    <html>
      <head>
        <style>
         html{-moz-tab-size:4;-o-tab-size:4;tab-size:4;line-height:1.15;-webkit-text-size-adjust:100%};
         body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif,Apple Color Emoji,Segoe UI Emoji};
       </style>
        <link rel="icon" href="https://www.asyncapi.com/favicon.ico">
        <link rel="icon" type="image/png" sizes="16x16" href="https://www.asyncapi.com/favicon-16x16.png">
        <link rel="icon" type="image/png" sizes="32x32" href="https://www.asyncapi.com/favicon-32x32.png">
        <link rel="icon" type="image/png" sizes="194x194" href="https://www.asyncapi.com/favicon-194x194.png">
       <link rel="stylesheet" href="https://unpkg.com/@asyncapi/react-component@latest/styles/default.min.css">

      <title>AsyncAPI Documentation </title>
      </head>
      <body>

        <div id="asyncapi"></div>
        <script src="https://unpkg.com/@asyncapi/react-component@latest/browser/standalone/index.js"></script>
        <script>
          AsyncApiStandalone.render({
            schema: {
                url: '/asyncapi.html',
                options: { method: "GET" },
            },
            config: {
              show: {
                sidebar: true,
              }
            },
          }, document.getElementById('asyncapi'));
        </script>

      </body>
    </html>
    """
