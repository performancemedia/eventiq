from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, model_validator

from eventiq import CloudEvent


class PublishInfo(BaseModel):
    event_type: Type[CloudEvent]
    topic: str = ""
    kwargs: Dict[str, Any] = {}

    @model_validator(mode="after")
    def set_default_topic(self):
        if not self.topic:
            self.topic = self.event_type.get_default_topic()
        return self

    @classmethod
    def s(cls, even_type: Type[CloudEvent], topic: Optional[str] = None, **kwargs: Any):
        return cls(event_type=even_type, topic=topic, kwargs=kwargs)
