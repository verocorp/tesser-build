import tesser.domain as ts

import tesser.serialization as serialization


class ItemID(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("id must be non-empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class ItemSpec(ts.Spec):

    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


class Item(ts.AggregateRoot):

    def __init__(self, spec: ItemSpec) -> None:
        item_id = ItemID(spec.id)
        if not spec.name:
            raise ValueError("name must be non-empty")
        self._id = str(item_id)
        self._name = spec.name

    def id(self) -> str:
        return self._id

    def name(self) -> str:
        return self._name
