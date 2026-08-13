import tesser.domain as ts


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
