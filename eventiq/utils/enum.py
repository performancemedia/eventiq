from enum import Enum, auto


class AutoEnum(str, Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    @staticmethod
    def auto():
        """
        Exposes `enum.auto()` to avoid requiring a second import to use `AutoEnum`
        """
        return auto()

    def __repr__(self) -> str:
        return f"{type(self).__name__}.{self.value}"
