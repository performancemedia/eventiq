from typing import Any, Optional

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
    def s(
        cls, even_type: type[CloudEvent], topic: Optional[str] = None, **kwargs: Any
    ) -> "PublishInfo":
        return cls(event_type=even_type, topic=topic, kwargs=kwargs)
