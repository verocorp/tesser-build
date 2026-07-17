"""One aggregate root holding another by object — DDD012.

``Warehouse`` is an aggregate root: it owns and guards a collection of Shelves.
``Order`` is a separate aggregate root, but it holds the whole ``Warehouse``
object as a field — reaching across the boundary and pulling another root into
its own consistency scope. Callers could now mutate the warehouse through the
order, and the two aggregates can no longer be loaded or persisted
independently. Reference it by identity (``WarehouseID``) instead.
"""


class Shelf:  # a member entity of the Warehouse aggregate
    def __init__(self, id: str) -> None:
        self._id = id

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Shelf) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)


class Warehouse:  # an aggregate root — owns a collection of Shelves
    def __init__(self, id: str, shelves: list[Shelf]) -> None:
        self._id = id
        self._shelves = list(shelves)

    @property
    def shelves(self) -> tuple[Shelf, ...]:
        return tuple(self._shelves)  # defensive copy — DDD011-clean

    __eq__ = None  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]


class Order:  # a separate aggregate root
    def __init__(self, id: str, warehouse: Warehouse) -> None:
        self._id = id
        self._warehouse = warehouse  # holds another ROOT by object — DDD012

    # An aggregate root blocks accidental equality (it is not a value).
    __eq__ = None  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]
