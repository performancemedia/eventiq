from __future__ import annotations

from typing import Any

from pydantic import BaseModel, model_validator

from eventiq import CloudEvent


class PublishInfo(BaseModel):
    event_type: type[CloudEvent]
    topic: str = ""
    kwargs: dict[str, Any] = {}

    @model_validator(mode="after")
    def set_default_topic(self):
        if not self.topic:
            self.topic = self.event_type.get_default_topic()
        return self

    @classmethod
    def s(cls, even_type: type[CloudEvent], topic: str | None = None, **kwargs: Any):
        return cls(event_type=even_type, topic=topic, kwargs=kwargs)
