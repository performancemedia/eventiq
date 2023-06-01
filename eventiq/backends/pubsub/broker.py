from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gcloud.aio.pubsub import (
    PublisherClient,
    PubsubMessage,
    SubscriberClient,
    SubscriberMessage,
    subscribe,
)

from eventiq.broker import Broker
from eventiq.exceptions import BrokerError

from ...utils import retry
from .settings import PubSubSettings

if TYPE_CHECKING:
    from eventiq import CloudEvent, Consumer, Service


class PubSubBroker(Broker[SubscriberMessage]):
    """
    Google Cloud Pub/Sub broker implementation
    :param service_file: path to the service account (json) file
    :param kwargs: Broker base class parameters
    """

    Settings = PubSubSettings

    WILDCARD_ONE = "*"
    WILDCARD_MANY = "*"

    def __init__(
        self,
        *,
        service_file: str,
        **kwargs: Any,
    ) -> None:

        super().__init__(**kwargs)
        self.service_file = service_file
        self._client = None

    def parse_incoming_message(self, message: SubscriberMessage) -> Any:
        return self.encoder.decode(message.data)

    async def _disconnect(self) -> None:
        await self.client.close()

    async def _start_consumer(self, service: Service, consumer: Consumer) -> None:
        consumer_client = SubscriberClient(service_file=self.service_file)
        handler = self.get_handler(service, consumer)
        await subscribe(
            subscription=consumer.topic,
            handler=handler,
            subscriber_client=consumer_client,
            **consumer.options.get("subscribe_options", {}),
        )

    @property
    def client(self) -> PublisherClient:
        if self._client is None:
            raise BrokerError("Broker not connected")
        return self._client

    @retry(max_retries=3)
    async def _publish(
        self,
        message: CloudEvent,
        **kwargs: Any,
    ) -> None:
        ordering_key = kwargs.get("ordering_key", str(message.id))
        timeout = kwargs.get("timeout", 10)
        msg = PubsubMessage(
            data=self.encoder.encode(message.dict()),
            ordering_key=ordering_key,
            content_type=self.encoder.CONTENT_TYPE,
            **kwargs.get("headers", {}),
        )
        await self.client.publish(topic=message.topic, messages=[msg], timeout=timeout)

    async def _connect(self) -> None:
        self._client = PublisherClient(service_file=self.service_file)

    @property
    def is_connected(self) -> bool:
        return self.client.session._session.closed
