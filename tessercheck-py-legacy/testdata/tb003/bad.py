from dataclasses import dataclass


@dataclass(frozen=True)
class Slug:
    _value: str

    def normalize(self) -> None:
        object.__setattr__(self, "_value", self._value.lower())


@dataclass(frozen=True, init=False)
class Label:
    _name: str

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "_name", name.strip())
        object.__setattr__(self, "_alias", name)

    def rename(self, name: str) -> None:
        object.__setattr__(self, "_name", name)


@dataclass(frozen=True)
class Code:
    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)
