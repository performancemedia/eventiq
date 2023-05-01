import inspect
import logging
from typing import Type, Union

from pythonjsonlogger import jsonlogger

from eventiq.utils.datetime import utc_now


class EventiqJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        if "timestamp" not in log_record:
            log_record["timestamp"] = utc_now()

        log_record["level"] = record.levelname.upper()


def setup_logging(level, fmt: str = "%(name) %(level) %(message)") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(EventiqJsonFormatter(fmt))
    logging.basicConfig(handlers=[handler], level=level)


def get_logger(module: str, name: Union[str, Type]) -> logging.Logger:
    if inspect.isclass(name):
        name = name.__name__

    return logging.getLogger(f"{module}.{name}")


class LoggerMixin:
    logger: logging.Logger

    def __init_subclass__(cls, **kwargs):
        cls.logger = get_logger(__name__, cls)
