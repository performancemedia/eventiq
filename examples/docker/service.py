from eventiq import Broker, Service

broker = Broker.from_env()
service = Service(name="docker-service", broker=broker)
