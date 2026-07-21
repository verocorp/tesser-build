from dataclasses import dataclass


def canonical_str(value: str) -> str:
    return value


@dataclass(frozen=True)
class WidgetID:
    _value: str

    def __str__(self) -> str:
        return canonical_str(self._value)


class Widget:
    def __init__(self, id: WidgetID) -> None:
        self._id = id

    @property
    def id(self) -> WidgetID:
        return self._id

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Widget) and other._id == self._id
