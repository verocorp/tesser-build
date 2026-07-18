"""An entity that defines __eq__ without __hash__ — TB014.

``Widget`` is an entity: it compares by identity (its id). But it defines only
``__eq__`` — in Python that silently sets ``__hash__ = None``, making the entity
unhashable (it can't go in a set or be a dict key). ``__eq__`` and ``__hash__``
are defined together, both by ID.
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

    def __eq__(self, other: object) -> bool:  # identity, but no __hash__ — TB014
        return isinstance(other, Widget) and other._id == self._id
