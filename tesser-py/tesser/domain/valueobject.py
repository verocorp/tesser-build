class ValueObject:

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        for base in cls.__mro__:
            if base.__dict__.get("__slots__"):
                raise TypeError(
                    f"{cls.__name__} must not define or inherit __slots__: "
                    "ValueObject equality and hash read __dict__"
                )
        for name in ("__eq__", "__hash__", "__setattr__", "__delattr__"):
            if name in cls.__dict__:
                raise TypeError(
                    f"{cls.__name__} must not override {name}: "
                    "ValueObject owns the identity contract"
                )

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash((type(self), tuple(sorted(self.__dict__.items()))))

    def __repr__(self) -> str:
        fields = ", ".join(f"{name}={value!r}" for name, value in self.__dict__.items())
        return f"{type(self).__name__}({fields})"

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable: cannot set {name!r}")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable: cannot delete {name!r}")
