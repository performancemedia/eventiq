from __future__ import annotations

from .models import CloudEvent


class EventSubmitterMixin:
    def __init__(self):
        self._events: list[CloudEvent] = []

    def submit(self, event: CloudEvent):
        self._events.append(event)

    def get_events(self) -> list[CloudEvent]:
        return self._events


class EventResolver:
    def __init__(self, service):
        self.service = service

    async def resolve(self, submitter: EventSubmitterMixin):
        for event in submitter.get_events():
            await self.service.publish_event(event)
