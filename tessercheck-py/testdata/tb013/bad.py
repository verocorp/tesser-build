"""An entity that constructs the ungrounded way — TB013.

``Widget`` exposes the two construction paths Go keeps to one: a value-taking
``__init__(self, id)`` that takes an already-built value object, AND a
``from_spec`` classmethod (the second constructor). The single path is
``__init__(self, spec)``, converting primitives to value objects there.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WidgetID:
    _value: str

    def __str__(self) -> str:
        return self._value


@dataclass(frozen=True)
class WidgetSpec:  # primitive leaves
    id: str


class Widget:
    def __init__(self, id: WidgetID) -> None:  # takes the built VO, not the spec
        self._id = id

    @classmethod
    def from_spec(cls, spec: WidgetSpec) -> "Widget":  # a second constructor
        return cls(WidgetID(spec.id))

    @property
    def id(self) -> WidgetID:
        return self._id

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Widget) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)
