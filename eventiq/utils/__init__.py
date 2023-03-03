import os
import socket
import uuid


def str_uuid() -> str:
    return str(uuid.uuid4())


def generate_instance_id() -> str:
    pid = os.getpid()
    hostname = socket.gethostname()
    return f"{hostname}:{pid}"
