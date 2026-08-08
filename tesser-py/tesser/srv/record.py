from __future__ import annotations


class Record:

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        for base in cls.__mro__:
            if base.__dict__.get("__slots__"):
                raise TypeError(
                    f"{cls.__name__} must not define or inherit __slots__: "
                    "Record equality reads __dict__"
                )
            if base is Record or base is object:
                continue
            for name in ("__eq__", "__hash__", "__setattr__", "__delattr__"):
                if name in base.__dict__:
                    raise TypeError(
                        f"{cls.__name__} must not override {name}: "
                        "Record owns the wire-record contract"
                    )

    def __init__(self, **fields: object) -> None:
        declared: set[str] = set()
        for base in type(self).__mro__:
            declared.update(getattr(base, "__annotations__", {}))
        for name, value in fields.items():
            if name not in declared:
                raise TypeError(f"{type(self).__name__} declares no field {name!r}")
            object.__setattr__(self, name, value)

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __repr__(self) -> str:
        fields = ", ".join(f"{name}={value!r}" for name, value in self.__dict__.items())
        return f"{type(self).__name__}({fields})"

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{type(self).__name__} is a frozen wire record: cannot set {name!r}")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"{type(self).__name__} is a frozen wire record: cannot delete {name!r}")
