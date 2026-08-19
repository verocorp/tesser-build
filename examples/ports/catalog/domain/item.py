import tesser.domain as ts

from tesser.serialization import canonical_str


class ItemID(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("id must be non-empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)


class ItemSpec(ts.Spec):

    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


class Item(ts.AggregateRoot):

    def __init__(self, spec: ItemSpec) -> None:
        if not spec.id:
            raise ValueError("id must be non-empty")
        if not spec.name:
            raise ValueError("name must be non-empty")
        self._id = spec.id
        self._name = spec.name

    def id(self) -> str:
        return self._id

    def name(self) -> str:
        return self._name
