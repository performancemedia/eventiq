import os

os.environ.update(
    {
        "BROKER_URL": "tests.app:app",
        "BROKER_BOOTSTRAP_SERVERS": "localhost:9092",
    }
)
