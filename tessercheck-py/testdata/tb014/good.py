"""An entity whose equality matches its stereotype — TB014 clean.

``Widget`` is an entity: identity equality by ID, with ``__eq__`` and ``__hash__``
defined together. (A value object would compare by value; an aggregate root would
block equality with ``__eq__ = None`` / ``__hash__ = None``.)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WidgetID:
    _value: str

    def __str__(self) -> str:
        return self._value


class Widget:
    def __init__(self, id: WidgetID) -> None:
        self._id = id

    @property
    def id(self) -> WidgetID:
        return self._id

    def __eq__(self, other: object) -> bool:  # identity by ID ...
        return isinstance(other, Widget) and other._id == self._id

    def __hash__(self) -> int:  # ... defined together with __hash__
        return hash(self._id)
