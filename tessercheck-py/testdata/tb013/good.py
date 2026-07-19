from dataclasses import dataclass


@dataclass(frozen=True)
class WidgetID:
    _value: str

    def __str__(self) -> str:
        return self._value


@dataclass(frozen=True)
class WidgetSpec:
    id: str


class Widget:
    def __init__(self, spec: WidgetSpec) -> None:
        self._id = WidgetID(spec.id)

    @property
    def id(self) -> WidgetID:
        return self._id

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Widget) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)
