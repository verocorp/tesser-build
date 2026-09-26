class Entity:

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        for name in ("__eq__", "__hash__"):
            if name in cls.__dict__ and cls.__dict__[name] is not None:
                raise TypeError(
                    f"{cls.__name__} must not override {name}: "
                    "Entity owns the identity contract; declare `identity`"
                )

    @property
    def identity(self) -> object:
        raise NotImplementedError(
            f"{type(self).__name__} must declare `identity` — the value object "
            "that is this entity's identity"
        )

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return bool(self.identity == other.identity)

    def __hash__(self) -> int:
        return hash((type(self), self.identity))
