class Shelf:
    def __init__(self, id: str) -> None:
        self._id = id

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Shelf) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)


class Warehouse:
    def __init__(self, id: str, shelves: list[Shelf]) -> None:
        self._id = id
        self._shelves = list(shelves)

    @property
    def shelves(self) -> tuple[Shelf, ...]:
        return tuple(self._shelves)

    __eq__ = None  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]


class Order:
    def __init__(self, id: str, warehouse: Warehouse) -> None:
        self._id = id
        self._warehouse = warehouse

    __eq__ = None  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]
