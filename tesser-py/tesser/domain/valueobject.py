class ValueObject:

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if "__slots__" in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must not define __slots__: "
                "ValueObject equality and hash read __dict__"
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
