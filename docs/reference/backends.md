# Available Backends (Brokers)

## Base Broker

::: eventiq.broker.Broker
    handler: python
    options:
        members:
            - publish
            - publish_event
        show_root_heading: true
        show_source: true
        show_bases: false


::: eventiq.backends.stub.StubBroker
    handler: python
    options:
        show_root_heading: true
        show_source: true
        show_bases: false

::: eventiq.backends.nats.NatsBroker
    handler: python
    options:
      show_root_heading: true
      show_source: true
      show_bases: false


::: eventiq.backends.nats.JetStreamBroker
    handler: python
    options:
      show_root_heading: true
      show_source: true
      show_bases: false

::: eventiq.backends.rabbitmq.RabbitmqBroker
    handler: python
    options:
      show_root_heading: true
      show_source: true
      show_bases: false

::: eventiq.backends.kafka.KafkaBroker
    handler: python
    options:
      show_root_heading: true
      show_source: true
      show_bases: false

::: eventiq.backends.redis.RedisBroker
    handler: python
    options:
      show_root_heading: true
      show_source: true
      show_bases: false

::: eventiq.backends.pubsub.PubSubBroker
    handler: python
    options:
      show_root_heading: true
      show_source: true
      show_bases: false

## Custom Broker

Create custom broker by subclassing `eventiq.broker.Broker` and implementing abstract methods.
