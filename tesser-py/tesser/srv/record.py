from __future__ import annotations

_NOT_A_FIELD = ("ClassVar", "Final")


def _is_field(annotation: object) -> bool:
    return not str(annotation).replace("typing.", "").startswith(_NOT_A_FIELD)


def _own_annotations(cls: type) -> dict[str, object]:
    annotations: dict[str, object] = getattr(cls, "__annotations__", {})
    return annotations


def _declared_fields(cls: type) -> set[str]:
    fields: set[str] = set()
    for base in cls.__mro__:
        for name, annotation in _own_annotations(base).items():
            if _is_field(annotation):
                fields.add(name)
    return fields


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
            for name in ("__eq__", "__ne__", "__hash__", "__setattr__", "__delattr__"):
                if name in base.__dict__:
                    raise TypeError(
                        f"{cls.__name__} must not override {name}: "
                        "Record owns the record contract"
                    )
            for name, annotation in _own_annotations(base).items():
                if name in base.__dict__ and _is_field(annotation):
                    raise TypeError(
                        f"{cls.__name__} gives field {name!r} a class-level default: "
                        "a record field has no default outside __init__"
                    )

    def __init__(self, **fields: object) -> None:
        if self.__dict__:
            raise AttributeError(
                f"{type(self).__name__} is a frozen record: already constructed"
            )
        declared = _declared_fields(type(self))
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
        raise AttributeError(f"{type(self).__name__} is a frozen record: cannot set {name!r}")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"{type(self).__name__} is a frozen record: cannot delete {name!r}")
