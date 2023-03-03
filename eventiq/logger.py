import inspect
import logging
from typing import Type, Union

from pythonjsonlogger import jsonlogger

from eventiq.context import context
from eventiq.utils.datetime import utc_now


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record.update(**context.get())
        if not log_record.get("timestamp"):
            log_record["timestamp"] = utc_now()
        if log_record.get("level"):
            log_record["level"] = log_record["level"].upper()
        else:
            log_record["level"] = record.levelname


def setup_logging(level):
    handler = logging.StreamHandler()
    handler.setFormatter(CustomJsonFormatter())
    logging.basicConfig(handlers=[handler], level=level)


def get_logger(module: str, name: Union[str, Type]) -> logging.Logger:
    if inspect.isclass(name):
        name = name.__name__

    return logging.getLogger(f"{module}.{name}")


class LoggerMixin:
    logger: logging.Logger

    def __init_subclass__(cls, **kwargs):
        cls.logger = get_logger(__name__, cls)
