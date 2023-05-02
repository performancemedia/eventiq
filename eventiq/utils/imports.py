import importlib
from typing import TYPE_CHECKING, Any, Callable

from pydantic import errors
from pydantic.validators import str_validator


def import_from_string(path: str) -> Any:
    module_name, _, obj = path.partition(":")
    module = importlib.import_module(module_name)
    return getattr(module, obj)


if TYPE_CHECKING:
    ImportedType = Callable[..., Any]
else:

    class ImportedType:
        validate_always = True

        @classmethod
        def __get_validators__(cls):
            yield cls.validate

        @classmethod
        def validate(cls, value: Any) -> Any:
            if isinstance(value, Callable):
                return value

            try:
                value = str_validator(value)
            except errors.StrError as e:
                raise errors.PyObjectError(
                    error_message="value is neither a valid import path not a valid callable"
                ) from e

            try:
                return import_from_string(value)
            except ImportError as e:
                raise errors.PyObjectError(error_message=str(e)) from e
