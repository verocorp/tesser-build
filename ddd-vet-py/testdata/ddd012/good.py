"""An aggregate that references another root by identity — DDD012 clean.

``Order`` needs to know *which* warehouse it draws from, so it holds a
``WarehouseID`` value object — not the ``Warehouse`` aggregate root itself. The
two roots stay independent: each is loaded, guarded, and persisted on its own,
and the order cannot reach in and mutate the warehouse. Crossing the boundary by
identity is the rule.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WarehouseID:
    _value: str  # hidden — a value object, the identity handle for a Warehouse

    def __str__(self) -> str:
        return self._value


class Shelf:  # a member entity of the Warehouse aggregate
    def __init__(self, id: str) -> None:
        self._id = id

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Shelf) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)


class Warehouse:  # an aggregate root — owns a collection of Shelves
    def __init__(self, id: WarehouseID, shelves: list[Shelf]) -> None:
        self._id = id
        self._shelves = list(shelves)

    @property
    def shelves(self) -> tuple[Shelf, ...]:
        return tuple(self._shelves)  # defensive copy

    __eq__ = None  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]


class Order:  # a separate aggregate root
    def __init__(self, id: str, warehouse_id: WarehouseID) -> None:
        self._id = id
        self._warehouse_id = warehouse_id  # reference the other root by ID — clean

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Order) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)
