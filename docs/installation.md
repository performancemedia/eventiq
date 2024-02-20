```shell
pip install eventiq
```
or

```shell
poetry add eventiq
```

### Installing optional dependencies

```shell
pip install 'eventiq[extension]'
```

### Available extensions

Misc:

- `cli`
- `prometheus`
- `opentelemetry`

Brokers

- `nats`
- `rabbitmq`
- `kafka`
- `pubsub`
- `redis`

Encoders:

- `orjson`
- `ormsgpack`


### Installing multiple extensions

```shell
pip install 'eventiq[cli, orjson, nats]'
```

### Installing commons (cli, orjson, prometheus) and broker

```shell
pip install 'eventiq[common, nats]'
```