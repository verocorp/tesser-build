class Response:

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        for name in ("__eq__", "__hash__"):
            if name in cls.__dict__:
                raise TypeError(
                    f"{cls.__name__} must not override {name}: "
                    "Response owns the identity contract"
                )

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash((type(self), tuple(sorted(self.__dict__.items()))))
