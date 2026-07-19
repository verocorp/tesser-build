from dataclasses import dataclass


@dataclass(frozen=True)
class Slug:
    _value: str

    def __str__(self) -> str:
        return self._value


@dataclass(frozen=True)
class SlugSpec:
    value: str
